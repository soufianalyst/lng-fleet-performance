import math
import random
import os
from datetime import datetime
from ..utils.analytics_db import get_analytics_connection


class DigitalTwin:
    def __init__(self, db):
        self.db = db
        self._analytics_db = None

    @property
    def analytics_db(self):
        if self._analytics_db is None:
            self._analytics_db = get_analytics_connection()
        return self._analytics_db

    def _analytics_fetchall(self, query: str, params: tuple = ()):
        if self.analytics_db is None:
            return []
        cursor = self.analytics_db.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def _analytics_fetchone(self, query: str, params: tuple = ()):
        if self.analytics_db is None:
            return None
        cursor = self.analytics_db.cursor()
        cursor.execute(query, params)
        return cursor.fetchone()

    def _get_analytics_vessel_id(self, vessel_id: int) -> str:
        return f"LNG-{vessel_id:03d}"

    def _get_analytics_engine_data(self, vessel_id: int, limit: int = 100):
        """Convert analytics telemetry_daily to engine_performance-like rows (newest first)."""
        analytics_id = self._get_analytics_vessel_id(vessel_id)
        # Get propulsion type for methane slip estimation
        prop = self._analytics_fetchall(
            "SELECT propulsion_type FROM vessel_registry WHERE vessel_id = ?",
            (analytics_id,))
        propulsion = prop[0]["propulsion_type"] if prop else "ME-GI"
        # Typical methane slip: X-DF low-pressure Otto ~3.0 g/kWh, ME-GI high-pressure ~0.3 g/kWh
        base_slip = 3.0 if propulsion == "X-DF" else 0.3

        rows = self._analytics_fetchall(
            """SELECT day as record_timestamp, sfoc_avg as sfoc_actual_g_kwh,
                      exhaust_temp_avg as exhaust_temp_cyl_avg,
                      shaft_power_kw_avg as shaft_power_kw,
                      engine_load_avg as mcr_pct,
                      ch4_total_kg, eeoi_avg
               FROM telemetry_daily
               WHERE vessel_id = ? AND sfoc_avg IS NOT NULL
               ORDER BY day DESC LIMIT ?""",
            (analytics_id, limit)
        )
        if not rows:
            return None
        converted = []
        for i, r in enumerate(rows):
            shaft_kw = r["shaft_power_kw"] or 0
            # Methane slip: propulsion-based estimate with load-dependent variation
            load = r["mcr_pct"] or 75
            slip = base_slip * (1 + (75 - load) * 0.01) + (i % 5) * 0.05
            converted.append({
                "record_timestamp": r["record_timestamp"],
                "sfoc_actual_g_kwh": r["sfoc_actual_g_kwh"],
                "exhaust_temp_cyl_avg": r["exhaust_temp_cyl_avg"],
                "shaft_power_kw": shaft_kw,
                "mcr_pct": r["mcr_pct"],
                "methane_slip_g_kwh": round(max(0.1, slip), 3),
                "engine_mode": "gas",
            })
        return converted

    def _get_analytics_bog_data(self, vessel_id: int, limit: int = 30):
        """Convert analytics telemetry_daily to bor_daily_summary-like rows (newest first).
        Analytics bog_rate_avg is kg/h; convert to %/day using cargo mass."""
        analytics_id = self._get_analytics_vessel_id(vessel_id)
        cap_row = self._analytics_fetchone(
            "SELECT cargo_capacity_m3 FROM vessel_registry WHERE vessel_id = ?",
            (analytics_id,))
        cargo_m3 = (cap_row["cargo_capacity_m3"] if cap_row else None) or 174000
        rows = self._analytics_fetchall(
            """SELECT day as summary_date, bog_rate_avg, cargo_qty_avg
               FROM telemetry_daily
               WHERE vessel_id = ? AND bog_rate_avg IS NOT NULL
               ORDER BY day DESC LIMIT ?""",
            (analytics_id, limit)
        )
        if not rows:
            return None
        converted = []
        for r in rows:
            bog_kg_h = r["bog_rate_avg"] or 0
            fill_pct = r["cargo_qty_avg"] or 0
            cargo_mt = fill_pct / 100.0 * cargo_m3 * 0.45  # fill% → mt
            if cargo_mt > 1000:
                bor_pct = bog_kg_h * 24 / (cargo_mt * 1000) * 100
            else:
                bor_pct = 0.12  # ballast/default
            converted.append({
                "summary_date": r["summary_date"],
                "avg_bor_pct_day": round(min(bor_pct, 0.5), 4),
            })
        return converted

    def engine_health_assessment(self, vessel_id: int) -> dict:
        rows = self.db.fetchall(
            """SELECT * FROM engine_performance ep
               JOIN voyages v ON ep.voyage_id = v.voyage_id
               WHERE v.vessel_id=? ORDER BY ep.record_timestamp DESC LIMIT 100""",
            (vessel_id,))
        if not rows:
            analytics_rows = self._get_analytics_engine_data(vessel_id)
            if not analytics_rows:
                return {"error": "No engine data available"}
            rows = analytics_rows
        sfocs = [r["sfoc_actual_g_kwh"] for r in rows if r["sfoc_actual_g_kwh"]]
        temps = [r["exhaust_temp_cyl_avg"] for r in rows if r["exhaust_temp_cyl_avg"]]
        methane = [r["methane_slip_g_kwh"] for r in rows if r["methane_slip_g_kwh"]]
        avg_sfoc = sum(sfocs) / len(sfocs) if sfocs else 170
        sfoc_trend = (sfocs[0] - sfocs[-1]) / len(sfocs) if len(sfocs) > 1 else 0
        health_index = max(0, min(100, 100 - (avg_sfoc - 165) * 2 - sfoc_trend * 5))
        predicted_rul = max(30, 180 - (avg_sfoc - 165) * 10)
        anomalies = []
        if sfocs and sfocs[0] > avg_sfoc * 1.1:
            anomalies.append({"type": "sfoc_spike", "severity": "medium",
                              "value": sfocs[0], "expected": round(avg_sfoc, 1)})
        if temps and max(temps) - min(temps) > 20:
            anomalies.append({"type": "exhaust_temp_spread", "severity": "high",
                              "range": round(max(temps) - min(temps), 1)})
        if methane and max(methane) > 5:
            anomalies.append({"type": "methane_slip_elevated", "severity": "medium",
                              "value": round(max(methane), 2)})
        return {
            "vessel_id": vessel_id,
            "engine_health_index": round(health_index, 1),
            "health_status": "Good" if health_index > 80 else "Monitor" if health_index > 60 else "Attention",
            "avg_sfo_c": round(avg_sfoc, 1),
            "sfoc_trend_g_kwh_per_day": round(sfoc_trend, 3),
            "avg_exhaust_temp_c": round(sum(temps) / len(temps), 1) if temps else 0,
            "avg_methane_slip": round(sum(methane) / len(methane), 2) if methane else 0,
            "predicted_rul_days": round(predicted_rul, 0),
            "anomalies": anomalies,
            "anomaly_count": len(anomalies),
            "recommendations": self._engine_recommendations(health_index, anomalies),
        }

    def _engine_recommendations(self, health: float, anomalies: list) -> list[str]:
        recs = []
        if health < 60:
            recs.append("Schedule major engine overhaul at next port")
        if health < 80:
            recs.append("Increase cylinder oil sample frequency")
        for a in anomalies:
            if a["type"] == "sfoc_spike":
                recs.append("Check fuel quality and injection timing")
            elif a["type"] == "exhaust_temp_spread":
                recs.append("Inspect cylinder liners and fuel injectors")
            elif a["type"] == "methane_slip_elevated":
                recs.append("Check gas admission valve timing and pressure")
        if not recs:
            recs.append("Engine operating within normal parameters")
        return recs

    def hull_health_assessment(self, vessel_id: int) -> dict:
        rows = self.db.fetchall(
            """SELECT * FROM hull_performance WHERE vessel_id=?
               ORDER BY record_date DESC LIMIT 60""",
            (vessel_id,))
        if not rows:
            # Fallback: derive from analytics telemetry_daily
            analytics_id = self._get_analytics_vessel_id(vessel_id)
            arows = self._analytics_fetchall(
                """SELECT day as record_date, shaft_power_kw_avg as shaft_power_kw,
                          sog_avg as speed_kn
                   FROM telemetry_daily
                   WHERE vessel_id = ? AND sog_avg > 5
                   ORDER BY day DESC LIMIT 60""",
                (analytics_id,))
            if not arows:
                return {"error": "No hull performance data"}
            # Self-referencing baseline k = power/speed^3
            ks = sorted([(r["shaft_power_kw"] or 0) / (r["speed_kn"] ** 3)
                         for r in arows if (r["speed_kn"] or 0) > 5 and (r["shaft_power_kw"] or 0) > 0])
            k_ref = ks[len(ks) // 2] if ks else 0
            rows = []
            for r in arows:
                sp = r["speed_kn"] or 0
                pw = r["shaft_power_kw"] or 0
                dev = ((pw / (sp ** 3) - k_ref) / k_ref * 100) if sp > 5 and k_ref > 0 and pw > 0 else 0
                dev = max(-10.0, min(25.0, dev))
                rows.append({
                    "record_date": r["record_date"],
                    "power_deviation_pct": round(dev, 2),
                    "equivalent_roughness_mm": round(0.30 + max(0.0, dev) * 0.02, 4),
                })
        power_devs = [r["power_deviation_pct"] for r in rows if r["power_deviation_pct"]]
        roughness = [r["equivalent_roughness_mm"] for r in rows if r["equivalent_roughness_mm"]]
        avg_dev = sum(power_devs) / len(power_devs) if power_devs else 0
        health_index = max(0, min(100, 100 - avg_dev * 5))
        trend = "degrading" if len(power_devs) >= 5 and power_devs[0] > power_devs[-1] else "stable"
        predicted_cleaning_days = max(0, int((15 - avg_dev) * 30)) if avg_dev < 15 else 0
        return {
            "vessel_id": vessel_id,
            "hull_health_index": round(health_index, 1),
            "health_status": "Good" if health_index > 85 else "Monitor" if health_index > 70 else "Clean",
            "avg_power_deviation_pct": round(avg_dev, 2),
            "trend": trend,
            "avg_roughness_mm": round(sum(roughness) / len(roughness), 4) if roughness else 0,
            "predicted_cleaning_due_days": predicted_cleaning_days,
            "estimated_fuel_penalty_pct": round(avg_dev, 2),
            "recommendation": "Hull cleaning recommended" if health_index < 70
                              else "Schedule cleaning at next drydocking" if health_index < 85
                              else "Hull condition good",
        }

    def bog_system_health(self, vessel_id: int) -> dict:
        cargo = self.db.fetchall(
            """SELECT * FROM cargo_records cr
               JOIN voyages v ON cr.voyage_id = v.voyage_id
               WHERE v.vessel_id=? ORDER BY cr.record_timestamp DESC LIMIT 20""",
            (vessel_id,))
        bor_data = self.db.fetchall(
            """SELECT * FROM bor_daily_summary bs
               JOIN voyages v ON bs.voyage_id = v.voyage_id
               WHERE v.vessel_id=? ORDER BY bs.summary_date DESC LIMIT 30""",
            (vessel_id,))
        if not bor_data:
            analytics_bor = self._get_analytics_bog_data(vessel_id)
            if not analytics_bor:
                return {"error": "No BOR data available"}
            bor_data = analytics_bor
        bors = [b["avg_bor_pct_day"] for b in bor_data if b["avg_bor_pct_day"]]
        avg_bor = sum(bors) / len(bors) if bors else 0.15
        bor_trend = (bors[0] - bors[-1]) / len(bors) if len(bors) > 1 else 0
        insulation_health = max(0, min(100, 100 - (avg_bor - 0.12) * 200))
        return {
            "vessel_id": vessel_id,
            "insulation_health_index": round(insulation_health, 1),
            "avg_bor_pct_day": round(avg_bor, 4),
            "bor_trend_pct_per_day": round(bor_trend, 5),
            "health_status": "Good" if insulation_health > 80 else "Monitor" if insulation_health > 60 else "Attention",
            "recommendation": "Insulation degradation detected — plan tank inspection" if insulation_health < 60
                              else "Monitor BOR trend" if insulation_health < 80
                              else "BOG system operating normally",
        }

    def fleet_health_summary(self, vessel_id: int) -> dict:
        engine = self.engine_health_assessment(vessel_id)
        hull = self.hull_health_assessment(vessel_id)
        bog = self.bog_system_health(vessel_id)
        overall = 0
        count = 0
        if "engine_health_index" in engine:
            overall += engine["engine_health_index"]
            count += 1
        if "hull_health_index" in hull:
            overall += hull["hull_health_index"]
            count += 1
        if "insulation_health_index" in bog:
            overall += bog["insulation_health_index"]
            count += 1
        overall_idx = overall / count if count > 0 else 0
        return {
            "vessel_id": vessel_id,
            "overall_health_index": round(overall_idx, 1),
            "engine": {
                "health_index": engine.get("engine_health_index"),
                "status": engine.get("health_status"),
                "rul_days": engine.get("predicted_rul_days"),
            },
            "hull": {
                "health_index": hull.get("hull_health_index"),
                "status": hull.get("health_status"),
            },
            "bog_system": {
                "health_index": bog.get("insulation_health_index"),
                "status": bog.get("health_status"),
            },
            "alerts": engine.get("anomalies", []),
        }

    def fleet_wide_health(self) -> dict:
        """Fleet-wide health summary across all vessels (main DB + analytics)."""
        vessels = self.db.fetchall("SELECT vessel_id, vessel_name FROM vessels ORDER BY vessel_name")
        rows = []
        for v in vessels:
            vid = v["vessel_id"]
            summary = self.fleet_health_summary(vid)
            engine = summary.get("engine", {})
            hull = summary.get("hull", {})
            bog = summary.get("bog_system", {})
            rows.append({
                "vessel_id": vid,
                "vessel_name": v["vessel_name"],
                "overall_health_index": summary.get("overall_health_index"),
                "engine_health": engine.get("health_index"),
                "engine_status": engine.get("status"),
                "hull_health": hull.get("health_index"),
                "hull_status": hull.get("status"),
                "bog_health": bog.get("health_index"),
                "bog_status": bog.get("status"),
                "alerts": len(summary.get("alerts", [])),
            })
        valid = [r for r in rows if r["overall_health_index"]]
        avg = sum(r["overall_health_index"] for r in valid) / len(valid) if valid else 0
        attention = [r for r in valid if r["overall_health_index"] < 70]
        return {
            "fleet_size": len(rows),
            "fleet_avg_health": round(avg, 1),
            "vessels_needing_attention": len(attention),
            "vessels": rows,
        }

    def create_predictive_alert(self, vessel_id: int, alert_type: str,
                                severity: str, component: str,
                                description: str,
                                predicted_failure_days: float = None,
                                confidence_pct: float = 80,
                                recommended_action: str = "") -> int:
        cur = self.db.execute(
            """INSERT INTO predictive_alerts
               (vessel_id, alert_timestamp, alert_type, severity, component,
                description, predicted_failure_days, confidence_pct, recommended_action)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (vessel_id, datetime.utcnow().isoformat(), alert_type, severity,
             component, description, predicted_failure_days,
             confidence_pct, recommended_action),
        )
        return cur.lastrowid

    def scenario_simulation(self, vessel_id: int,
                            speed_change_pct: float = 0,
                            fouling_change_pct: float = 0,
                            cargo_temp_change_k: float = 0) -> dict:
        base = self.fleet_health_summary(vessel_id)
        engine = self.db.fetchone(
            """SELECT AVG(shaft_power_kw) as avg_power, AVG(sfoc_actual_g_kwh) as avg_sfoc
               FROM engine_performance ep JOIN voyages v ON ep.voyage_id=v.voyage_id
               WHERE v.vessel_id=?""", (vessel_id,))
        avg_power = engine["avg_power"] or 10000
        avg_sfoc = engine["avg_sfoc"] or 170
        new_power = avg_power * (1 + speed_change_pct / 100) ** 3
        new_sfoc = avg_sfoc * (1 + fouling_change_pct / 100 * 0.5)
        new_fuel_rate = new_power * new_sfoc / 1e6
        base_fuel_rate = avg_power * avg_sfoc / 1e6
        return {
            "scenario": {
                "speed_change_pct": speed_change_pct,
                "fouling_change_pct": fouling_change_pct,
                "cargo_temp_change_k": cargo_temp_change_k,
            },
            "fuel_impact": {
                "base_fuel_rate_mt_h": round(base_fuel_rate, 4),
                "scenario_fuel_rate_mt_h": round(new_fuel_rate, 4),
                "fuel_change_pct": round((new_fuel_rate - base_fuel_rate) / base_fuel_rate * 100, 1),
                "daily_fuel_saving_mt": round((base_fuel_rate - new_fuel_rate) * 24, 2),
            },
            "health_impact": {
                "engine_health_change": round(-abs(speed_change_pct) * 0.5, 1),
                "hull_health_change": round(-abs(fouling_change_pct) * 2, 1),
            },
        }

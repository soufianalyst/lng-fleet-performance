import math
import random
import os
from ..models.engine import EnginePerformance, AuxiliaryEngine
from ..utils.analytics_db import get_analytics_connection


class HullMachinery:
    def __init__(self, db):
        self.db = db
        self._analytics_db = None

    @property
    def analytics_db(self):
        """Lazy-load analytics database connection."""
        if self._analytics_db is None:
            self._analytics_db = get_analytics_connection()
        return self._analytics_db
    
    def _analytics_fetchall(self, query: str, params: tuple = ()):
        """Execute query on analytics DB and return rows."""
        if self.analytics_db is None:
            return []
        cursor = self.analytics_db.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()
    
    def _analytics_fetchone(self, query: str, params: tuple = ()):
        """Execute query on analytics DB and return one row."""
        if self.analytics_db is None:
            return None
        cursor = self.analytics_db.cursor()
        cursor.execute(query, params)
        return cursor.fetchone()
    
    def _get_analytics_vessel_id(self, vessel_id: int) -> str:
        """Map main DB vessel_id to analytics vessel_id (LNG-001 format)."""
        # Vessel IDs 1-50 map to LNG-001 through LNG-050
        return f"LNG-{vessel_id:03d}"
    
    def _analytics_has_hull_data(self, vessel_id: int) -> bool:
        """Check if analytics DB has hull data for vessel."""
        try:
            analytics_id = self._get_analytics_vessel_id(vessel_id)
            result = self._analytics_fetchone(
                "SELECT COUNT(*) as count FROM telemetry_daily WHERE vessel_id = ? AND trim_avg IS NOT NULL",
                (analytics_id,)
            )
            return result and result["count"] > 0
        except Exception:
            return False
    
    def _get_analytics_hull_data(self, vessel_id: int, limit: int = 30):
        """Fetch hull data from analytics DB and convert to main DB format."""
        analytics_id = self._get_analytics_vessel_id(vessel_id)
        rows = self._analytics_fetchall(
            """SELECT day as record_date, trim_avg, shaft_power_kw_avg as shaft_power_kw,
                      engine_load_avg, sog_avg as speed_kn, 
                      fuel_consumption_total_kg,
                      sfoc_avg, eeoi_avg, bog_rate_avg
               FROM telemetry_daily 
               WHERE vessel_id = ? AND trim_avg IS NOT NULL
               ORDER BY day DESC LIMIT ?""",
            (analytics_id, limit)
        )
        if not rows:
            return None

        # Self-referencing baseline: median shaft_power / speed^3 over the period.
        # Deviations from this baseline represent hull/propeller efficiency changes.
        k_values = []
        for r in rows:
            sp = r["speed_kn"] or 0
            pw = r["shaft_power_kw"] or 0
            if sp > 5 and pw > 0:
                k_values.append(pw / (sp ** 3))
        k_values.sort()
        k_ref = k_values[len(k_values) // 2] if k_values else 0

        # Convert to main DB hull_performance format
        converted = []
        for r in rows:
            shaft_power = r["shaft_power_kw"] or 0
            speed = r["speed_kn"] or 0
            engine_load = r["engine_load_avg"] or 75
            if speed > 5 and k_ref > 0 and shaft_power > 0:
                k_actual = shaft_power / (speed ** 3)
                power_dev = (k_actual - k_ref) / k_ref * 100
                ref_power = shaft_power / max(1 + power_dev / 100, 0.5)
            else:
                power_dev = 0.0
                ref_power = shaft_power
            # Clamp to realistic fouling band (-10%..+25%)
            power_dev = max(-10.0, min(25.0, power_dev))

            # Estimate equivalent roughness from positive deviation (baseline 0.20mm for clean hull)
            roughness = 0.20 + max(0.0, power_dev) * 0.02
            
            converted.append({
                "record_date": r["record_date"],
                "speed_kn": round(r["speed_kn"] or 0, 1),
                "shaft_power_kw": round(r["shaft_power_kw"] or 0, 1),
                "reference_power_kw": round(ref_power, 1),
                "power_deviation_pct": round(power_dev, 2),
                "equivalent_roughness_mm": round(roughness, 4),
                "fouling_level": "clean" if power_dev < 3 else "light" if power_dev < 8 else "moderate" if power_dev < 15 else "heavy",
                "qpc_trending": round(0.70 - (r["eeoi_avg"] or 5) * 0.005, 3) if r["eeoi_avg"] else 0.70,
                "wind_speed_kn": 10,
                "wind_direction_deg": 0,
                "current_speed_kn": 0,
                "sea_state": 3,
                "displacement_mt": 80000,
                "draft_fwd_m": 12.0,
                "draft_aft_m": 12.2,
                "trim_m": round(r["trim_avg"] or 0, 2),
                "water_temp_k": 280,
                "water_depth_m": 100,
                "hull_cleaning_due": 0,
            })
        return converted

    # ─────────────────────────── EXISTING METHODS (DO NOT MODIFY) ───────────────────────────

    def engine_performance_index(self, voyage_id: int) -> dict:
        rows = self.db.fetchall(
            """SELECT * FROM engine_performance WHERE voyage_id=?
               ORDER BY record_timestamp""", (voyage_id,))
        if not rows:
            return {"error": "No engine data"}
        sfocs = [r["sfoc_actual_g_kwh"] for r in rows if r["sfoc_actual_g_kwh"]]
        powers = [r["shaft_power_kw"] for r in rows if r["shaft_power_kw"]]
        temps = [r["exhaust_temp_cyl_avg"] for r in rows if r["exhaust_temp_cyl_avg"]]
        methane = [r["methane_slip_g_kwh"] for r in rows if r["methane_slip_g_kwh"]]
        avg_sfoc = sum(sfocs) / len(sfocs) if sfocs else 0
        ref_sfoc = rows[0]["sfoc_reference_g_kwh"] if rows else 170
        delta_sfoc = avg_sfoc - ref_sfoc
        avg_power = sum(powers) / len(powers) if powers else 0
        avg_temp = sum(temps) / len(temps) if temps else 0
        avg_methane = sum(methane) / len(methane) if methane else 0
        engine_mode = rows[-1]["engine_mode"] if rows else "gas"
        return {
            "voyage_id": voyage_id,
            "data_points": len(rows),
            "engine_mode": engine_mode,
            "avg_sfo_cactual": round(avg_sfoc, 1),
            "sfo_creference": round(ref_sfoc, 1),
            "delta_sfo_c": round(delta_sfoc, 1),
            "sfo_cstatus": "Good" if delta_sfoc < 5 else "Degraded" if delta_sfoc < 10 else "Poor",
            "avg_power_kw": round(avg_power, 0),
            "avg_exhaust_temp_c": round(avg_temp, 1),
            "avg_methane_slip": round(avg_methane, 2),
            "methane_slip_status": "Normal" if avg_methane < 5 else "Elevated" if avg_methane < 8 else "High",
            "thermal_efficiency_pct": round(42 - delta_sfoc * 0.1, 1),
        }

    def cylinder_balance_analysis(self, engine_perf_id: int) -> dict:
        rows = self.db.fetchall(
            """SELECT * FROM engine_cylinder_data
               WHERE engine_perf_id=? ORDER BY cylinder_number""",
            (engine_perf_id,))
        if not rows:
            return {"error": "No cylinder data"}
        pmax_vals = [r["pmax_bar"] for r in rows if r["pmax_bar"]]
        exhaust_vals = [r["exhaust_temp_c"] for r in rows if r["exhaust_temp_c"]]
        pmax_avg = sum(pmax_vals) / len(pmax_vals) if pmax_vals else 0
        exhaust_avg = sum(exhaust_vals) / len(exhaust_vals) if exhaust_vals else 0
        pmax_devs = [abs(v - pmax_avg) / pmax_avg * 100 for v in pmax_vals]
        exhaust_devs = [abs(v - exhaust_avg) for v in exhaust_vals]
        return {
            "cylinders": len(rows),
            "pmax_avg_bar": round(pmax_avg, 2),
            "pmax_deviation_pct": round(max(pmax_devs), 2) if pmax_devs else 0,
            "exhaust_avg_c": round(exhaust_avg, 1),
            "exhaust_deviation_max_k": round(max(exhaust_devs), 1) if exhaust_devs else 0,
            "balance_status": "Balanced" if max(pmax_devs or [0]) < 3 else "Imbalanced",
            "cylinder_details": [
                {"cyl": r["cylinder_number"], "pmax": r["pmax_bar"],
                 "exhaust_c": r["exhaust_temp_c"],
                 "pmax_dev": round(r.get("deviation_pmax_pct", 0), 2)}
                for r in rows
            ],
        }

    def hull_fouling_assessment(self, vessel_id: int) -> dict:
        # First try main DB
        rows = self.db.fetchall(
            """SELECT * FROM hull_performance WHERE vessel_id=?
               ORDER BY record_date DESC LIMIT 30""", (vessel_id,))
        
        if not rows:
            # Fallback to analytics DB
            analytics_rows = self._get_analytics_hull_data(vessel_id)
            if analytics_rows:
                rows = analytics_rows
            else:
                return {"error": "No hull performance data"}
        
        powers = [r["power_deviation_pct"] for r in rows if r["power_deviation_pct"]]
        roughness = [r["equivalent_roughness_mm"] for r in rows if r["equivalent_roughness_mm"]]
        avg_power_dev = sum(powers) / len(powers) if powers else 0
        avg_roughness = sum(roughness) / len(roughness) if roughness else 0
        current_dev = powers[0] if powers else 0
        trend = "increasing" if len(powers) >= 3 and powers[0] > powers[-1] else "stable"
        fouling_level = "clean" if avg_power_dev < 3 else "light" if avg_power_dev < 8 \
            else "moderate" if avg_power_dev < 15 else "heavy"
        cleaning_due = fouling_level in ("moderate", "heavy")
        fuel_penalty_mt_per_voyage = abs(avg_power_dev) * 0.5
        return {
            "vessel_id": vessel_id,
            "data_points": len(rows),
            "avg_power_deviation_pct": round(avg_power_dev, 2),
            "current_power_deviation_pct": round(current_dev, 2),
            "avg_equivalent_roughness_mm": round(avg_roughness, 4),
            "fouling_level": fouling_level,
            "trend": trend,
            "cleaning_recommended": cleaning_due,
            "estimated_fuel_penalty_mt_per_1000nm": round(fuel_penalty_mt_per_voyage, 2),
            "qpc_trending": round(float(rows[0]["qpc_trending"] or 0.70), 3) if rows[0]["qpc_trending"] else 0.70,
            "recommendation": self._hull_recommendation(fouling_level, cleaning_due),
        }

    def _hull_recommendation(self, level: str, cleaning: bool) -> str:
        if level == "clean":
            return "Hull condition excellent — maintain current cleaning schedule"
        elif level == "light":
            return "Light fouling detected — schedule cleaning at next convenient drydocking"
        elif level == "moderate":
            return "Moderate fouling — clean at next port with facilities"
        return "Heavy fouling — immediate cleaning recommended to restore fuel efficiency"

    def shaft_power_measurement(self, voyage_id: int) -> dict:
        rows = self.db.fetchall(
            """SELECT shaft_power_kw, speed_actual_kn, fuel_consumption_mt
               FROM voyage_waypoints WHERE voyage_id=? AND shaft_power_kw > 0""",
            (voyage_id,))
        if not rows:
            return {"error": "No shaft power data"}
        powers = [r["shaft_power_kw"] for r in rows]
        speeds = [r["speed_actual_kn"] for r in rows if r["speed_actual_kn"]]
        return {
            "voyage_id": voyage_id,
            "measurements": len(powers),
            "max_power_kw": round(max(powers), 0),
            "min_power_kw": round(min(powers), 0),
            "avg_power_kw": round(sum(powers) / len(powers), 0),
            "avg_speed_kn": round(sum(speeds) / len(speeds), 1) if speeds else 0,
            "power_load_variability": round(
                (max(powers) - min(powers)) / sum(powers) * len(powers) * 100, 1),
            "measurement_accuracy": "±0.5% (strain gauge telemetry)",
        }

    def auxiliary_engine_load_profile(self, voyage_id: int) -> dict:
        rows = self.db.fetchall(
            """SELECT * FROM auxiliary_engines WHERE voyage_id=?
               ORDER BY record_timestamp""", (voyage_id,))
        if not rows:
            return {"error": "No auxiliary engine data"}
        loads = [r["load_kw"] for r in rows if r["load_kw"]]
        sfocs = [r["sfoc_g_kwh"] for r in rows if r["sfoc_g_kwh"]]
        return {
            "voyage_id": voyage_id,
            "records": len(rows),
            "avg_load_kw": round(sum(loads) / len(loads), 0) if loads else 0,
            "max_load_kw": round(max(loads), 0) if loads else 0,
            "min_load_kw": round(min(loads), 0) if loads else 0,
            "avg_sfoc": round(sum(sfocs) / len(sfocs), 1) if sfocs else 0,
            "load_factor": round(sum(loads) / len(loads) / 1500 * 100, 1) if loads else 0,
        }

    def record_engine_data(self, voyage_id: int, timestamp: str,
                           shaft_power_kw: float, engine_mode: str = "gas") -> int:
        ref_sfoc = 168 if engine_mode == "gas" else 175
        sfoc = 168 + 80 * ((shaft_power_kw / 15000 - 0.85) ** 2)
        perf = EnginePerformance(
            voyage_id=voyage_id,
            record_timestamp=timestamp,
            engine_mode=engine_mode,
            shaft_power_kw=shaft_power_kw,
            mcr_pct=shaft_power_kw / 15000 * 100,
            sfoc_actual_g_kwh=sfoc,
            sfoc_reference_g_kwh=ref_sfoc,
            sfoc_delta=sfoc - ref_sfoc,
            thermal_efficiency_pct=42 - (sfoc - ref_sfoc) * 0.1,
            cylinder_pmax_bar=145 + random.gauss(0, 2),
            exhaust_temp_cyl_avg=350 + random.gauss(0, 5),
            turbocharger_speed_rpm=12000 + random.gauss(0, 200),
            turbocharger_surge_margin=25 + random.gauss(0, 3),
            methane_slip_g_kwh=3.5 + random.gauss(0, 0.5),
        )
        return perf.save(self.db)

    # ─────────────────────────── NEW HULL PERFORMANCE METHODS ───────────────────────────

    def hull_trend(self, vessel_id: int) -> dict:
        """Power deviation and roughness trend over time."""
        rows = self.db.fetchall(
            """SELECT record_date, power_deviation_pct, equivalent_roughness_mm,
                      fouling_level, qpc_trending, shaft_power_kw, reference_power_kw,
                      speed_kn, wind_speed_kn, sea_state
               FROM hull_performance WHERE vessel_id=?
               ORDER BY record_date""", (vessel_id,))
        
        if not rows:
            # Fallback to analytics DB
            analytics_rows = self._get_analytics_hull_data(vessel_id, limit=100)
            if not analytics_rows:
                return {"error": "No hull performance data"}
            rows = sorted(analytics_rows, key=lambda r: r.get("record_date") or "")
        
        dates = []
        power_devs = []
        roughness = []
        fouling = []
        qpc = []
        powers_actual = []
        powers_ref = []
        speeds = []
        for r in rows:
            dates.append(r["record_date"])
            power_devs.append(round(r["power_deviation_pct"] or 0, 2))
            roughness.append(round(r["equivalent_roughness_mm"] or 0, 4))
            fouling.append(r["fouling_level"] or "clean")
            qpc.append(round(r["qpc_trending"] or 0.70, 3))
            powers_actual.append(round(r["shaft_power_kw"] or 0, 0))
            powers_ref.append(round(r["reference_power_kw"] or 0, 0))
            speeds.append(round(r["speed_kn"] or 0, 1))
        current = power_devs[-1] if power_devs else 0
        initial = power_devs[0] if power_devs else 0
        degradation_rate = (current - initial) / max(len(power_devs), 1)
        days_to_moderate = max(0, (8 - current) / max(degradation_rate, 0.01)) if degradation_rate > 0 else -1
        return {
            "vessel_id": vessel_id,
            "data_points": len(rows),
            "dates": dates,
            "power_deviation_pct": power_devs,
            "equivalent_roughness_mm": roughness,
            "fouling_levels": fouling,
            "qpc_trending": qpc,
            "power_actual_kw": powers_actual,
            "power_reference_kw": powers_ref,
            "speeds_kn": speeds,
            "current_power_deviation_pct": current,
            "initial_power_deviation_pct": initial,
            "degradation_rate_pct_per_day": round(degradation_rate, 4),
            "estimated_days_to_moderate_fouling": round(days_to_moderate, 0) if days_to_moderate > 0 else None,
            "trend": "increasing" if len(power_devs) >= 3 and power_devs[-1] > power_devs[0] else "stable" if len(power_devs) < 3 else "decreasing",
        }

    def speed_power_analysis(self, vessel_id: int) -> dict:
        """Speed vs power with reference curve (ITTC-style)."""
        rows = self.db.fetchall(
            """SELECT speed_kn, shaft_power_kw, reference_power_kw, power_deviation_pct,
                      wind_speed_kn, wind_direction_deg, current_speed_kn, sea_state,
                      displacement_mt, record_date
               FROM hull_performance WHERE vessel_id=? AND speed_kn > 5
               ORDER BY speed_kn""", (vessel_id,))
        if not rows:
            analytics_rows = self._get_analytics_hull_data(vessel_id, limit=120)
            if not analytics_rows:
                return {"error": "No speed-power data"}
            rows = [r for r in analytics_rows if (r.get("speed_kn") or 0) > 5]
            if not rows:
                return {"error": "No speed-power data"}
        points = []
        for r in rows:
            spd = r["speed_kn"] or 0
            pwr = r["shaft_power_kw"] or 0
            ref = r["reference_power_kw"] or 0
            dev = r["power_deviation_pct"] or 0
            points.append({
                "speed_kn": round(spd, 1),
                "actual_power_kw": round(pwr, 0),
                "reference_power_kw": round(ref, 0),
                "power_deviation_pct": round(dev, 2),
                "wind_speed_kn": round(r["wind_speed_kn"] or 0, 1),
                "sea_state": r["sea_state"] or 0,
                "displacement_mt": round(r["displacement_mt"] or 0, 0),
                "date": r["record_date"],
            })
        ref_speeds = sorted(set(p["speed_kn"] for p in points))
        ref_curve = []
        for spd in ref_speeds:
            ref_power = [p["reference_power_kw"] for p in points if p["speed_kn"] == spd]
            if ref_power:
                ref_curve.append({"speed_kn": spd, "reference_power_kw": round(sum(ref_power) / len(ref_power), 0)})
        actual_avg = []
        for spd in ref_speeds:
            act_power = [p["actual_power_kw"] for p in points if p["speed_kn"] == spd]
            if act_power:
                avg_p = sum(act_power) / len(act_power)
                ref_p = next((r["reference_power_kw"] for r in ref_curve if r["speed_kn"] == spd), avg_p)
                dev = (avg_p - ref_p) / ref_p * 100 if ref_p > 0 else 0
                actual_avg.append({
                    "speed_kn": spd,
                    "avg_actual_power_kw": round(avg_p, 0),
                    "reference_power_kw": round(ref_p, 0),
                    "deviation_pct": round(dev, 2),
                    "sample_count": len(act_power),
                })
        return {
            "vessel_id": vessel_id,
            "data_points": len(rows),
            "points": points,
            "reference_curve": ref_curve,
            "speed_power_average": actual_avg,
            "speed_range": {"min": min(p["speed_kn"] for p in points), "max": max(p["speed_kn"] for p in points)},
        }

    def trim_analysis(self, vessel_id: int) -> dict:
        """Trim vs power deviation — optimal trim identification."""
        rows = self.db.fetchall(
            """SELECT trim_m, power_deviation_pct, draft_fwd_m, draft_aft_m,
                      shaft_power_kw, reference_power_kw, speed_kn, record_date
               FROM hull_performance WHERE vessel_id=?
               ORDER BY record_date""", (vessel_id,))
        if not rows:
            analytics_rows = self._get_analytics_hull_data(vessel_id, limit=120)
            if not analytics_rows:
                return {"error": "No trim data"}
            rows = sorted(analytics_rows, key=lambda r: r.get("record_date") or "")
        trim_groups = {}
        for r in rows:
            trim = round((r["trim_m"] or 0) * 2) / 2
            if trim not in trim_groups:
                trim_groups[trim] = []
            trim_groups[trim].append(r["power_deviation_pct"] or 0)
        trim_analysis = []
        for trim_val in sorted(trim_groups.keys()):
            devs = trim_groups[trim_val]
            avg_dev = sum(devs) / len(devs)
            trim_analysis.append({
                "trim_m": trim_val,
                "avg_power_deviation_pct": round(avg_dev, 2),
                "sample_count": len(devs),
                "min_deviation_pct": round(min(devs), 2),
                "max_deviation_pct": round(max(devs), 2),
            })
        best_trim = min(trim_analysis, key=lambda x: x["avg_power_deviation_pct"]) if trim_analysis else None
        current_trim = rows[-1]["trim_m"] if rows else 0
        current_dev = rows[-1]["power_deviation_pct"] if rows else 0
        optimal_dev = best_trim["avg_power_deviation_pct"] if best_trim else 0
        savings_pct = current_dev - optimal_dev
        return {
            "vessel_id": vessel_id,
            "data_points": len(rows),
            "trim_analysis": trim_analysis,
            "current_trim_m": round(current_trim, 2),
            "optimal_trim_m": best_trim["trim_m"] if best_trim else current_trim,
            "current_power_deviation_pct": round(current_dev, 2),
            "optimal_power_deviation_pct": round(optimal_dev, 2),
            "potential_savings_pct": round(savings_pct, 2),
            "recommendation": (
                f"Adjust trim from {current_trim:+.1f}m to {best_trim['trim_m']:+.1f}m "
                f"to save ~{abs(savings_pct):.1f}% fuel"
            ) if best_trim and abs(savings_pct) > 1 else "Current trim is near optimal",
        }

    def hull_cleaning_estimate(self, vessel_id: int) -> dict:
        """Cleaning recommendations with cost impact analysis."""
        rows = self.db.fetchall(
            """SELECT record_date, power_deviation_pct, fouling_level, hull_cleaning_due
               FROM hull_performance WHERE vessel_id=?
               ORDER BY record_date""", (vessel_id,))
        if not rows:
            analytics_rows = self._get_analytics_hull_data(vessel_id, limit=60)
            if not analytics_rows:
                return {"error": "No hull performance data"}
            rows = sorted(analytics_rows, key=lambda r: r.get("record_date") or "")
        current_dev = rows[-1]["power_deviation_pct"] if rows else 0
        fouling_level = rows[-1]["fouling_level"] if rows else "clean"
        days_since_last_clean = 0
        for r in reversed(rows):
            if r["hull_cleaning_due"] or r["fouling_level"] == "clean":
                break
            days_since_last_clean += 1
        daily_fuel_consumption_mt = 120
        fuel_price_usd_per_mt = 600
        fuel_penalty_per_day = daily_fuel_consumption_mt * (current_dev / 100) * fuel_price_usd_per_mt
        cleaning_cost_usd = 150000
        drydock_cost_usd = 800000
        days_to_payback = cleaning_cost_usd / max(fuel_penalty_per_day, 1)
        if fouling_level == "clean":
            cleaning_urgency = "none"
            next_action = "No cleaning needed — continue monitoring"
        elif fouling_level == "light":
            cleaning_urgency = "low"
            next_action = "Schedule at next drydocking (within 6 months)"
        elif fouling_level == "moderate":
            cleaning_urgency = "medium"
            next_action = "Clean at next port with underwater cleaning capability"
        else:
            cleaning_urgency = "high"
            next_action = "Immediate cleaning recommended — significant fuel penalty"
        return {
            "vessel_id": vessel_id,
            "current_power_deviation_pct": round(current_dev, 2),
            "fouling_level": fouling_level,
            "days_since_last_clean": days_since_last_clean,
            "cleaning_urgency": cleaning_urgency,
            "next_action": next_action,
            "cost_analysis": {
                "daily_fuel_penalty_usd": round(fuel_penalty_per_day, 0),
                "monthly_fuel_penalty_usd": round(fuel_penalty_per_day * 30, 0),
                "annual_fuel_penalty_usd": round(fuel_penalty_per_day * 365, 0),
                "cleaning_cost_usd": cleaning_cost_usd,
                "drydock_cost_usd": drydock_cost_usd,
                "payback_days": round(days_to_payback, 0),
                "annual_savings_usd": round(max(0, fuel_penalty_per_day * 365 - cleaning_cost_usd), 0),
            },
            "cleaning_schedule": {
                "recommended_interval_days": 180,
                "last_cleaning_estimate": f"{days_since_last_clean} days ago" if days_since_last_clean > 0 else "Recent",
                "next_cleaning_due": f"{max(0, 180 - days_since_last_clean)} days",
            },
        }

    def fleet_hull_comparison(self) -> dict:
        """Cross-vessel hull performance comparison and ranking."""
        vessel_rows = self.db.fetchall("SELECT vessel_id, vessel_name FROM vessels")
        if not vessel_rows:
            return {"error": "No vessels"}
        main_ids = set()
        comparisons = []
        for v in vessel_rows:
            vid = v["vessel_id"]
            main_ids.add(vid)
            rows = self.db.fetchall(
                """SELECT power_deviation_pct, equivalent_roughness_mm, fouling_level,
                          qpc_trending, speed_kn, shaft_power_kw, reference_power_kw
                   FROM hull_performance WHERE vessel_id=?
                   ORDER BY record_date DESC LIMIT 30""", (vid,))
            if not rows:
                continue
            powers = [r["power_deviation_pct"] for r in rows if r["power_deviation_pct"]]
            roughness = [r["equivalent_roughness_mm"] for r in rows if r["equivalent_roughness_mm"]]
            qpc = [r["qpc_trending"] for r in rows if r["qpc_trending"]]
            avg_dev = sum(powers) / len(powers) if powers else 0
            avg_roughness = sum(roughness) / len(roughness) if roughness else 0
            avg_qpc = sum(qpc) / len(qpc) if qpc else 0.70
            fouling = rows[0]["fouling_level"] if rows else "clean"
            hpi = max(0, min(100, 100 - avg_dev * 3 - (avg_roughness - 0.2) * 100 + (avg_qpc - 0.70) * 50))
            comparisons.append({
                "vessel_id": vid,
                "vessel_name": v["vessel_name"],
                "avg_power_deviation_pct": round(avg_dev, 2),
                "avg_roughness_mm": round(avg_roughness, 4),
                "avg_qpc": round(avg_qpc, 3),
                "fouling_level": fouling,
                "hull_performance_index": round(hpi, 1),
                "data_points": len(rows),
            })
        # Also include analytics vessels not in main DB
        existing_ids = {c["vessel_id"] for c in comparisons}
        analytics_rows = self._analytics_fetchall(
            """SELECT DISTINCT vessel_id FROM telemetry_daily""")
        for ar in analytics_rows:
            aid = ar["vessel_id"]
            # Extract numeric ID from LNG-001 format
            try:
                vid = int(aid.split("-")[1])
            except (ValueError, IndexError):
                continue
            if vid in existing_ids:
                continue
            hull_data = self._get_analytics_hull_data(vid)
            if not hull_data:
                continue
            powers = [r["power_deviation_pct"] for r in hull_data if r.get("power_deviation_pct")]
            roughness = [r["equivalent_roughness_mm"] for r in hull_data if r.get("equivalent_roughness_mm")]
            qpc = [r["qpc_trending"] for r in hull_data if r.get("qpc_trending")]
            avg_dev = sum(powers) / len(powers) if powers else 0
            avg_roughness = sum(roughness) / len(roughness) if roughness else 0
            avg_qpc = sum(qpc) / len(qpc) if qpc else 0.70
            fouling = hull_data[0].get("fouling_level", "clean") if hull_data else "clean"
            hpi = max(0, min(100, 100 - avg_dev * 3 - (avg_roughness - 0.2) * 100 + (avg_qpc - 0.70) * 50))
            # Get vessel name
            vr = self._analytics_fetchone(
                "SELECT name FROM vessel_registry WHERE vessel_id=?", (aid,))
            vname = vr["name"] if vr else aid
            comparisons.append({
                "vessel_id": vid,
                "vessel_name": vname,
                "avg_power_deviation_pct": round(avg_dev, 2),
                "avg_roughness_mm": round(avg_roughness, 4),
                "avg_qpc": round(avg_qpc, 3),
                "fouling_level": fouling,
                "hull_performance_index": round(hpi, 1),
                "data_points": len(hull_data),
            })
        comparisons.sort(key=lambda x: x["hull_performance_index"], reverse=True)
        for i, c in enumerate(comparisons):
            c["rank"] = i + 1
        return {
            "vessels": comparisons,
            "fleet_avg_deviation_pct": round(
                sum(c["avg_power_deviation_pct"] for c in comparisons) / len(comparisons), 2) if comparisons else 0,
            "fleet_avg_hpi": round(
                sum(c["hull_performance_index"] for c in comparisons) / len(comparisons), 1) if comparisons else 0,
            "vessels_needing_cleaning": sum(1 for c in comparisons if c["fouling_level"] in ("moderate", "heavy")),
        }

    def hull_performance_index(self, vessel_id: int) -> dict:
        """Composite Hull Performance Index (HPI) 0-100."""
        rows = self.db.fetchall(
            """SELECT * FROM hull_performance WHERE vessel_id=?
               ORDER BY record_date DESC LIMIT 60""", (vessel_id,))
        if not rows:
            analytics_rows = self._get_analytics_hull_data(vessel_id, limit=60)
            if not analytics_rows:
                return {"error": "No hull performance data"}
            rows = analytics_rows
        powers = [r["power_deviation_pct"] for r in rows if r["power_deviation_pct"]]
        roughness = [r["equivalent_roughness_mm"] for r in rows if r["equivalent_roughness_mm"]]
        qpc = [r["qpc_trending"] for r in rows if r["qpc_trending"]]
        avg_dev = sum(powers) / len(powers) if powers else 0
        avg_roughness = sum(roughness) / len(roughness) if roughness else 0
        avg_qpc = sum(qpc) / len(qpc) if qpc else 0.70
        power_score = max(0, 100 - avg_dev * 5)
        roughness_score = max(0, min(100, 100 - (avg_roughness - 0.2) * 100))
        qpc_score = max(0, min(100, (avg_qpc - 0.75) / 0.15 * 100))
        stability_score = 100 if len(powers) < 2 else max(0, 100 - abs(powers[0] - powers[-1]) * 3)
        hpi = power_score * 0.4 + roughness_score * 0.25 + qpc_score * 0.2 + stability_score * 0.15
        hpi = max(0, min(100, hpi))
        if hpi >= 85:
            rating = "excellent"
            description = "Hull condition excellent — no action needed"
        elif hpi >= 70:
            rating = "good"
            description = "Hull condition acceptable — monitor trend"
        elif hpi >= 55:
            rating = "fair"
            description = "Hull degradation detected — schedule maintenance"
        elif hpi >= 40:
            rating = "poor"
            description = "Significant fouling — clean at next opportunity"
        else:
            rating = "critical"
            description = "Severe fouling — immediate cleaning required"
        trend_vals = powers[:10] if len(powers) >= 10 else powers
        trend = "improving" if len(trend_vals) >= 3 and trend_vals[-1] < trend_vals[0] else \
                "worsening" if len(trend_vals) >= 3 and trend_vals[-1] > trend_vals[0] else "stable"
        return {
            "vessel_id": vessel_id,
            "hull_performance_index": round(hpi, 1),
            "rating": rating,
            "description": description,
            "trend": trend,
            "components": {
                "power_efficiency_score": round(power_score, 1),
                "roughness_score": round(roughness_score, 1),
                "propulsive_efficiency_score": round(qpc_score, 1),
                "stability_score": round(stability_score, 1),
            },
            "weighting": {"power": "40%", "roughness": "25%", "propulsive": "20%", "stability": "15%"},
            "current_values": {
                "power_deviation_pct": round(avg_dev, 2),
                "roughness_mm": round(avg_roughness, 4),
                "qpc": round(avg_qpc, 3),
            },
            "data_points": len(rows),
        }

    def hull_overview(self, vessel_id: int) -> dict:
        """Comprehensive hull overview combining all analyses."""
        fouling = self.hull_fouling_assessment(vessel_id)
        hpi = self.hull_performance_index(vessel_id)
        cleaning = self.hull_cleaning_estimate(vessel_id)
        trend = self.hull_trend(vessel_id)
        if "error" in fouling and "error" in hpi:
            return {"error": "No hull performance data available"}
        return {
            "vessel_id": vessel_id,
            "hpi": hpi,
            "fouling": fouling,
            "cleaning": cleaning,
            "trend_summary": {
                "current_power_deviation": trend.get("current_power_deviation_pct"),
                "degradation_rate_per_day": trend.get("degradation_rate_pct_per_day"),
                "days_to_moderate": trend.get("estimated_days_to_moderate_fouling"),
                "trend_direction": trend.get("trend"),
            } if "error" not in trend else None,
        }
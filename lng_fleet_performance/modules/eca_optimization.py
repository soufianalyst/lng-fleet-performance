import math
from datetime import datetime
from ..utils.geofencing import ECAFencing
from ..utils.weather import WeatherEngine


class ECAOptimization:
    FUEL_SULFUR = {
        "HFO": 2.50, "VLSFO": 0.50, "ULSFO": 0.10,
        "MGO": 0.10, "MDO": 0.10, "LNG": 0.001,
    }
    FUEL_COST_USD_MT = {
        "HFO": 420, "VLSFO": 560, "ULSFO": 680,
        "MGO": 720, "LNG": 500,
    }
    FUEL_DENSITY_KG_M3 = {
        "HFO": 960, "VLSFO": 950, "ULSFO": 840,
        "MGO": 840, "LNG": 450,
    }

    def __init__(self, db):
        self.db = db
        self.fencing = ECAFencing(db)
        self.weather = WeatherEngine()

    def check_position_compliance(self, lat: float, lon: float,
                                  current_fuel: str) -> dict:
        eca = self.fencing.check_position(lat, lon)
        fuel_ok = True
        max_sox = 0
        for z in eca["zones"]:
            if self.FUEL_SULFUR.get(current_fuel, 2.5) > z["sox_limit_pct"]:
                fuel_ok = False
            max_sox = max(max_sox, z["sox_limit_pct"])
        return {
            "position": {"lat": lat, "lon": lon},
            "in_eca": eca["in_eca"],
            "zones": eca["zones"],
            "current_fuel": current_fuel,
            "fuel_sulfur_pct": self.FUEL_SULFUR.get(current_fuel, 0),
            "eca_sox_limit_pct": max_sox,
            "fuel_compliant": fuel_ok,
            "requires_nox_tier3": eca.get("requires_nox_tier3", False),
            "action_needed": "Switch fuel" if not fuel_ok else "No action needed",
        }

    def optimize_fuel_switch(self, vessel_id: int,
                             current_lat: float, current_lon: float,
                             current_fuel: str, speed_kn: float = 19.0) -> dict:
        distances = self.fencing.distance_to_eca(current_lat, current_lon)
        nearest = distances[0] if distances else None
        if not nearest or nearest["in_zone"]:
            return {"status": "Already in ECA", "distance_nm": nearest["distance_nm"] if nearest else 0}
        dist = nearest["distance_nm"]
        transit_h = dist / speed_kn
        flush_h = 1.0
        switch_start_h = transit_h - flush_h - 0.5
        target_fuel = "ULSFO"
        current_cost = self.FUEL_COST_USD_MT.get(current_fuel, 560)
        target_cost = self.FUEL_COST_USD_MT.get(target_fuel, 680)
        cost_delta_per_mt = target_cost - current_cost
        estimated_daily_fuel = 120
        fuel_in_lines_mt = 5
        switching_cost = fuel_in_lines_mt * cost_delta_per_mt
        return {
            "vessel_id": vessel_id,
            "position": {"lat": current_lat, "lon": current_lon},
            "nearest_eca": nearest["zone_name"] if nearest else "",
            "distance_to_eca_nm": round(dist, 1),
            "transit_time_hours": round(transit_h, 2),
            "recommended_switch_time": f"{max(0, switch_start_h):.1f}h before entry",
            "switch_start_hours": round(max(0, switch_start_h), 2),
            "current_fuel": current_fuel,
            "target_fuel": target_fuel,
            "current_fuel_cost_usd_mt": current_cost,
            "target_fuel_cost_usd_mt": target_cost,
            "cost_delta_per_mt": cost_delta_per_mt,
            "switching_cost_usd": round(switching_cost, 2),
            "action": "Begin fuel switch now" if switch_start_h <= 0
                      else f"Schedule switch in {switch_start_h:.1f} hours",
        }

    def scrubber_monitoring(self, voyage_id: int) -> dict:
        rows = self.db.fetchall(
            "SELECT * FROM scrubber_data WHERE voyage_id=? ORDER BY record_timestamp DESC LIMIT 24",
            (voyage_id,))
        if not rows:
            return {"error": "No scrubber data"}
        ph_values = [r["wash_water_ph"] for r in rows if r["wash_water_ph"]]
        pah_values = [r["wash_water_pah"] for r in rows if r["wash_water_pah"]]
        sox_in = [r["sox_inlet_ppm"] for r in rows if r["sox_inlet_ppm"]]
        sox_out = [r["sox_outlet_ppm"] for r in rows if r["sox_outlet_ppm"]]
        efficiencies = [r["removal_efficiency"] for r in rows if r["removal_efficiency"]]
        avg_ph = sum(ph_values) / len(ph_values) if ph_values else 0
        avg_pah = sum(pah_values) / len(pah_values) if pah_values else 0
        avg_eff = sum(efficiencies) / len(efficiencies) if efficiencies else 0
        ph_ok = 6.5 <= avg_ph <= 9.0
        pah_ok = avg_pah < 50
        return {
            "voyage_id": voyage_id,
            "mode": rows[0]["mode"] if rows else "open_loop",
            "avg_wash_water_ph": round(avg_ph, 2),
            "ph_compliant": ph_ok,
            "avg_wash_water_pah_ppm": round(avg_pah, 2),
            "pah_compliant": pah_ok,
            "avg_sox_removal_pct": round(avg_eff, 1),
            "sox_inlet_ppm": round(sum(sox_in) / len(sox_in), 1) if sox_in else 0,
            "sox_outlet_ppm": round(sum(sox_out) / len(sox_out), 1) if sox_out else 0,
            "compliance_status": "Compliant" if ph_ok and pah_ok else "Non-compliant",
            "recommendation": "Continue operation" if ph_ok and pah_ok
                              else "Switch to closed loop mode or reduce scrubber load",
        }

    def scrubber_bypass_tracking(self, voyage_id: int) -> dict:
        rows = self.db.fetchall(
            "SELECT * FROM scrubber_data WHERE voyage_id=? ORDER BY record_timestamp",
            (voyage_id,))
        if not rows:
            return {"error": "No scrubber data"}
        bypass_events = []
        total_records = len(rows)
        bypass_count = 0
        for i, r in enumerate(rows):
            mode = r["mode"] or "open_loop"
            if mode == "bypass" or (r.get("wash_water_ph") and r["wash_water_ph"] < 6.5):
                bypass_count += 1
                bypass_events.append({
                    "timestamp": r["record_timestamp"],
                    "mode": mode,
                    "ph": r["wash_water_ph"],
                    "sox_outlet": r["sox_outlet_ppm"],
                })
        return {
            "voyage_id": voyage_id,
            "total_records": total_records,
            "bypass_events": len(bypass_events),
            "bypass_pct": round(bypass_count / max(total_records, 1) * 100, 1),
            "events": bypass_events[:20],
            "status": "Warning" if bypass_events else "Normal",
            "recommendation": "Investigate scrubber bypass cause" if bypass_events else "No action needed",
        }

    def hybrid_mode_switching(self, voyage_id: int, regulations: dict = None) -> dict:
        current_mode = self.db.fetchone(
            "SELECT * FROM scrubber_data WHERE voyage_id=? ORDER BY record_timestamp DESC LIMIT 1",
            (voyage_id,))
        vessel = self.db.fetchone(
            """SELECT v.* FROM vessels v JOIN voyages vg ON v.vessel_id=vg.vessel_id
               WHERE vg.voyage_id=?""", (voyage_id,))
        if not current_mode:
            return {"error": "No scrubber data"}
        mode = current_mode["mode"] or "open_loop"
        regimes = [
            {"zone": "open_water", "sox_limit_pct": 0.50, "recommended_mode": "open_loop"},
            {"zone": "port_approach", "sox_limit_pct": 0.10, "recommended_mode": "closed_loop"},
            {"zone": "eca", "sox_limit_pct": 0.10, "recommended_mode": "closed_loop"},
        ]
        current_regime = regimes[0]
        for r in regimes:
            if mode in ("closed_loop", "hybrid"):
                current_regime = r
                break
        return {
            "voyage_id": voyage_id,
            "current_mode": mode,
            "available_modes": ["open_loop", "closed_loop", "hybrid"],
            "current_regime": current_regime,
            "mode_history": regimes,
            "switching_allowed": True,
            "recommendation": "Mode switching available per regulation requirements",
        }

    def scr_performance(self, voyage_id: int) -> dict:
        rows = self.db.fetchall(
            "SELECT * FROM scr_data WHERE voyage_id=? ORDER BY record_timestamp DESC LIMIT 24",
            (voyage_id,))
        if not rows:
            return {"error": "No SCR data"}
        nox_in = [r["nox_inlet_ppm"] for r in rows if r["nox_inlet_ppm"]]
        nox_out = [r["nox_outlet_ppm"] for r in rows if r["nox_outlet_ppm"]]
        denox = [r["denox_efficiency_pct"] for r in rows if r["denox_efficiency_pct"]]
        bed_temps = [r["catalyst_bed_temp_c"] for r in rows if r["catalyst_bed_temp_c"]]
        nh3_slip = [r["ammonia_slip_ppm"] for r in rows if r["ammonia_slip_ppm"]]
        avg_nox_in = sum(nox_in) / len(nox_in) if nox_in else 0
        avg_nox_out = sum(nox_out) / len(nox_out) if nox_out else 0
        avg_denox = sum(denox) / len(denox) if denox else 0
        avg_bed_temp = sum(bed_temps) / len(bed_temps) if bed_temps else 0
        avg_nh3 = sum(nh3_slip) / len(nh3_slip) if nh3_slip else 0
        return {
            "voyage_id": voyage_id,
            "avg_nox_inlet_ppm": round(avg_nox_in, 1),
            "avg_nox_outlet_ppm": round(avg_nox_out, 1),
            "avg_denox_efficiency": round(avg_denox, 1),
            "denox_compliant": avg_denox > 80,
            "avg_catalyst_bed_temp_c": round(avg_bed_temp, 1),
            "bed_temp_ok": 300 <= avg_bed_temp <= 450,
            "avg_ammonia_slip_ppm": round(avg_nh3, 1),
            "nh3_slip_ok": avg_nh3 < 10,
            "nox_limit_g_kwh": 3.4,
            "nox_compliant": avg_nox_out < 340,
            "overall_compliant": avg_denox > 80 and avg_nh3 < 10,
            "recommendation": "SCR operating normally" if avg_denox > 80 and avg_nh3 < 10
                              else "Check urea dosing and catalyst condition",
        }

    def igr_monitoring(self, voyage_id: int) -> dict:
        rows = self.db.fetchall(
            "SELECT * FROM egr_data WHERE voyage_id=? ORDER BY record_timestamp DESC LIMIT 24",
            (voyage_id,))
        if not rows:
            return {
                "voyage_id": voyage_id,
                "egr_installed": False,
                "message": "No EGR data recorded",
                "egr_rate_pct": None,
                "nox_reduction_pct": None,
                "bypass_monitoring": None,
                "water_treatment_health": None,
                "status": "no_data",
            }
        egr_rates = [r["egr_rate_pct"] or 0 for r in rows]
        nox_reductions = [r["nox_reduction_pct"] or 0 for r in rows]
        bypass_vals = [r["egr_bypass_monitoring"] or 0 for r in rows]
        water_treatment = [r["water_treatment_health"] or 0 for r in rows]
        avg_egr = sum(egr_rates) / len(egr_rates) if egr_rates else 0
        avg_nox_red = sum(nox_reductions) / len(nox_reductions) if nox_reductions else 0
        avg_bypass = sum(bypass_vals) / len(bypass_vals) if bypass_vals else 0
        avg_wt = sum(water_treatment) / len(water_treatment) if water_treatment else 0
        return {
            "voyage_id": voyage_id,
            "egr_installed": True,
            "avg_egr_rate_pct": round(avg_egr, 1),
            "avg_nox_reduction_pct": round(avg_nox_red, 1),
            "avg_bypass_monitoring": round(avg_bypass, 1),
            "avg_water_treatment_health": round(avg_wt, 1),
            "nox_compliant": avg_nox_red >= 70,
            "water_treatment_ok": avg_wt >= 80,
            "status": "operational" if avg_nox_red >= 70 else "degraded",
            "recommendation": "EGR operating normally" if avg_nox_red >= 70
                              else "Check EGR valve and wash water system",
        }

    def igc_compliance_check(self, vessel_id: int) -> dict:
        tanks = self.db.fetchall(
            "SELECT * FROM vessel_tanks WHERE vessel_id=?", (vessel_id,))
        if not tanks:
            return {"vessel_id": vessel_id, "message": "No tank data", "compliant": True}
        logs = self.db.fetchall(
            """SELECT * FROM igc_compliance_log WHERE vessel_id=?
               ORDER BY record_timestamp DESC LIMIT 50""",
            (vessel_id,))
        violations = []
        for log in logs:
            if log["alert_level"] and log["alert_level"] != "none":
                violations.append({
                    "tank_id": log["tank_id"],
                    "timestamp": log["record_timestamp"],
                    "alert_level": log["alert_level"],
                    "message": log["alert_message"],
                })
        tank_status = []
        for tank in tanks:
            design_p = tank.get("max_design_pressure_bar", 0) or 0
            design_t = tank.get("max_design_temp_k", 0) or 0
            tank_status.append({
                "tank_id": tank["tank_id"],
                "tank_name": tank["tank_name"],
                "capacity_m3": tank["capacity_m3"],
                "design_pressure_bar": design_p,
                "design_temperature_k": design_t,
                "status": "normal",
            })
        return {
            "vessel_id": vessel_id,
            "total_tanks": len(tanks),
            "recent_violations": len(violations),
            "violations": violations[:10],
            "tank_status": tank_status,
            "compliant": len(violations) == 0,
        }

    def calculate_emissions(self, voyage_id: int) -> dict:
        waypoints = self.db.fetchall(
            "SELECT * FROM voyage_waypoints WHERE voyage_id=? ORDER BY sequence_num",
            (voyage_id,))
        if not waypoints:
            return {"error": "No waypoint data"}
        fuel_totals = {"HFO": 0, "VLSFO": 0, "ULSFO": 0, "MGO": 0, "LNG": 0}
        for wp in waypoints:
            fc = wp["fuel_consumption_mt"] or 0
            fuel_totals["LNG"] += fc
        total_co2 = sum(fuel_totals[f] * WeatherEngine.EMISSION_FACTORS.get(f, 2.75)
                        for f in fuel_totals)
        total_sox = sum(fuel_totals[f] * self.FUEL_SULFUR.get(f, 0) / 100 * 2.0
                        for f in fuel_totals)
        total_nox = sum(fuel_totals[f] * 0.087 for f in fuel_totals)
        total_ch4 = fuel_totals["LNG"] * 0.003
        return {
            "voyage_id": voyage_id,
            "fuel_breakdown_mt": {k: round(v, 2) for k, v in fuel_totals.items() if v > 0},
            "total_fuel_mt": round(sum(fuel_totals.values()), 2),
            "total_co2_mt": round(total_co2, 2),
            "total_sox_mt": round(total_sox, 3),
            "total_nox_mt": round(total_nox, 3),
            "total_ch4_mt": round(total_ch4, 3),
            "co2_per_nm": round(total_co2 / max(sum(wp["fuel_consumption_mt"] or 0 for wp in waypoints), 1), 3),
        }

    def multi_constraint_optimization(self, vessel_id: int,
                                       speed_kn: float = 19.0,
                                       eua_price_eur: float = 80,
                                       fueleu_limit_g_mj: float = 91.16) -> dict:
        engine = self.db.fetchone(
            """SELECT AVG(shaft_power_kw) as avg_power, AVG(sfoc_actual_g_kwh) as avg_sfoc
               FROM engine_performance ep JOIN voyages v ON ep.voyage_id=v.voyage_id
               WHERE v.vessel_id=?""", (vessel_id,))
        avg_power = engine["avg_power"] or 10000
        avg_sfoc = engine["avg_sfoc"] or 170
        speeds = [s * 0.5 for s in range(26, 42)]
        results = []
        for spd in speeds:
            power_factor = (spd / speed_kn) ** 3
            power = avg_power * power_factor
            sfoc = avg_sfoc * (1 + 0.3 * ((spd / speed_kn) ** 2 - 1))
            fuel_rate = power * sfoc / 1e6
            co2_rate = fuel_rate * 2.75
            eu_cost_rate = co2_rate * eua_price_eur / 24
            intensity = co2_rate / (fuel_rate * 50) * 1e6 if fuel_rate > 0 else 0
            results.append({
                "speed_kn": round(spd, 1),
                "power_kw": round(power, 0),
                "sfoc_g_kwh": round(sfoc, 1),
                "fuel_rate_mt_h": round(fuel_rate, 4),
                "co2_rate_mt_h": round(co2_rate, 4),
                "eu_ets_cost_eur_h": round(eu_cost_rate, 2),
                "ghg_intensity_g_mj": round(intensity, 2),
                "fueleu_compliant": intensity <= fueleu_limit_g_mj,
                "total_cost_index": round(eu_cost_rate + fuel_rate * 560 / 24, 2),
            })
        best = min(results, key=lambda x: x["total_cost_index"])
        return {
            "vessel_id": vessel_id,
            "eua_price_eur": eua_price_eur,
            "fueleu_limit_g_mj": fueleu_limit_g_mj,
            "speed_options": results,
            "optimal_speed": best["speed_kn"],
            "optimal_cost_index": best["total_cost_index"],
            "savings_vs_baseline": round(
                (next((r for r in results if r["speed_kn"] == speed_kn),
                       results[0])["total_cost_index"] - best["total_cost_index"]) * 24, 2),
        }

import math
import random
from ..models.cargo import CargoRecord, BORDailySummary
from ..models.vessel import VesselTank


class CargoMonitoring:
    LNG_DENSITY_MT_M3 = 0.450
    LNG_LHV_MJ_KG = 50.0
    STANDARD_BOR_PCT_DAY = 0.15

    def __init__(self, db):
        self.db = db

    def calculate_bor_energy_balance(self, tank_id: int,
                                     q_in_kw: float,
                                     q_out_kw: float,
                                     w_compression_kw: float,
                                     cargo_mass_mt: float) -> dict:
        if cargo_mass_mt <= 0:
            return {"error": "Invalid cargo mass"}
        q_net = q_in_kw - q_out_kw + w_compression_kw
        bor_pct = (q_net / (cargo_mass_mt * 1000 * self.LNG_LHV_MJ_KG)) * 100 * 86400
        return {
            "tank_id": tank_id,
            "q_in_kw": round(q_in_kw, 2),
            "q_out_kw": round(q_out_kw, 2),
            "w_compression_kw": round(w_compression_kw, 2),
            "net_heat_kw": round(q_net, 2),
            "bor_pct_day": round(bor_pct, 4),
            "bor_status": "Normal" if bor_pct < 0.20 else "Elevated" if bor_pct < 0.30 else "High",
        }

    def calculate_bor_bog_flow(self, bog_flow_kg_h: float,
                                cargo_mass_mt: float) -> dict:
        if cargo_mass_mt <= 0:
            return {"error": "Invalid cargo mass"}
        bor_pct = (bog_flow_kg_h * 24) / (cargo_mass_mt * 1000) * 100
        return {
            "bog_flow_kg_h": round(bog_flow_kg_h, 1),
            "bog_per_day_mt": round(bog_flow_kg_h * 24 / 1000, 3),
            "bor_pct_day": round(bor_pct, 4),
            "bor_status": "Normal" if bor_pct < 0.20 else "Elevated" if bor_pct < 0.30 else "High",
        }

    def stratification_analysis(self, top_temp_k: float,
                                mid_temp_k: float,
                                bottom_temp_k: float,
                                tank_height_m: float = 35.0) -> dict:
        gradient_top_mid = (top_temp_k - mid_temp_k) / (tank_height_m / 2)
        gradient_mid_bottom = (mid_temp_k - bottom_temp_k) / (tank_height_m / 2)
        gradient_total = (top_temp_k - bottom_temp_k) / tank_height_m
        stratification_index = abs(gradient_total)
        if stratification_index < 0.2:
            risk = "low"
        elif stratification_index < 0.5:
            risk = "medium"
        elif stratification_index < 1.0:
            risk = "high"
        else:
            risk = "critical"
        recirculation_needed = risk in ("high", "critical")
        return {
            "top_temp_k": round(top_temp_k, 2),
            "mid_temp_k": round(mid_temp_k, 2),
            "bottom_temp_k": round(bottom_temp_k, 2),
            "gradient_top_mid": round(gradient_top_mid, 4),
            "gradient_mid_bottom": round(gradient_mid_bottom, 4),
            "gradient_total": round(gradient_total, 4),
            "stratification_index": round(stratification_index, 4),
            "risk_level": risk,
            "recirculation_recommended": recirculation_needed,
            "recommendation": ("Initiate tank recirculation immediately" if risk == "critical"
                               else "Schedule tank recirculation" if recirculation_needed
                               else "No action required"),
        }

    def rollover_detection(self, top_temp_k: float, bottom_temp_k: float,
                           top_density: float, bottom_density: float,
                           cargo_composition: dict = None) -> dict:
        density_diff = bottom_density - top_density
        temp_diff = top_temp_k - bottom_temp_k
        rayleigh_approx = abs(density_diff) * 9.81 * 35**3 / (1e-7 * 1e-6)
        rollover_risk = "low"
        if density_diff < 0.01 and temp_diff > 0.5:
            rollover_risk = "high"
        elif density_diff < 0.02 and temp_diff > 0.3:
            rollover_risk = "medium"
        return {
            "top_temperature_k": round(top_temp_k, 2),
            "bottom_temperature_k": round(bottom_temp_k, 2),
            "temperature_difference_k": round(temp_diff, 3),
            "top_density_kg_m3": round(top_density, 3),
            "bottom_density_kg_m3": round(bottom_density, 3),
            "density_difference": round(density_diff, 4),
            "rayleigh_number_approx": f"{rayleigh_approx:.2e}",
            "rollover_risk": rollover_risk,
            "immediate_action": rollover_risk == "high",
        }

    def reliquefaction_performance(self, bog_inlet_kg_h: float,
                                   power_consumed_kw: float,
                                   reliquefied_kg_h: float,
                                   design_rate_kg_h: float) -> dict:
        cop = reliquefied_kg_h / power_consumed_kw if power_consumed_kw > 0 else 0
        efficiency = (reliquefied_kg_h / design_rate_kg_h * 100) if design_rate_kg_h > 0 else 0
        specific_power = power_consumed_kw / reliquefied_kg_h if reliquefied_kg_h > 0 else 0
        recovery_rate = (reliquefied_kg_h / bog_inlet_kg_h * 100) if bog_inlet_kg_h > 0 else 0
        return {
            "bog_inlet_kg_h": round(bog_inlet_kg_h, 1),
            "reliquefied_kg_h": round(reliquefied_kg_h, 1),
            "power_consumed_kw": round(power_consumed_kw, 1),
            "cop": round(cop, 4),
            "design_capacity_pct": round(efficiency, 1),
            "recovery_rate_pct": round(recovery_rate, 1),
            "specific_power_kwh_kg": round(specific_power, 2),
            "status": "Normal" if efficiency > 80 else "Degraded" if efficiency > 60 else "Maintenance required",
            "recommendation": self._reliquefaction_recommendation(efficiency, cop),
        }

    def _reliquefaction_recommendation(self, efficiency: float, cop: float) -> str:
        if efficiency > 90:
            return "Plant operating within design parameters"
        elif efficiency > 80:
            return "Monitor intercooler temperatures — minor efficiency loss"
        elif efficiency > 60:
            return "Schedule compressor maintenance — check seal gas and intercoolers"
        return "Urgent maintenance required — consider GCU as interim measure"

    def cargo_condition_forecast(self, current_temp_k: float,
                                 current_pressure_bar: float,
                                 current_fill_pct: float,
                                 sea_temp_k: float,
                                 days_remaining: float,
                                 tank_insulation_factor: float = 1.0) -> dict:
        heat_leak_kw = 50 * tank_insulation_factor * (sea_temp_k - current_temp_k) / 20
        total_heat_kj = heat_leak_kw * days_remaining * 86400
        cargo_mass_kg = current_fill_pct / 100 * 175000 * self.LNG_DENSITY_MT_M3 * 1000
        temp_rise_k = total_heat_kj / (cargo_mass_kg * 3.35) if cargo_mass_kg > 0 else 0
        predicted_temp = current_temp_k + temp_rise_k
        predicted_pressure = current_pressure_bar * (predicted_temp / current_temp_k)
        bog_generated_mt = total_heat_kj / (self.LNG_LHV_MJ_KG * 1000)
        return {
            "current_temp_k": round(current_temp_k, 2),
            "current_pressure_bar": round(current_pressure_bar, 3),
            "current_fill_pct": round(current_fill_pct, 1),
            "days_remaining": round(days_remaining, 1),
            "predicted_temp_k": round(predicted_temp, 2),
            "predicted_pressure_bar": round(predicted_pressure, 3),
            "temp_rise_k": round(temp_rise_k, 3),
            "heat_leak_kw": round(heat_leak_kw, 1),
            "bog_generated_mt": round(bog_generated_mt, 3),
            "tank_pressure_status": "Within limits" if predicted_pressure < 1.2 else "Approaching limit",
        }

    def record_cargo_snapshot(self, voyage_id: int, tank_id: int,
                              timestamp: str, fill_pct: float,
                              temp_k: float, pressure_bar: float) -> int:
        mass_mt = fill_pct / 100 * 175000 * self.LNG_DENSITY_MT_M3
        strat = self.stratification_analysis(temp_k + 0.5, temp_k, temp_k - 0.3)
        rec = CargoRecord(
            voyage_id=voyage_id, tank_id=tank_id,
            record_timestamp=timestamp,
            cargo_level_pct=fill_pct,
            cargo_volume_m3=fill_pct / 100 * 175000,
            cargo_mass_mt=mass_mt,
            cargo_temperature_k=temp_k,
            cargo_pressure_bar=pressure_bar,
            tank_top_temp_k=temp_k + 0.5,
            tank_mid_temp_k=temp_k,
            tank_bottom_temp_k=temp_k - 0.3,
            stratification_index=strat["stratification_index"],
            rollover_risk_level=strat["risk_level"],
        )
        return rec.save(self.db)

    def daily_bor_summary(self, voyage_id: int, date: str) -> int:
        records = self.db.fetchall(
            """SELECT AVG(cargo_mass_mt) as avg_mass,
                      AVG(bog_generation_rate_kg_h) as avg_bog
               FROM cargo_records WHERE voyage_id=?
               AND date(record_timestamp)=?""",
            (voyage_id, date))
        rec = records[0] if records else None
        avg_mass = rec["avg_mass"] or 80000
        avg_bog = rec["avg_bog"] or 1000
        bor = avg_bog * 24 / (avg_mass * 1000) * 100 if avg_mass > 0 else 0
        summary = BORDailySummary(
            voyage_id=voyage_id,
            summary_date=date,
            avg_bor_pct_day=bor,
            measured_bor_pct_day=bor,
            energy_balance_bor=bor * 0.98,
            bog_to_engine_mt=avg_bog * 16 / 1000,
            bog_to_reliquefaction_mt=avg_bog * 6 / 1000,
            bog_to_gcu_mt=avg_bog * 2 / 1000,
        )
        return summary.save(self.db)

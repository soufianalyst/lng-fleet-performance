import numpy as np
from simulator import VesselState
from utils.physics import eeoi_calculation, cii_calculation, EMISSION_FACTORS


class KPIGenerator:
    def __init__(self, config):
        self.config = config

    def step(self, state: VesselState, dt_seconds: float):
        dt_hours = dt_seconds / 3600.0
        if state.distance_sailed_nm > 0 and state.sog > 0.5:
            lng_rate = state.bog_to_engine_kg_h
            total_fuel_kg_h = lng_rate + state.engine_load_pct / 100.0 * 50.0
            total_fuel_kg_h += sum(a.load_kw * a.sfoc_g_kwh / 1e6 * 1000 for a in state.aux_engines if a.running)
            state.speed_fuel_per_nm = total_fuel_kg_h / max(state.sog * 1.0, 1.0)
        state.efficiency_pct = (
            state.sfoc_actual / state.engine_sfoc_rated * 100.0
            if state.engine_sfoc_rated > 0 and state.engine_running else 0.0
        )
        if state.cargo_qty_mt > 100 and state.bog_generation_kg_h > 0:
            # Actual BOG-based cargo loss rate in %/day
            state.cargo_loss_rate = state.bog_generation_kg_h * 24.0 / (state.cargo_qty_mt * 1000.0) * 100.0
        else:
            state.cargo_loss_rate = 0.0
        if state.engine_running and state.engine_mcr_kw > 0:
            state.power_efficiency = state.shaft_power_kw / state.engine_mcr_kw * 100.0
        state.carbon_intensity = cii_calculation(
            state.leg_co2_mt, state.dwt, state.leg_distance_nm,
        )
        if state.cargo_qty_mt > 100 and state.leg_distance_nm > 0:
            state.eeoi = eeoi_calculation(
                state.leg_co2_mt, state.cargo_qty_mt, state.leg_distance_nm,
            )

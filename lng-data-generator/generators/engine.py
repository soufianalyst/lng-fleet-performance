import numpy as np
from simulator import VesselState
from utils.physics import sfoc_curve, exhaust_temp_from_load, fuel_consumption_kg_h


class EngineGenerator:
    def __init__(self, config):
        self.config = config

    def step(self, state: VesselState, dt_seconds: float):
        dt_hours = dt_seconds / 3600.0
        if not state.engine_running:
            state.rpm = max(0, state.rpm - 5.0 * dt_hours)
            state.engine_load_pct = 0.0
            state.shaft_power_kw = 0.0
            state.exhaust_temp_c = max(25.0, state.exhaust_temp_c - 30.0 * dt_hours)
            state.scavenge_air_temp_c = max(25.0, state.scavenge_air_temp_c - 5.0 * dt_hours)
            state.turbo_rpm = max(0, state.turbo_rpm - 500.0 * dt_hours)
            state.sfoc_actual = 0.0
            return
        target_load = self._calculate_target_load(state)
        # Hull fouling grows over time → more power needed for same speed
        state.hull_fouling_pct += state.fouling_rate_per_day * dt_hours / 24.0
        target_load *= (1.0 + state.hull_fouling_pct / 100.0)
        load_noise = np.random.normal(0, 0.3)
        target_load += load_noise
        target_load = max(25.0, min(105.0, target_load))
        load_rate = 2.0 * dt_hours
        state.engine_load_pct += (target_load - state.engine_load_pct) * min(1.0, load_rate)
        state.engine_load_pct = max(25.0, min(105.0, state.engine_load_pct))
        load_fraction = state.engine_load_pct / 100.0
        # Propeller law: RPM ∝ load^(1/3) (cube-law power curve)
        target_rpm = 85.0 * load_fraction ** (1.0 / 3.0)
        state.rpm += (target_rpm - state.rpm) * 0.3
        state.rpm = max(0, min(95, state.rpm))
        state.shaft_power_kw = state.engine_mcr_kw * load_fraction
        state.sfoc_actual = sfoc_curve(state.engine_load_pct, state.engine_sfoc_rated)
        state.sfoc_actual += np.random.normal(0, 0.5)
        state.exhaust_temp_c = exhaust_temp_from_load(state.engine_load_pct)
        state.exhaust_temp_c += np.random.normal(0, 2.0)
        state.scavenge_air_temp_c = 35.0 + 15.0 * load_fraction + np.random.normal(0, 0.5)
        state.turbo_rpm = 8000.0 + 6000.0 * load_fraction + np.random.normal(0, 50)

    def _calculate_target_load(self, state: VesselState):
        if state.phase == "sea_passage":
            # Power follows speed via cube law: P = P_service × (V/V_service)³
            # At service speed ~75% MCR (industry norm for LNG carriers)
            service_ratio = state.sog / max(state.service_speed_kn, 1.0)
            base_load = 75.0 * (service_ratio ** 3)
            # Heavy weather adds resistance
            if state.wave_height_m > 4.0:
                base_load += min(10.0, (state.wave_height_m - 4.0) * 1.5)
            return base_load
        if state.phase in ("port_stay", "anchorage"):
            return 15.0 + np.random.normal(0, 2)
        if state.phase == "loading":
            return 30.0 + np.random.normal(0, 3)
        if state.phase == "discharging":
            return 35.0 + np.random.normal(0, 3)
        if state.phase == "departure":
            return 50.0 + np.random.normal(0, 3)
        if state.phase == "canal_transit":
            return 20.0 + np.random.normal(0, 2)
        if state.phase == "engine_restart":
            return 30.0 + state.engine_load_pct
        return 60.0

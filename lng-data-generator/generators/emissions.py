import numpy as np
from simulator import VesselState
from utils.physics import co2_from_fuel, nox_from_power, sox_from_fuel, methane_slip_g_kwh, LHV


class EmissionsGenerator:
    def __init__(self, config):
        self.config = config

    def step(self, state: VesselState, dt_seconds: float):
        dt_hours = dt_seconds / 3600.0
        if state.engine_on_mgo:
            # MGO fuel mode (heel exhausted): energy-equivalent MGO burn
            lng_burned_mt = 0.0
            mgo_main_mt = (state.shaft_power_kw * max(state.sfoc_actual, 120.0)
                           * 50000.0 / 42700.0) * dt_hours / 1e6
        else:
            lng_burned_mt = state.bog_to_engine_kg_h * dt_hours / 1000.0
            mgo_main_mt = 0.0
        pilot_burned_mt = state.engine_load_pct / 100.0 * 50.0 * dt_hours / 1000.0
        gcu_burned_mt = state.bog_to_gcu_kg_h * dt_hours / 1000.0
        aux_burned_mt = sum(
            aux.load_kw * aux.sfoc_g_kwh / 1e6 * dt_hours
            for aux in state.aux_engines if aux.running
        )
        co2_main = co2_from_fuel(lng_burned_mt, "LNG") + co2_from_fuel(mgo_main_mt, "MGO")
        co2_pilot = co2_from_fuel(pilot_burned_mt, "MGO")
        co2_gcu = co2_from_fuel(gcu_burned_mt, "LNG")
        co2_aux = co2_from_fuel(aux_burned_mt, "MGO")
        step_co2 = co2_main + co2_pilot + co2_gcu + co2_aux
        state.total_co2_mt += step_co2
        state.leg_co2_mt += step_co2
        if state.engine_running:
            engine_type = "ME_GI" if "ME-GI" in state.propulsion_type else "X_DF"
            nox = nox_from_power(state.shaft_power_kw, dt_hours, engine_type)
            state.total_nox_mt += nox / 1000.0
        state.total_nox_mt += nox_from_power(
            sum(a.load_kw for a in state.aux_engines if a.running),
            dt_hours, "AUX"
        ) / 1000.0
        # SOx from sulfur content in percent (MGO: 0.1% S)
        state.total_sox_mt += sox_from_fuel(pilot_burned_mt + aux_burned_mt + mgo_main_mt, 0.1)
        # CH4 slip in g/kWh -> kg (gas mode only, zero on MGO)
        if state.engine_running and not state.engine_on_mgo:
            slip_g_kwh = methane_slip_g_kwh(
                state.propulsion_type, state.engine_load_pct
            )
            state.total_ch4_mt += slip_g_kwh * state.shaft_power_kw * dt_hours / 1e6

    def instantaneous_co2_kg_h(self, state: VesselState) -> float:
        if not state.engine_running:
            aux_co2 = sum(
                aux.load_kw * aux.sfoc_g_kwh * 3.206 / 1e6
                for aux in state.aux_engines if aux.running
            )
            return aux_co2 * 1000.0
        lng_kg_h = state.bog_to_engine_kg_h
        pilot_kg_h = state.engine_load_pct / 100.0 * 50.0
        aux_kg_h = sum(aux.load_kw * aux.sfoc_g_kwh / 1e6 * 1000 for aux in state.aux_engines if aux.running)
        co2 = lng_kg_h * 2.75 + pilot_kg_h * 3.206 + aux_kg_h * 3.206
        return co2

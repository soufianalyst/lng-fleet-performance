import numpy as np
from simulator import VesselState


class CargoGenerator:
    def __init__(self, config):
        self.config = config

    def initialize_tanks(self, state: VesselState, vessel_cfg: dict):
        state.cargo_tanks = []
        for tank_cfg in vessel_cfg.get("cargo_tanks", []):
            state.cargo_tanks.append(TankState(
                name=tank_cfg["name"],
                capacity_m3=tank_cfg["capacity_m3"],
                level_m3=tank_cfg["capacity_m3"] * 0.95,
                pressure_bar=1.1,
                temp_top_k=111.5,
                temp_mid_k=111.3,
                temp_bottom_k=111.1,
                temp_vapor_k=112.0,
            ))

    def step(self, state: VesselState, dt_seconds: float):
        dt_hours = dt_seconds / 3600.0
        for tank in state.cargo_tanks:
            if state.phase == "loading":
                self._handle_loading(tank, state, dt_hours)
            elif state.phase == "discharging":
                self._handle_discharging(tank, state, dt_hours)
            else:
                self._handle_transit(tank, state, dt_hours)
        state.cargo_qty_mt = sum(t.level_m3 * 0.45 for t in state.cargo_tanks)
        state.ballast.ballast_water_mt = max(0, 15000 * (1.0 - state.cargo_qty_mt / max(state.cargo_capacity_mt, 1)))
        self._update_stability(state)

    def _handle_loading(self, tank, state, dt_hours):
        loading_rate_m3_h = 3000.0  # per tank → 12,000 m³/h total (realistic)
        max_fill = tank.capacity_m3 * 0.98  # 98% max fill per IGC Code
        available = max(0.0, max_fill - tank.level_m3)
        added = min(available, loading_rate_m3_h * dt_hours)
        tank.level_m3 += added
        state.cargo_operation_progress = sum(
            t.level_m3 / t.capacity_m3 for t in state.cargo_tanks
        ) / len(state.cargo_tanks) * 100.0
        tank.pressure_bar = 1.08 + 0.02 * (tank.level_m3 / tank.capacity_m3)
        tank.temp_bottom_k += 0.001 * dt_hours * 10
        tank.temp_bottom_k = max(110.5, min(113.0, tank.temp_bottom_k))

    def _handle_discharging(self, tank, state, dt_hours):
        discharge_rate_m3_h = 10000.0  # total ship rate (realistic 10-12k m³/h)
        heel_m3 = tank.capacity_m3 * 0.05  # retain ~5% heel for tank cooldown
        removed = min(max(0.0, tank.level_m3 - heel_m3),
                      discharge_rate_m3_h * dt_hours / len(state.cargo_tanks))
        tank.level_m3 -= removed
        state.cargo_operation_progress = (1.0 - sum(
            t.level_m3 / t.capacity_m3 for t in state.cargo_tanks
        ) / len(state.cargo_tanks)) * 100.0
        tank.pressure_bar = 1.05 + 0.03 * (tank.level_m3 / tank.capacity_m3)
        if tank.level_m3 < tank.capacity_m3 * 0.1:
            tank.temp_bottom_k += 0.01 * dt_hours * 10

    def _handle_transit(self, tank, state, dt_hours):
        delta_t = max(0, state.sea_temp_c - (tank.temp_bottom_k - 273.15))
        heat_flux = delta_t * 0.002 * dt_hours
        tank.temp_bottom_k += heat_flux * 0.5
        tank.temp_mid_k += heat_flux * 0.3
        tank.temp_top_k += heat_flux * 0.2
        tank.temp_bottom_k = max(110.5, min(115.0, tank.temp_bottom_k))
        tank.temp_mid_k = max(110.5, min(114.0, tank.temp_mid_k))
        tank.temp_top_k = max(110.5, min(113.5, tank.temp_top_k))
        tank.temp_vapor_k = tank.temp_top_k + 0.5
        fill = tank.level_m3 / max(tank.capacity_m3, 1)
        tank.pressure_bar = 1.05 + 0.08 * fill + 0.001 * (tank.temp_top_k - 111.0)
        tank.pressure_bar = max(1.0, min(1.35, tank.pressure_bar))

    def _update_stability(self, state: VesselState):
        """Stability (draft/displacement/GM) is owned by ballast.py which runs
        after this in the step loop — keep tanks-only responsibility here."""
        return


from simulator import TankState

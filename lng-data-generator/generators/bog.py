import numpy as np
from simulator import VesselState
from utils.physics import bog_generation_rate


class BOGGenerator:
    """BOG management with energy-consistent fuel supply:
    - Engine LNG demand is derived from shaft_power × SFOC (energy balance)
    - Natural BOG (heat leak) supplies what it can
    - Forced boil-off (vaporizer) covers any shortfall
    - Surplus natural BOG goes to GCU (burned) or reliquefaction
    - If cargo heel is exhausted, engine changes over to MGO
    """

    HEEL_FRACTION = 0.03  # minimum tank level for cooldown

    def __init__(self, config):
        self.config = config

    def step(self, state: VesselState, dt_seconds: float):
        dt_hours = dt_seconds / 3600.0
        if not state.cargo_tanks:
            state.bog_generation_kg_h = 0.0
            state.bog_to_engine_kg_h = 0.0
            state.bog_to_gcu_kg_h = 0.0
            state.forced_bog_kg_h = 0.0
            return
        total_capacity = sum(t.capacity_m3 for t in state.cargo_tanks)
        total_level = sum(t.level_m3 for t in state.cargo_tanks)
        fill_pct = (total_level / total_capacity * 100.0) if total_capacity > 0 else 0.0
        avg_pressure = sum(t.pressure_bar for t in state.cargo_tanks) / len(state.cargo_tanks)
        avg_temp = sum(t.temp_bottom_k for t in state.cargo_tanks) / len(state.cargo_tanks)
        state.bog_generation_kg_h = bog_generation_rate(
            avg_pressure, state.sea_temp_c, avg_temp, fill_pct,
            insulation_quality=0.95, num_tanks=len(state.cargo_tanks),
            tank_capacity_m3=state.tank_capacity_m3,
        )
        if state.storm.active and state.storm.intensity > 0.5:
            state.bog_generation_kg_h *= 1.2

        # Engine gas demand from shaft power × SFOC (1st law: energy in = work out)
        engine_demand_kg_h = 0.0
        if state.engine_running and state.shaft_power_kw > 0:
            sfoc = max(state.sfoc_actual, 120.0)
            engine_demand_kg_h = state.shaft_power_kw * sfoc / 1000.0

        # Available LNG above heel
        available_lng_kg = sum(
            max(0.0, t.level_m3 - t.capacity_m3 * self.HEEL_FRACTION)
            for t in state.cargo_tanks
        ) * 450.0

        if available_lng_kg > 1.0 and engine_demand_kg_h > 0:
            state.bog_to_engine_kg_h = engine_demand_kg_h
            state.engine_on_mgo = False
        elif available_lng_kg <= 1.0 and state.engine_running:
            # Heel exhausted → changeover to MGO fuel mode
            state.bog_to_engine_kg_h = 0.0
            state.engine_on_mgo = True
        else:
            state.bog_to_engine_kg_h = 0.0
            state.engine_on_mgo = False

        # Forced boil-off covers demand above natural BOG
        state.forced_bog_kg_h = max(0.0, state.bog_to_engine_kg_h - state.bog_generation_kg_h)

        # Surplus natural BOG → reliquefaction (returns to tank) or GCU (burned)
        surplus = max(0.0, state.bog_generation_kg_h - state.bog_to_engine_kg_h)
        if state.reliq_active:
            state.bog_to_reliq_kg_h = surplus * 0.9
        else:
            state.bog_to_reliq_kg_h = 0.0
        state.bog_to_gcu_kg_h = surplus - state.bog_to_reliq_kg_h

        # Tank mass removal: natural evaporation + forced vaporization,
        # minus reliquefaction return. Distributed proportionally to ullage.
        removal_kg = (state.bog_generation_kg_h + state.forced_bog_kg_h
                      - state.bog_to_reliq_kg_h) * dt_hours
        removal_m3 = removal_kg / 450.0
        total_removable = sum(
            max(0.0, t.level_m3 - t.capacity_m3 * self.HEEL_FRACTION)
            for t in state.cargo_tanks
        )
        for tank in state.cargo_tanks:
            removable = max(0.0, tank.level_m3 - tank.capacity_m3 * self.HEEL_FRACTION)
            if total_removable > 0.001:
                share = removal_m3 * (removable / total_removable)
            else:
                share = 0.0
            tank.level_m3 = max(tank.capacity_m3 * self.HEEL_FRACTION,
                                tank.level_m3 - min(share, removable))
            tank.pressure_bar = max(1.0, tank.pressure_bar - 0.0001 * dt_hours * 10)
        # Note: the dedicated LNG fuel tank is only replenished by bunkering
        # in port — engine gas comes from cargo tanks as BOG (no double drain).


from simulator import TankState

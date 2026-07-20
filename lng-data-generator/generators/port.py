import numpy as np
from simulator import VesselState


class PortGenerator:
    """Handles port-phase kinematics only. Phase lifecycle transitions are
    owned by VoyageGenerator (sea_passage -> arrival -> cargo ops -> port_stay
    -> departure). This generator zeroes speed/engine for stationary phases
    and simulates slow-speed maneuvers for anchorage/berthing/canal phases."""

    STATIONARY_PHASES = ("port_stay", "loading", "discharging")

    def __init__(self, config):
        self.config = config

    def step(self, state: VesselState, dt_seconds: float):
        dt_hours = dt_seconds / 3600.0
        if state.phase in self.STATIONARY_PHASES:
            state.sog = 0.0
            state.stw = 0.0
            state.rpm = 0.0
            state.shaft_power_kw = 0.0
            state.engine_running = False
            state.engine_load_pct = 0.0
        elif state.phase == "anchorage":
            state.sog = 0.0
            state.stw = 0.0
            state.heading = (state.heading + np.random.normal(0, 0.5)) % 360
            state.engine_running = False
            state.engine_load_pct = 0.0
        elif state.phase == "berthing":
            state.sog = max(0, state.sog - 1.0 * dt_hours)
            state.stw = state.sog
        elif state.phase == "canal_transit":
            state.sog = max(0.0, min(8.0, 6.0 + np.random.normal(0, 0.3)))
            state.stw = state.sog
            state.engine_load_pct = 25.0 + np.random.normal(0, 2)
        elif state.phase == "departure":
            # Voyage generator ramps speed; just keep engine on
            state.engine_running = True

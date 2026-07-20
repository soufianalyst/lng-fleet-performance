import numpy as np
from simulator import VesselState


class BallastGenerator:
    """Stability model: draft, trim, heel, displacement, GM.
    Displacement via mass balance (lightweight + cargo + ballast + fuel/stores)
    — always physically consistent, unlike a fixed-Cb draft formula."""

    LIGHTWEIGHT_MT = 36000.0   # typical 145-185k m³ LNGC lightweight
    STORES_FUEL_MT = 2500.0    # fuel, lube oil, fresh water, stores

    def __init__(self, config):
        self.config = config

    def step(self, state: VesselState, dt_seconds: float):
        dt_hours = dt_seconds / 3600.0
        if not state.cargo_tanks:
            return
        cargo_fill = sum(t.level_m3 / t.capacity_m3 for t in state.cargo_tanks) / len(state.cargo_tanks)
        # Drafts: ~8.5 m ballast / ~11.5 m laden for a 174k m³ LNGC
        draft_target_f = 8.5 + 3.0 * cargo_fill
        draft_target_a = draft_target_f + 0.2  # slight stern trim
        state.ballast.draft_f_m += (draft_target_f - state.ballast.draft_f_m) * 0.01 + np.random.normal(0, 0.005)
        state.ballast.draft_a_m += (draft_target_a - state.ballast.draft_a_m) * 0.01 + np.random.normal(0, 0.005)
        state.ballast.trim_m = state.ballast.draft_a_m - state.ballast.draft_f_m
        # Heel from waves
        heel_target = 0.0
        if state.wave_height_m > 3.0:
            heel_target = np.random.normal(0, 0.5)
        state.ballast.heel_deg += (heel_target - state.ballast.heel_deg) * 0.05
        # Ballast water inversely proportional to cargo fill
        state.ballast.ballast_water_mt = max(0, 15000.0 * (1.0 - cargo_fill))
        # Displacement via mass balance
        state.ballast.displacement_mt = (
            self.LIGHTWEIGHT_MT
            + state.cargo_qty_mt
            + state.ballast.ballast_water_mt
            + self.STORES_FUEL_MT
        )
        # GM: 1.5-3.0 m realistic for LNGC (stiffer in ballast)
        gm_target = 2.8 - 1.1 * cargo_fill
        state.ballast.gm_m += (gm_target - state.ballast.gm_m) * 0.01 + np.random.normal(0, 0.02)
        state.ballast.gm_m = max(1.0, min(4.0, state.ballast.gm_m))

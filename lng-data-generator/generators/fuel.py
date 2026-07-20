import numpy as np
from simulator import VesselState


class FuelGenerator:
    def __init__(self, config):
        self.config = config

    def step(self, state: VesselState, dt_seconds: float):
        dt_hours = dt_seconds / 3600.0
        # Bunkering during port calls — top up fuel tanks
        if state.phase in ("loading", "discharging", "port_stay"):
            self._handle_bunkering(state, dt_hours)
        aux_fuel = sum(
            aux.load_kw * aux.sfoc_g_kwh / 1e6 * dt_hours
            for aux in state.aux_engines if aux.running
        )
        state.fuel.mgo_level_mt -= aux_fuel
        state.fuel.mgo_level_mt = max(0, state.fuel.mgo_level_mt)
        state.total_fuel_mgo_mt += aux_fuel
        # GCU burns surplus BOG (also in port with engine off) — count as LNG fuel
        gcu_mt = state.bog_to_gcu_kg_h * dt_hours / 1000.0
        state.total_fuel_lng_mt += gcu_mt
        if not state.engine_running:
            return
        # Main engine fuel accounting (BOG from cargo tanks tracked there)
        if state.engine_on_mgo:
            mgo_main_mt = (state.shaft_power_kw * max(state.sfoc_actual, 120.0)
                           * 50000.0 / 42700.0) * dt_hours / 1e6
            state.fuel.mgo_level_mt = max(0, state.fuel.mgo_level_mt - mgo_main_mt)
            state.total_fuel_mgo_mt += mgo_main_mt
        else:
            lng_rate_kg_h = state.bog_to_engine_kg_h
            lng_consumed_mt = lng_rate_kg_h * dt_hours / 1000.0
            state.total_fuel_lng_mt += lng_consumed_mt
        pilot_rate_kg_h = state.engine_load_pct / 100.0 * 50.0
        pilot_consumed_mt = pilot_rate_kg_h * dt_hours / 1000.0
        state.fuel.pilot_level_mt -= pilot_consumed_mt
        state.fuel.pilot_level_mt = max(0, state.fuel.pilot_level_mt)
        state.total_fuel_mgo_mt += pilot_consumed_mt

    def _handle_bunkering(self, state: VesselState, dt_hours: float):
        """Refuel LNG fuel tank, MGO and pilot while alongside."""
        ft = state.fuel
        bunk_rate_lng = 400.0 * dt_hours   # m3/h truck-to-ship LNG fuel
        bunk_rate_mgo = 150.0 * dt_hours   # mt/h MGO bunkering
        if ft.lng_level_m3 < ft.lng_capacity_m3:
            ft.lng_level_m3 = min(ft.lng_capacity_m3, ft.lng_level_m3 + bunk_rate_lng)
        if ft.mgo_level_mt < ft.mgo_capacity_mt:
            ft.mgo_level_mt = min(ft.mgo_capacity_mt, ft.mgo_level_mt + bunk_rate_mgo)
        if ft.pilot_level_mt < ft.pilot_capacity_mt:
            ft.pilot_level_mt = min(ft.pilot_capacity_mt, ft.pilot_level_mt + 20.0 * dt_hours)

    def generate_aux_engines(self, state: VesselState, num_gen: int = 3):
        """Create gensets: 1 running, rest on standby (realistic port/sea config)."""
        state.aux_engines = []
        for i in range(num_gen):
            state.aux_engines.append(AuxEngineState(
                engine_id=i + 1,
                running=(i == 0),  # only first genset online initially
                load_kw=900.0 if i == 0 else 0.0,
                sfoc_g_kwh=200.0 + np.random.normal(0, 3),
                running_hours=5000.0 + np.random.uniform(0, 2000),
                fuel_type="MGO",
            ))

    def update_aux_loads(self, state: VesselState):
        """Hotel load shared across online gensets; start/stop units by demand."""
        # Total hotel/electric load demand by phase (kW)
        if state.phase == "sea_passage":
            demand = 1100.0 + np.random.normal(0, 50)
        elif state.phase in ("loading", "discharging"):
            demand = 2800.0 + np.random.normal(0, 100)  # cargo pumps
        elif state.phase in ("port_stay", "anchorage", "berthing", "arrival"):
            demand = 700.0 + np.random.normal(0, 40)
        elif state.phase == "departure":
            demand = 1400.0 + np.random.normal(0, 50)
        else:
            demand = 1000.0 + np.random.normal(0, 50)
        demand = max(300.0, demand)

        genset_rated = 1800.0  # kW per unit continuous rating
        # Units needed: keep each online unit between 40-85% load
        units_needed = max(1, min(len(state.aux_engines),
                                  int(np.ceil(demand / (genset_rated * 0.85)))))
        for i, aux in enumerate(state.aux_engines):
            if i < units_needed:
                if not aux.running:
                    aux.running = True
                aux.load_kw = demand / units_needed + np.random.normal(0, 20)
                aux.load_kw = max(200.0, aux.load_kw)
                # SFOC curve: best near 75-85% load
                load_frac = aux.load_kw / genset_rated
                aux.sfoc_g_kwh = 195.0 + (load_frac - 0.8) ** 2 * 40.0
                aux.running_hours += 0.008
            else:
                aux.running = False
                aux.load_kw = 0.0


from simulator import AuxEngineState

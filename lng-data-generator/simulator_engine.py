import os
import yaml
import time
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from simulator import VesselState, TankState, FuelState, BallastState
from generators.voyage import VoyageGenerator
from generators.weather import WeatherGenerator
from generators.engine import EngineGenerator
from generators.cargo import CargoGenerator
from generators.bog import BOGGenerator
from generators.fuel import FuelGenerator
from generators.emissions import EmissionsGenerator
from generators.alarms import AlarmGenerator
from generators.maintenance import MaintenanceGenerator
from generators.ballast import BallastGenerator
from generators.port import PortGenerator
from generators.kpi import KPIGenerator
from writers import CSVWriter
from writers.sqlite_writer import SQLiteWriter
from writers.parquet_writer import ParquetWriter


class TelemetrySimulator:
    def __init__(self, config_dir: str = "config"):
        self.config = self._load_configs(config_dir)
        self.gen_config = self.config["generator"]
        self.timestep = self.gen_config.get("timestep_seconds", 30)
        self.voyage_gen = VoyageGenerator(self.config)
        self.weather_gen = WeatherGenerator(self.config)
        self.engine_gen = EngineGenerator(self.config)
        self.cargo_gen = CargoGenerator(self.config)
        self.bog_gen = BOGGenerator(self.config)
        self.fuel_gen = FuelGenerator(self.config)
        self.emissions_gen = EmissionsGenerator(self.config)
        self.alarms_gen = AlarmGenerator(self.config)
        self.maintenance_gen = MaintenanceGenerator(self.config)
        self.ballast_gen = BallastGenerator(self.config)
        self.port_gen = PortGenerator(self.config)
        self.kpi_gen = KPIGenerator(self.config)
        self.vessels: Dict[str, VesselState] = {}
        self.writers = {}
        self.buffer: Dict[str, List[Dict]] = {}
        self.buffer_size = self.gen_config.get("output", {}).get("csv_chunk_size", 10000)

    def _load_configs(self, config_dir: str) -> dict:
        configs = {}
        for name in ["vessels", "routes", "weather", "generator"]:
            path = os.path.join(config_dir, f"{name}.yaml")
            with open(path) as f:
                raw = yaml.safe_load(f)
                if name in raw:
                    configs[name] = raw[name]
                else:
                    configs[name] = raw
        return configs

    def initialize(self, vessel_ids: Optional[List[str]] = None, scenario: str = "normal_voyage"):
        vessel_cfgs = self.config["vessels"]
        if isinstance(vessel_cfgs, dict):
            vessel_cfgs = vessel_cfgs.get("vessels", [])
        route_cfgs = self.config["routes"]
        if isinstance(route_cfgs, dict):
            route_cfgs = route_cfgs.get("routes", [])
        if vessel_ids:
            vessel_cfgs = [v for v in vessel_cfgs if v["id"] in vessel_ids]
        for vc in vessel_cfgs:
            state = self._create_vessel_state(vc)
            route = self._assign_route(vc["id"], route_cfgs)
            self.voyage_gen.initialize_voyage(state, route)
            self.weather_gen.initialize(state)
            self.fuel_gen.generate_aux_engines(state)
            self.cargo_gen.initialize_tanks(state, vc)
            self.vessels[vc["id"]] = state
            self.buffer[vc["id"]] = []
        output_cfg = self.gen_config.get("output", {})
        output_dir = output_cfg.get("directory", "output")
        formats = output_cfg.get("formats", ["csv", "sqlite"])
        if "csv" in formats:
            self.writers["csv"] = CSVWriter(output_dir, output_cfg.get("csv_chunk_size", 10000))
        if "sqlite" in formats:
            self.writers["sqlite"] = SQLiteWriter(output_dir, output_cfg.get("sqlite_db", "lng_telemetry.db"))
        if "parquet" in formats:
            self.writers["parquet"] = ParquetWriter(output_dir)

    def _create_vessel_state(self, vc: dict) -> VesselState:
        ft = vc.get("fuel_tanks", {})
        try:
            vessel_num = int(vc["id"].split("-")[1])
        except (ValueError, IndexError):
            vessel_num = 0
        return VesselState(
            vessel_id=vc["id"],
            vessel_name=vc["name"],
            imo=vc["imo"],
            propulsion_type=vc["type"],
            engine_mcr_kw=vc["engine_mcr_kw"],
            engine_sfoc_rated=vc["engine_sfoc_g_kwh"],
            service_speed_kn=vc["service_speed_kn"],
            gt=vc["gt"],
            dwt=vc["dwt"],
            lwl_m=vc["loa_m"] * 0.96,  # LWL ≈ 96% of LOA
            beam_m=vc["beam_m"],
            num_cargo_tanks=len(vc.get("cargo_tanks", [])),
            tank_capacity_m3=vc.get("cargo_tanks", [{}])[0].get("capacity_m3", 43500) if vc.get("cargo_tanks") else 43500,
            cargo_capacity_mt=vc["cargo_capacity_m3"] * 0.45,
            hull_fouling_pct=1.0 + (vessel_num % 5) * 0.5,          # 1.0-3.0% initial
            fouling_rate_per_day=0.01 + (vessel_num % 6) * 0.008,   # 0.01-0.05 %/day
            fuel=FuelState(
                lng_level_m3=ft.get("lng_level_init_m3", 3800),
                lng_capacity_m3=ft.get("lng_capacity_m3", 4500),
                mgo_level_mt=ft.get("mgo_level_init_mt", 2000),
                mgo_capacity_mt=ft.get("mgo_capacity_mt", 2500),
                vlsfo_level_mt=ft.get("vlsfo_level_init_mt", 0),
                vlsfo_capacity_mt=ft.get("vlsfo_capacity_mt", 0),
                pilot_level_mt=ft.get("pilot_fuel_level_init_mt", 80),
                pilot_capacity_mt=ft.get("pilot_fuel_capacity_mt", 100),
            ),
        )

    def _assign_route(self, vessel_id: str, routes: list) -> dict:
        # Deterministic assignment (Python hash() is randomized per process)
        try:
            num = int(vessel_id.split("-")[1])
        except (ValueError, IndexError):
            num = 0
        return routes[num % len(routes)]

    def run(self, duration_days: float = 1.0, progress_callback=None):
        total_steps = int(duration_days * 86400 / self.timestep)
        print(f"Simulating {len(self.vessels)} vessels x {total_steps} steps "
              f"({duration_days} days, {self.timestep}s timestep)")
        start_time = time.time()
        for step_num in range(total_steps):
            sim_time = step_num * self.timestep
            for vessel_id, state in self.vessels.items():
                state.time = sim_time
                self.weather_gen.step(state, self.timestep)
                self.voyage_gen.step(state, self.timestep)
                self.engine_gen.step(state, self.timestep)
                self.cargo_gen.step(state, self.timestep)
                self.bog_gen.step(state, self.timestep)
                self.fuel_gen.step(state, self.timestep)
                self.fuel_gen.update_aux_loads(state)
                self.emissions_gen.step(state, self.timestep)
                self.alarms_gen.step(state, self.timestep)
                self.maintenance_gen.step(state, self.timestep)
                self.ballast_gen.step(state, self.timestep)
                self.port_gen.step(state, self.timestep)
                self.kpi_gen.step(state, self.timestep)
                self.buffer[vessel_id].append(state.to_dict())
                if len(self.buffer[vessel_id]) >= self.buffer_size:
                    self._flush_buffer(vessel_id)
            if progress_callback and step_num % 100 == 0:
                pct = step_num / total_steps * 100
                elapsed = time.time() - start_time
                rate = (step_num + 1) / elapsed if elapsed > 0 else 0
                eta = (total_steps - step_num - 1) / rate if rate > 0 else 0
                progress_callback(pct, step_num, total_steps, eta)
        self._flush_all()
        self._finalize()
        elapsed = time.time() - start_time
        print(f"\nDone in {elapsed:.1f}s")
        self._print_summary()

    def _flush_buffer(self, vessel_id: str):
        records = self.buffer[vessel_id]
        if not records:
            return
        for writer in self.writers.values():
            writer.write_batch(vessel_id, records)
        self.buffer[vessel_id] = []

    def _flush_all(self):
        for vessel_id in list(self.buffer.keys()):
            self._flush_buffer(vessel_id)

    def _finalize(self):
        for writer in self.writers.values():
            writer.finalize()

    def _print_summary(self):
        total_records = 0
        for vessel_id, state in self.vessels.items():
            vessel_records = 0
            for writer in self.writers.values():
                counts = writer.get_counts()
                vessel_records = counts.get(vessel_id, 0)
            total_records += vessel_records
            print(f"  {state.vessel_name}: {vessel_records:,} records | "
                  f"Distance: {state.distance_sailed_nm:,.0f} nm | "
                  f"CO2: {state.total_co2_mt:.1f} mt | "
                  f"Cargo: {state.cargo_qty_mt:,.0f} mt")
        print(f"  Total: {total_records:,} telemetry records")
        for name, writer in self.writers.items():
            counts = writer.get_counts()
            total = sum(counts.values())
            print(f"  {name.upper()}: {total:,} records")

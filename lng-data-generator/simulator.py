import math
import yaml
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from utils.physics import (
    haversine_nm, bearing_deg, interpolate_position,
    sfoc_curve, exhaust_temp_from_load, bog_generation_rate,
    calculate_displacement, fuel_consumption_kg_h, co2_from_fuel,
    nox_from_power, sox_from_fuel, methane_slip_g_kwh,
    speed_from_power, LHV, EMISSION_FACTORS,
)
from utils.random_utils import AR1Process, StormEvent


@dataclass
class TankState:
    name: str
    capacity_m3: float
    level_m3: float
    pressure_bar: float = 1.1
    temp_top_k: float = 111.5
    temp_mid_k: float = 111.3
    temp_bottom_k: float = 111.1
    temp_vapor_k: float = 112.0


@dataclass
class AuxEngineState:
    engine_id: int
    running: bool = True
    load_kw: float = 1500.0
    sfoc_g_kwh: float = 220.0
    running_hours: float = 0.0
    fuel_type: str = "MGO"


@dataclass
class FuelState:
    lng_level_m3: float = 3800.0
    lng_capacity_m3: float = 4500.0
    mgo_level_mt: float = 2000.0
    mgo_capacity_mt: float = 2500.0
    vlsfo_level_mt: float = 0.0
    vlsfo_capacity_mt: float = 0.0
    pilot_level_mt: float = 80.0
    pilot_capacity_mt: float = 100.0


@dataclass
class BallastState:
    draft_f_m: float = 8.0
    draft_a_m: float = 8.2
    trim_m: float = 0.2
    heel_deg: float = 0.0
    displacement_mt: float = 65000.0
    gm_m: float = 12.0
    ballast_water_mt: float = 15000.0


@dataclass
class AlarmState:
    alarm_type: str
    severity: str  # info, warning, critical
    active: bool = True
    timestamp: float = 0.0
    description: str = ""


@dataclass
class VesselState:
    vessel_id: str
    vessel_name: str
    imo: int
    propulsion_type: str
    engine_mcr_kw: float
    engine_sfoc_rated: float
    service_speed_kn: float
    gt: float
    dwt: float
    lwl_m: float
    beam_m: float
    num_cargo_tanks: int
    tank_capacity_m3: float

    time: float = 0.0
    phase: str = "sea_passage"

    lat: float = 0.0
    lon: float = 0.0
    heading: float = 0.0
    cog: float = 0.0
    sog: float = 0.0
    stw: float = 0.0
    rudder_angle: float = 0.0
    rpm: float = 80.0
    shaft_power_kw: float = 20000.0

    engine_load_pct: float = 70.0
    exhaust_temp_c: float = 350.0
    scavenge_air_temp_c: float = 45.0
    turbo_rpm: float = 12000.0
    sfoc_actual: float = 165.0
    engine_running: bool = True

    fuel: FuelState = field(default_factory=FuelState)
    ballast: BallastState = field(default_factory=BallastState)
    cargo_tanks: List[TankState] = field(default_factory=list)
    aux_engines: List[AuxEngineState] = field(default_factory=list)

    bog_generation_kg_h: float = 2500.0
    bog_to_engine_kg_h: float = 2200.0
    bog_to_gcu_kg_h: float = 300.0
    bog_to_reliq_kg_h: float = 0.0
    forced_bog_kg_h: float = 0.0
    engine_on_mgo: bool = False
    reliq_active: bool = False

    total_fuel_lng_mt: float = 0.0
    total_fuel_mgo_mt: float = 0.0
    total_fuel_vlsfo_mt: float = 0.0
    total_co2_mt: float = 0.0
    total_nox_mt: float = 0.0
    total_sox_mt: float = 0.0
    total_ch4_mt: float = 0.0
    distance_sailed_nm: float = 0.0

    route_index: int = 0
    waypoint_index: int = 0
    total_route_distance_nm: float = 0.0
    distance_to_go_nm: float = 0.0
    route_waypoints: List[Dict] = field(default_factory=list)
    route_progress_nm: float = 0.0
    port_timer: float = 0.0
    leg_type: str = "laden"  # "laden" or "ballast"
    leg_co2_mt: float = 0.0
    leg_distance_nm: float = 0.0
    weather_region: str = ""

    alarms: List[AlarmState] = field(default_factory=list)
    storm: StormEvent = field(default_factory=StormEvent)
    hull_fouling_pct: float = 2.0
    fouling_rate_per_day: float = 0.03
    running_hours_engine: float = 5000.0
    last_overhaul_hours: float = 0.0

    port_state: str = ""  # "", "anchorage", "berthing", "loading", "discharging"
    cargo_operation_progress: float = 0.0
    cargo_loaded_mt: float = 0.0
    cargo_capacity_mt: float = 75000.0

    ar1_wind: Optional[AR1Process] = None
    ar1_wave: Optional[AR1Process] = None
    ar1_swell: Optional[AR1Process] = None
    ar1_sea_temp: Optional[AR1Process] = None
    ar1_air_temp: Optional[AR1Process] = None
    ar1_pressure: Optional[AR1Process] = None
    ar1_visibility: Optional[AR1Process] = None

    wind_speed_kn: float = 10.0
    wind_direction_deg: float = 180.0
    wave_height_m: float = 1.5
    wave_direction_deg: float = 180.0
    swell_height_m: float = 0.5
    sea_temp_c: float = 20.0
    air_temp_c: float = 22.0
    pressure_hpa: float = 1013.0
    visibility_nm: float = 8.0

    cargo_qty_mt: float = 0.0
    speed_fuel_per_nm: float = 0.0
    efficiency_pct: float = 0.0
    cargo_loss_rate: float = 0.0
    power_efficiency: float = 0.0
    carbon_intensity: float = 0.0
    eeoi: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "timestamp": self.time,
            "vessel_id": self.vessel_id,
            "vessel_name": self.vessel_name,
            "imo": self.imo,
            "phase": self.phase,
            "lat": round(self.lat, 6),
            "lon": round(self.lon, 6),
            "heading": round(self.heading, 1),
            "cog": round(self.cog, 1),
            "sog": round(self.sog, 2),
            "stw": round(self.stw, 2),
            "rudder_angle": round(self.rudder_angle, 1),
            "rpm": round(self.rpm, 1),
            "shaft_power_kw": round(self.shaft_power_kw, 1),
            "engine_load_pct": round(self.engine_load_pct, 1),
            "engine_running": self.engine_running,
            "exhaust_temp_c": round(self.exhaust_temp_c, 1),
            "scavenge_air_temp_c": round(self.scavenge_air_temp_c, 1),
            "turbo_rpm": round(self.turbo_rpm, 0),
            "sfoc_actual": round(self.sfoc_actual, 1),
            "fuel_lng_level_m3": round(self.fuel.lng_level_m3, 1),
            "fuel_mgo_level_mt": round(self.fuel.mgo_level_mt, 1),
            "fuel_vlsfo_level_mt": round(self.fuel.vlsfo_level_mt, 1),
            "fuel_pilot_level_mt": round(self.fuel.pilot_level_mt, 1),
            "bog_generation_kg_h": round(self.bog_generation_kg_h, 1),
            "bog_to_engine_kg_h": round(self.bog_to_engine_kg_h, 1),
            "bog_to_gcu_kg_h": round(self.bog_to_gcu_kg_h, 1),
            "bog_to_reliq_kg_h": round(self.bog_to_reliq_kg_h, 1),
            "forced_bog_kg_h": round(self.forced_bog_kg_h, 1),
            "engine_on_mgo": self.engine_on_mgo,
            "tank_pressure_bar": round(self.cargo_tanks[0].pressure_bar if self.cargo_tanks else 1.1, 3),
            "cargo_qty_mt": round(self.cargo_qty_mt, 1),
            "draft_f_m": round(self.ballast.draft_f_m, 2),
            "draft_a_m": round(self.ballast.draft_a_m, 2),
            "trim_m": round(self.ballast.trim_m, 2),
            "heel_deg": round(self.ballast.heel_deg, 2),
            "displacement_mt": round(self.ballast.displacement_mt, 1),
            "gm_m": round(self.ballast.gm_m, 2),
            "wind_speed_kn": round(self.wind_speed_kn, 1),
            "wind_direction_deg": round(self.wind_direction_deg, 1),
            "wave_height_m": round(self.wave_height_m, 2),
            "swell_height_m": round(self.swell_height_m, 2),
            "sea_temp_c": round(self.sea_temp_c, 1),
            "air_temp_c": round(self.air_temp_c, 1),
            "pressure_hpa": round(self.pressure_hpa, 1),
            "visibility_nm": round(self.visibility_nm, 1),
            "distance_sailed_nm": round(self.distance_sailed_nm, 1),
            "distance_to_go_nm": round(self.distance_to_go_nm, 1),
            "leg_distance_nm": round(self.leg_distance_nm, 1),
            "leg_co2_mt": round(self.leg_co2_mt, 3),
            "leg_type": self.leg_type,
            "total_fuel_lng_mt": round(self.total_fuel_lng_mt, 3),
            "total_fuel_mgo_mt": round(self.total_fuel_mgo_mt, 3),
            "total_co2_mt": round(self.total_co2_mt, 3),
            "total_nox_mt": round(self.total_nox_mt, 4),
            "total_sox_mt": round(self.total_sox_mt, 4),
            "total_ch4_mt": round(self.total_ch4_mt, 4),
            "running_hours_engine": round(self.running_hours_engine, 1),
            "hull_fouling_pct": round(self.hull_fouling_pct, 1),
        }
        for i, tank in enumerate(self.cargo_tanks):
            prefix = f"tank{i+1}"
            d[f"{prefix}_level_m3"] = round(tank.level_m3, 1)
            d[f"{prefix}_pressure_bar"] = round(tank.pressure_bar, 3)
            d[f"{prefix}_temp_top_k"] = round(tank.temp_top_k, 2)
            d[f"{prefix}_temp_mid_k"] = round(tank.temp_mid_k, 2)
            d[f"{prefix}_temp_bottom_k"] = round(tank.temp_bottom_k, 2)
            d[f"{prefix}_temp_vapor_k"] = round(tank.temp_vapor_k, 2)
        for i, aux in enumerate(self.aux_engines):
            prefix = f"aux{i+1}"
            d[f"{prefix}_running"] = aux.running
            d[f"{prefix}_load_kw"] = round(aux.load_kw, 1)
            d[f"{prefix}_sfoc"] = round(aux.sfoc_g_kwh, 1)
        for alarm in self.alarms:
            if alarm.active:
                d[f"alarm_{alarm.alarm_type}"] = alarm.severity
        d["eeoi"] = round(self.eeoi, 4)
        d["carbon_intensity"] = round(self.carbon_intensity, 2)
        return d

    def tank_columns(self) -> List[str]:
        cols = []
        for i in range(len(self.cargo_tanks)):
            prefix = f"tank{i+1}"
            for suffix in ["level_m3", "pressure_bar", "temp_top_k", "temp_mid_k", "temp_bottom_k", "temp_vapor_k"]:
                cols.append(f"{prefix}_{suffix}")
        return cols

    def aux_columns(self) -> List[str]:
        cols = []
        for i in range(len(self.aux_engines)):
            prefix = f"aux{i+1}"
            for suffix in ["running", "load_kw", "sfoc"]:
                cols.append(f"{prefix}_{suffix}")
        return cols

    def all_columns(self) -> List[str]:
        return list(self.to_dict().keys())

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class Vessel:
    id: UUID
    imo: int
    name: str
    flag: str
    capacity_m3: int
    build_year: int
    engine_type: str
    tank_type: str
    design_draft_m: float
    design_speed_kn: float
    max_power_kw: float


@dataclass
class Voyage:
    id: UUID
    vessel_id: UUID
    voyage_number: str
    departure_port: str
    arrival_port: str
    departure_time: datetime
    arrival_time: datetime
    cargo_laden: bool
    cargo_quantity_m3: float
    status: str
    total_distance_nm: float


@dataclass
class TelemetryPoint:
    time: datetime
    vessel_id: UUID
    voyage_id: UUID
    latitude: float
    longitude: float
    sog_kn: float
    cog_deg: float
    heading_deg: float
    engine_speed_rpm: float
    shaft_power_kw: float
    sfoc_g_per_kwh: float
    fuel_flow_t_per_day: float
    bog_flow_t_per_day: float
    pilot_fuel_flow_t_per_day: float
    engine_load_pct: float
    exhaust_temp_c: float
    scavenge_air_pressure_bar: float
    turbocharger_speed_rpm: float
    fuel_type: str
    fuel_sulfur_pct: float
    methane_slip_g_per_kwh: float
    cargo_tank_temp_c: float
    cargo_tank_pressure_bar: float
    cargo_tank_level_pct: float
    cargo_tank_top_temp_c: float
    cargo_tank_mid_temp_c: float
    cargo_tank_bot_temp_c: float
    bor_pct_per_day: float
    wind_speed_kn: float
    wind_direction_deg: float
    wave_height_m: float
    wave_period_s: float
    air_temp_c: float
    sea_temp_c: float
    current_speed_kn: float
    current_direction_deg: float
    air_pressure_hpa: float
    in_eca_zone: bool
    eca_zone_name: str
    scrubber_operating: bool
    co2_t_per_day: float
    nox_g_per_kwh: float
    sox_g_per_kwh: float
    hull_draft_fwd_m: float
    hull_draft_aft_m: float
    hull_trim_m: float
    water_depth_m: float
    quality_flag: int


@dataclass
class BOGRecord:
    id: UUID
    vessel_id: UUID
    voyage_id: UUID
    recorded_at: datetime
    tank_id: int
    tank_level_pct: float
    tank_temp_c: float
    tank_pressure_bar: float
    bor_pct_per_day: float
    bog_flow_t_per_day: float
    bog_to_engine_pct: float
    bog_to_gcu_pct: float
    bog_to_reliquefaction_pct: float
    reliquefaction_power_kw: float
    stratification_index: float
    rollover_risk: str


@dataclass
class ECAEvent:
    id: UUID
    vessel_id: UUID
    voyage_id: UUID
    eca_zone_name: str
    entry_time: datetime
    exit_time: datetime
    fuel_type_before: str
    fuel_type_after: str
    fuel_switch_completed: bool
    compliance_status: str
    scrubber_mode: str
    nox_aftertreatment_active: bool


@dataclass
class CIIRecord:
    id: UUID
    vessel_id: UUID
    year: int
    month: int
    co2_total_t: float
    transport_work_t_nm: float
    cii_calculated: float
    cii_required_c: float
    cii_rating: str
    running_annual_cii: float


@dataclass
class CharterParty:
    id: UUID
    vessel_id: UUID
    charterer_name: str
    charter_type: str
    start_date: datetime
    end_date: datetime
    warranted_speed_kn: float
    warranted_consumption_t_per_day: float
    warranted_bor_pct_per_day: float
    speed_tolerance_pct: float
    weather_allowance_beaufort_max: int
    demurrage_rate_usd_per_day: float


@dataclass
class CharterVerification:
    id: UUID
    charter_id: UUID
    voyage_id: UUID
    verified_speed_kn: float
    verified_consumption_t_per_day: float
    weather_correction_applied: bool
    weather_adjusted_speed_kn: float
    weather_adjusted_consumption_t_per_day: float
    speed_compliance: bool
    consumption_compliance: bool
    off_hire_hours: float
    claim_amount_usd: float


@dataclass
class MaintenancePrediction:
    id: UUID
    vessel_id: UUID
    component: str
    parameter: str
    predicted_value: float
    actual_value: float
    deviation_pct: float
    rul_days: int
    confidence_pct: float
    anomaly_score: float
    model_version: str
    predicted_at: datetime

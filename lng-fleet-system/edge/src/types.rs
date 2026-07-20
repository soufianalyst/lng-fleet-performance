use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

// ---------------------------------------------------------------------------
// Raw sensor telemetry
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EngineTelemetry {
    pub vessel_id: String,
    pub timestamp: DateTime<Utc>,

    // Main engine (ME)
    pub me_rpm: f64,
    pub me_power_kw: f64,
    pub me_torque_nm: f64,
    pub me_scavenge_air_pressure_bar: f64,
    pub me_exhaust_gas_temp_c: f64,
    pub me_cylinder_exhaust_temps_c: Vec<f64>,
    pub me_fuel_oil_flow_rate_kg_h: f64,
    pub me_fuel_oil_temp_c: f64,
    pub me_fuel_oil_pressure_bar: f64,
    pub me_jacket_cooling_water_temp_c: f64,
    pub me_lub_oil_pressure_bar: f64,
    pub me_lub_oil_temp_c: f64,

    // Auxiliary engines
    pub ae1_rpm: f64,
    pub ae1_power_kw: f64,
    pub ae2_rpm: f64,
    pub ae2_power_kw: f64,

    // Shaft
    pub shaft_power_kw: f64,
    pub shaft_rpm: f64,
    pub shaft_torque_nm: f64,
    pub thrust_bearing_temp_c: f64,

    // Propeller
    pub propeller_pitch_pct: f64,
    pub propeller_thrust_kn: f64,
    pub propeller_slip_pct: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CargoTelemetry {
    pub vessel_id: String,
    pub timestamp: DateTime<Utc>,

    // Cargo tanks (per tank, typically 4)
    pub tank_levels_pct: Vec<f64>,
    pub tank_temps_c: Vec<f64>,
    pub tank_vapor_pressures_bar: Vec<f64>,
    pub tank_liquid_density_kg_m3: Vec<f64>,

    // Boil-off
    pub bor_kg_h: f64,
    pub bor_rate_pct_per_day: f64,
    pub lng_vapor_temp_c: f64,

    // Cargo machinery
    pub hp_compressor_speed_rpm: f64,
    pub hp_compressor_discharge_pressure_bar: f64,
    pub lp_compressor_speed_rpm: f64,
    pub lp_compressor_suction_pressure_bar: f64,
    pub vaporizer_temp_c: f64,
    pub gas_heater_temp_c: f64,
    pub fuel_gas_pressure_bar: f64,
    pub fuel_gas_temp_c: f64,

    // Tank atmosphere
    pub o2_pct: f64,
    pub hydrocarbon_pct: f64,
    pub co2_pct: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuxTelemetry {
    pub vessel_id: String,
    pub timestamp: DateTime<Utc>,

    // Power generation
    pub main_switchboard_freq_hz: f64,
    pub main_switchboard_voltage_v: f64,
    pub total_power_kw: f64,
    pub power_demand_consumers_kw: f64,

    // Boilers
    pub boiler_pressure_bar: f64,
    pub boiler_temp_c: f64,
    pub boiler_fuel_flow_kg_h: f64,

    // HVAC
    pub engine_room_temp_c: f64,
    pub engine_room_humidity_pct: f64,
    pub cargo_control_room_temp_c: f64,
    pub bridge_room_temp_c: f64,

    // Ballast
    pub ballast_pump_status: bool,
    pub ballast_tank_levels_pct: Vec<f64>,

    // Fire & safety
    pub fire_main_line_pressure_bar: f64,
    pub sprinkler_flow_status: bool,
    pub co2_release_status: bool,
    pub gas_detection_alarm: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NavigationTelemetry {
    pub vessel_id: String,
    pub timestamp: DateTime<Utc>,

    pub latitude: f64,
    pub longitude: f64,
    pub speed_over_ground_knots: f64,
    pub course_over_ground_deg: f64,
    pub heading_deg: f64,
    pub draft_fore_m: f64,
    pub draft_aft_m: f64,
    pub depth_below_keel_m: f64,
    pub wind_speed_knots: f64,
    pub wind_direction_deg: f64,
    pub sea_state: f64,
    pub air_temp_c: f64,
    pub sea_water_temp_c: f64,
    pub eca_zone: Option<String>,
}

// ---------------------------------------------------------------------------
// Aggregated telemetry (5-minute window)
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AggregatedTelemetry {
    pub id: Uuid,
    pub vessel_id: String,
    pub window_start: DateTime<Utc>,
    pub window_end: DateTime<Utc>,
    pub n_samples: u32,

    pub engine: AggregatedEngine,
    pub cargo: AggregatedCargo,
    pub aux: AggregatedAux,
    pub navigation: AggregatedNavigation,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AggregatedEngine {
    pub me_power_kw: StatSummary,
    pub me_rpm: StatSummary,
    pub me_fuel_flow_kg_h: StatSummary,
    pub shaft_power_kw: StatSummary,
    pub me_exhaust_gas_temp_c: StatSummary,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AggregatedCargo {
    pub tank_levels_pct: Vec<StatSummary>,
    pub tank_vapor_pressures_bar: Vec<StatSummary>,
    pub bor_kg_h: StatSummary,
    pub fuel_gas_pressure_bar: StatSummary,
    pub fuel_gas_temp_c: StatSummary,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AggregatedAux {
    pub total_power_kw: StatSummary,
    pub main_switchboard_freq_hz: StatSummary,
    pub boiler_pressure_bar: StatSummary,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AggregatedNavigation {
    pub speed_over_ground_knots: StatSummary,
    pub latitude: f64,
    pub longitude: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StatSummary {
    pub mean: f64,
    pub min: f64,
    pub max: f64,
    pub std: f64,
    pub count: u32,
}

// ---------------------------------------------------------------------------
// Events
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnomalyEvent {
    pub id: Uuid,
    pub vessel_id: String,
    pub timestamp: DateTime<Utc>,
    pub channel: String,
    pub value: f64,
    pub z_score: f64,
    pub mean: f64,
    pub std: f64,
    pub severity: AnomalySeverity,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum AnomalySeverity {
    Warning,
    Critical,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ECAEvent {
    pub id: Uuid,
    pub vessel_id: String,
    pub timestamp: DateTime<Utc>,
    pub event_type: ECAEventType,
    pub zone: String,
    pub latitude: f64,
    pub longitude: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ECAEventType {
    Enter,
    Exit,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FuelSwitchEvent {
    pub id: Uuid,
    pub vessel_id: String,
    pub timestamp: DateTime<Utc>,
    pub from_fuel: String,
    pub to_fuel: String,
    pub sox_compliance: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CIIEvent {
    pub id: Uuid,
    pub vessel_id: String,
    pub timestamp: DateTime<Utc>,
    pub voyage_distance_nm: f64,
    pub fuel_consumption_tonnes: f64,
    pub cii_rating: f64,
    pub cii_grade: String,
    pub cumulative_cii: f64,
    pub required_cii: f64,
}

// ---------------------------------------------------------------------------
// Heartbeat & satellite messages
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Heartbeat {
    pub vessel_id: String,
    pub timestamp: DateTime<Utc>,
    pub uptime_seconds: u64,
    pub services_online: Vec<String>,
    pub queue_depth: usize,
    pub last_transmission: Option<DateTime<Utc>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum SatelliteMessage {
    Telemetry(AggregatedTelemetry),
    Anomaly(AnomalyEvent),
    ECA(ECAEvent),
    FuelSwitch(FuelSwitchEvent),
    CII(CIIEvent),
    Heartbeat(Heartbeat),
}

impl SatelliteMessage {
    pub fn message_type(&self) -> &'static str {
        match self {
            SatelliteMessage::Telemetry(_) => "telemetry",
            SatelliteMessage::Anomaly(_) => "anomaly",
            SatelliteMessage::ECA(_) => "eca",
            SatelliteMessage::FuelSwitch(_) => "fuel_switch",
            SatelliteMessage::CII(_) => "cii",
            SatelliteMessage::Heartbeat(_) => "heartbeat",
        }
    }

    pub fn priority(&self) -> u8 {
        match self {
            SatelliteMessage::Anomaly(_) | SatelliteMessage::ECA(_) => 0,
            SatelliteMessage::CII(_) => 1,
            SatelliteMessage::FuelSwitch(_) => 1,
            SatelliteMessage::Telemetry(_) => 2,
            SatelliteMessage::Heartbeat(_) => 2,
        }
    }
}

// ---------------------------------------------------------------------------
// Payload wrapper with compression metadata
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompressedPayload {
    pub vessel_id: String,
    pub algorithm: String,
    pub level: i32,
    pub original_size: usize,
    pub compressed_size: usize,
    pub data: Vec<u8>,
}

// ---------------------------------------------------------------------------
// Fuel type constants
// ---------------------------------------------------------------------------

pub const FUEL_HFO: &str = "HFO";
pub const FUEL_LSMGO: &str = "LSMGO";
pub const FUEL_LNG: &str = "LNG";
pub const FUEL_METHANOL: &str = "Methanol";

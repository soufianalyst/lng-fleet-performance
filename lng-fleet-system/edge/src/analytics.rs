use std::collections::VecDeque;
use std::sync::Arc;

use chrono::{DateTime, Duration, Utc};
use log::{debug, info, warn};
use tokio::sync::mpsc;
use tokio::time;
use uuid::Uuid;

use crate::config::Config;
use crate::eca::ECATracker;
use crate::types::*;

// ---------------------------------------------------------------------------
// Moving window buffer for per-channel statistics
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct StatBuffer {
    max_samples: usize,
    window: Duration,
    samples: VecDeque<(DateTime<Utc>, f64)>,
}

impl StatBuffer {
    pub fn new(max_samples: usize, window_seconds: i64) -> Self {
        Self {
            max_samples,
            window: Duration::seconds(window_seconds),
            samples: VecDeque::with_capacity(max_samples),
        }
    }

    pub fn push(&mut self, ts: DateTime<Utc>, value: f64) {
        self.samples.push_back((ts, value));
        if self.samples.len() > self.max_samples {
            self.samples.pop_front();
        }
        // Purge old samples outside the window
        let cutoff = ts - self.window;
        while let Some((t, _)) = self.samples.front() {
            if *t < cutoff {
                self.samples.pop_front();
            } else {
                break;
            }
        }
    }

    pub fn count(&self) -> u32 {
        self.samples.len() as u32
    }

    pub fn summary(&self) -> Option<StatSummary> {
        let n = self.samples.len();
        if n == 0 {
            return None;
        }
        let sum: f64 = self.samples.iter().map(|(_, v)| v).sum();
        let mean = sum / n as f64;
        let min = self.samples.iter().map(|(_, v)| *v).fold(f64::INFINITY, f64::min);
        let max = self.samples.iter().map(|(_, v)| *v).fold(f64::NEG_INFINITY, f64::max);

        let variance = self.samples.iter().map(|(_, v)| {
            let d = v - mean;
            d * d
        }).sum::<f64>() / n as f64;

        Some(StatSummary {
            mean,
            min,
            max,
            std: variance.sqrt(),
            count: n as u32,
        })
    }

    /// Compute z-score for a new value against current window statistics.
    pub fn z_score(&self, value: f64) -> Option<f64> {
        self.summary().map(|s| {
            if s.std < 1e-12 {
                0.0
            } else {
                (value - s.mean) / s.std
            }
        })
    }
}

// ---------------------------------------------------------------------------
// Aggregate accumulator for 5-minute windows
// ---------------------------------------------------------------------------

#[derive(Debug)]
pub struct AggregateAccumulator {
    window_start: DateTime<Utc>,
    window_seconds: i64,
    engine_samples: Vec<EngineTelemetry>,
    cargo_samples: Vec<CargoTelemetry>,
    aux_samples: Vec<AuxTelemetry>,
    nav_samples: Vec<NavigationTelemetry>,
}

impl AggregateAccumulator {
    pub fn new(window_seconds: i64) -> Self {
        Self {
            window_start: Utc::now(),
            window_seconds,
            engine_samples: Vec::new(),
            cargo_samples: Vec::new(),
            aux_samples: Vec::new(),
            nav_samples: Vec::new(),
        }
    }

    pub fn push_engine(&mut self, data: EngineTelemetry) {
        self.engine_samples.push(data);
    }

    pub fn push_cargo(&mut self, data: CargoTelemetry) {
        self.cargo_samples.push(data);
    }

    pub fn push_aux(&mut self, data: AuxTelemetry) {
        self.aux_samples.push(data);
    }

    pub fn push_nav(&mut self, data: NavigationTelemetry) {
        self.nav_samples.push(data);
    }

    pub fn is_window_expired(&self) -> bool {
        Utc::now() - self.window_start >= chrono::Duration::seconds(self.window_seconds)
    }

    pub fn window_start(&self) -> DateTime<Utc> {
        self.window_start
    }

    pub fn drain(&mut self, vessel_id: &str) -> Option<AggregatedTelemetry> {
        let now = Utc::now();
        let window_end = now;
        let n_engine = self.engine_samples.len() as u32;
        let n_cargo = self.cargo_samples.len() as u32;
        let n_aux = self.aux_samples.len() as u32;
        let n_nav = self.nav_samples.len() as u32;

        if n_engine == 0 && n_cargo == 0 && n_aux == 0 && n_nav == 0 {
            self.window_start = now;
            return None;
        }

        let agg = AggregatedTelemetry {
            id: Uuid::new_v4(),
            vessel_id: vessel_id.to_string(),
            window_start: self.window_start,
            window_end,
            n_samples: n_engine + n_cargo + n_aux + n_nav,
            engine: self.aggregate_engine(),
            cargo: self.aggregate_cargo(),
            aux: self.aggregate_aux(),
            navigation: self.aggregate_nav(),
        };

        self.engine_samples.clear();
        self.cargo_samples.clear();
        self.aux_samples.clear();
        self.nav_samples.clear();
        self.window_start = now;

        Some(agg)
    }

    fn aggregate_engine(&self) -> AggregatedEngine {
        AggregatedEngine {
            me_power_kw: stat_from_vec(&self.engine_samples, |e| e.me_power_kw),
            me_rpm: stat_from_vec(&self.engine_samples, |e| e.me_rpm),
            me_fuel_flow_kg_h: stat_from_vec(&self.engine_samples, |e| e.me_fuel_oil_flow_rate_kg_h),
            shaft_power_kw: stat_from_vec(&self.engine_samples, |e| e.shaft_power_kw),
            me_exhaust_gas_temp_c: stat_from_vec(&self.engine_samples, |e| e.me_exhaust_gas_temp_c),
        }
    }

    fn aggregate_cargo(&self) -> AggregatedCargo {
        let n_tanks = self.cargo_samples.first().map(|c| c.tank_levels_pct.len()).unwrap_or(0);
        let tank_levels = (0..n_tanks).map(|i| {
            stat_from_vec(&self.cargo_samples, |c| c.tank_levels_pct[i])
        }).collect();
        let tank_pressures = (0..n_tanks).map(|i| {
            stat_from_vec(&self.cargo_samples, |c| c.tank_vapor_pressures_bar[i])
        }).collect();

        AggregatedCargo {
            tank_levels_pct: tank_levels,
            tank_vapor_pressures_bar: tank_pressures,
            bor_kg_h: stat_from_vec(&self.cargo_samples, |c| c.bor_kg_h),
            fuel_gas_pressure_bar: stat_from_vec(&self.cargo_samples, |c| c.fuel_gas_pressure_bar),
            fuel_gas_temp_c: stat_from_vec(&self.cargo_samples, |c| c.fuel_gas_temp_c),
        }
    }

    fn aggregate_aux(&self) -> AggregatedAux {
        AggregatedAux {
            total_power_kw: stat_from_vec(&self.aux_samples, |a| a.total_power_kw),
            main_switchboard_freq_hz: stat_from_vec(&self.aux_samples, |a| a.main_switchboard_freq_hz),
            boiler_pressure_bar: stat_from_vec(&self.aux_samples, |a| a.boiler_pressure_bar),
        }
    }

    fn aggregate_nav(&self) -> AggregatedNavigation {
        let speed = stat_from_vec(&self.nav_samples, |n| n.speed_over_ground_knots);
        let lat = self.nav_samples.last().map(|n| n.latitude).unwrap_or(0.0);
        let lon = self.nav_samples.last().map(|n| n.longitude).unwrap_or(0.0);

        AggregatedNavigation {
            speed_over_ground_knots: speed,
            latitude: lat,
            longitude: lon,
        }
    }
}

fn stat_from_vec<T, F>(items: &[T], f: F) -> StatSummary
where
    F: Fn(&T) -> f64,
{
    let n = items.len();
    if n == 0 {
        return StatSummary { mean: 0.0, min: 0.0, max: 0.0, std: 0.0, count: 0 };
    }
    let sum: f64 = items.iter().map(|item| f(item)).sum();
    let mean = sum / n as f64;
    let min = items.iter().map(|item| f(item)).fold(f64::INFINITY, f64::min);
    let max = items.iter().map(|item| f(item)).fold(f64::NEG_INFINITY, f64::max);
    let variance = items.iter().map(|item| {
        let v = f(item) - mean;
        v * v
    }).sum::<f64>() / n as f64;

    StatSummary {
        mean,
        min,
        max,
        std: variance.sqrt(),
        count: n as u32,
    }
}

// ---------------------------------------------------------------------------
// BOR calculation from tank pressure rise rate (closed hold method)
// ---------------------------------------------------------------------------

/// Calculate Boil-Off Rate from tank pressure rise rate using the closed hold method.
/// Uses ideal gas law: BOR = (V_tank / (R * T)) * (dP/dt)
pub fn calculate_bor(
    pressure_rise_rate_pa_per_s: f64,
    tank_vapor_volume_m3: f64,
    vapor_temp_k: f64,
    gas_constant_j_kgk: f64,
) -> f64 {
    // BOR in kg/s
    let bor_kg_s = (tank_vapor_volume_m3 / (gas_constant_j_kgk * vapor_temp_k)) * pressure_rise_rate_pa_per_s;
    bor_kg_s * 3600.0 // convert to kg/h
}

// ---------------------------------------------------------------------------
// CII Calculation
// ---------------------------------------------------------------------------

/// Calculate CII rating (gCO2 / (dwt * nm))
pub fn calculate_cii(
    fuel_consumption_tonnes: f64,
    co2_conversion_factor: f64,
    distance_nm: f64,
    deadweight_tonnes: f64,
) -> f64 {
    if distance_nm <= 0.0 || deadweight_tonnes <= 0.0 {
        return 0.0;
    }
    let co2_emissions = fuel_consumption_tonnes * co2_conversion_factor * 1000.0; // kgCO2
    co2_emissions / (deadweight_tonnes * distance_nm)
}

/// CII grade based on AER rating boundaries (simplified IMO DCS 2026 boundaries)
pub fn cii_grade(cii: f64, vessel_type: &str) -> String {
    let thresholds = match vessel_type {
        "LNG Carrier (>100k DWT)" => (1.5, 2.5, 3.5, 5.0),
        "LNG Carrier (65-100k DWT)" => (1.8, 3.0, 4.2, 5.8),
        _ => (2.0, 3.5, 5.0, 7.0),
    };

    if cii < thresholds.0 { "A".into() }
    else if cii < thresholds.1 { "B".into() }
    else if cii < thresholds.2 { "C".into() }
    else if cii < thresholds.3 { "D".into() }
    else { "E".into() }
}

// ---------------------------------------------------------------------------
// Fuel type detection
// ---------------------------------------------------------------------------

/// Detect fuel type based on sulfur content and fuel oil flow.
/// Returns (fuel_type_string, sox_compliant).
pub fn detect_fuel_type(
    sulfur_content_pct: f64,
    fuel_oil_temp_c: f64,
    fuel_oil_pressure_bar: f64,
) -> (&'static str, bool) {
    if sulfur_content_pct <= 0.1 {
        (FUEL_METHANOL, true)
    } else if sulfur_content_pct <= 0.5 {
        (FUEL_LSMGO, true)
    } else if sulfur_content_pct <= 3.5 && fuel_oil_temp_c > 100.0 {
        (FUEL_HFO, false)
    } else if sulfur_content_pct <= 0.1 {
        (FUEL_LNG, true)
    } else {
        (FUEL_HFO, false)
    }
}

// ---------------------------------------------------------------------------
// Main analytics engine task
// ---------------------------------------------------------------------------

pub async fn analytics_engine(
    config: Arc<Config>,
    mut engine_rx: mpsc::Receiver<EngineTelemetry>,
    mut cargo_rx: mpsc::Receiver<CargoTelemetry>,
    mut aux_rx: mpsc::Receiver<AuxTelemetry>,
    mut nav_rx: mpsc::Receiver<NavigationTelemetry>,
    agg_tx: mpsc::Sender<AggregatedTelemetry>,
    anomaly_tx: mpsc::Sender<AnomalyEvent>,
    eca_tx: mpsc::Sender<ECAEvent>,
    cii_tx: mpsc::Sender<CIIEvent>,
    shutdown: crate::Shutdown,
) {
    let mut accumulator = AggregateAccumulator::new(config.analytics_window_seconds as i64);

    // Per-channel moving windows for anomaly detection
    let mut buffers: Vec<(&str, StatBuffer)> = vec![
        ("me_power_kw", StatBuffer::new(300, 600)),
        ("me_rpm", StatBuffer::new(300, 600)),
        ("me_exhaust_gas_temp_c", StatBuffer::new(300, 600)),
        ("me_fuel_oil_flow_rate_kg_h", StatBuffer::new(300, 600)),
        ("shaft_power_kw", StatBuffer::new(300, 600)),
        ("me_jacket_cooling_water_temp_c", StatBuffer::new(300, 600)),
        ("me_lub_oil_temp_c", StatBuffer::new(300, 600)),
        ("bor_kg_h", StatBuffer::new(100, 1800)),
        ("fuel_gas_pressure_bar", StatBuffer::new(100, 1800)),
        ("boiler_pressure_bar", StatBuffer::new(100, 1800)),
    ];

    let mut eca_tracker = ECATracker::new();
    let zscore_threshold = config.anomaly_zscore_threshold;
    let vessel_id = config.vessel_id.clone();

    // CII tracking
    let mut cumulative_fuel_consumption_tonnes = 0.0;
    let mut cumulative_distance_nm = 0.0;
    let mut last_nav: Option<NavigationTelemetry> = None;

    // Fuel state tracking
    let mut current_fuel: String = FUEL_HFO.to_string();

    info!("Analytics engine started");

    loop {
        tokio::select! {
            biased;

            _ = shutdown.wait() => {
                info!("Analytics engine shutting down");
                return;
            }

            Some(engine) = engine_rx.recv() => {
                accumulator.push_engine(engine.clone());

                // Anomaly detection on key channels
                check_anomaly("me_power_kw", engine.me_power_kw, &mut buffers, zscore_threshold, &vessel_id, &anomaly_tx).await;
                check_anomaly("me_rpm", engine.me_rpm, &mut buffers, zscore_threshold, &vessel_id, &anomaly_tx).await;
                check_anomaly("me_exhaust_gas_temp_c", engine.me_exhaust_gas_temp_c, &mut buffers, zscore_threshold, &vessel_id, &anomaly_tx).await;
                check_anomaly("me_fuel_oil_flow_rate_kg_h", engine.me_fuel_oil_flow_rate_kg_h, &mut buffers, zscore_threshold, &vessel_id, &anomaly_tx).await;
                check_anomaly("shaft_power_kw", engine.shaft_power_kw, &mut buffers, zscore_threshold, &vessel_id, &anomaly_tx).await;

                // Fuel type detection
                let (fuel_type, sox_comp) = detect_fuel_type(
                    engine.me_fuel_oil_flow_rate_kg_h * 0.005, // proxy for sulfur
                    engine.me_fuel_oil_temp_c,
                    engine.me_fuel_oil_pressure_bar,
                );

                if current_fuel != fuel_type {
                    info!("Fuel switch detected: {} -> {}", current_fuel, fuel_type);
                    current_fuel = fuel_type.to_string();
                }
            }

            Some(cargo) = cargo_rx.recv() => {
                accumulator.push_cargo(cargo.clone());
                check_anomaly("bor_kg_h", cargo.bor_kg_h, &mut buffers, zscore_threshold, &vessel_id, &anomaly_tx).await;
                check_anomaly("fuel_gas_pressure_bar", cargo.fuel_gas_pressure_bar, &mut buffers, zscore_threshold, &vessel_id, &anomaly_tx).await;
            }

            Some(aux) = aux_rx.recv() => {
                accumulator.push_aux(aux.clone());
                check_anomaly("boiler_pressure_bar", aux.boiler_pressure_bar, &mut buffers, zscore_threshold, &vessel_id, &anomaly_tx).await;
            }

            Some(nav) = nav_rx.recv() => {
                accumulator.push_nav(nav.clone());

                // ECA zone detection
                if let Some(event) = eca_tracker.check_transition(&vessel_id, nav.latitude, nav.longitude) {
                    info!("ECA event: {:?} {}", event.event_type, event.zone);
                    let _ = eca_tx.send(event).await;
                }

                // Accumulate distance for CII
                if let Some(prev) = &last_nav {
                    let dist = haversine_distance(
                        prev.latitude, prev.longitude,
                        nav.latitude, nav.longitude,
                    );
                    cumulative_distance_nm += dist;
                }
                last_nav = Some(nav);
            }
        }

        // Check if aggregation window has expired
        if accumulator.is_window_expired() {
            if let Some(agg) = accumulator.drain(&vessel_id) {
                // CII event at end of each window
                let last_lat = agg.navigation.latitude;
                let last_lon = agg.navigation.longitude;

                let cii_val = calculate_cii(
                    agg.engine.me_fuel_flow_kg_h.mean * (config.analytics_window_seconds as f64 / 3600.0) / 1000.0,
                    3.114, // LNG CO2 conversion factor
                    cumulative_distance_nm.max(1.0),
                    100000.0, // DWT placeholder
                );

                let grade = cii_grade(cii_val, "LNG Carrier (>100k DWT)");
                cumulative_fuel_consumption_tonnes +=
                    agg.engine.me_fuel_flow_kg_h.mean * (config.analytics_window_seconds as f64 / 3600.0) / 1000.0;

                let cii_event = CIIEvent {
                    id: Uuid::new_v4(),
                    vessel_id: vessel_id.clone(),
                    timestamp: Utc::now(),
                    voyage_distance_nm: cumulative_distance_nm,
                    fuel_consumption_tonnes: cumulative_fuel_consumption_tonnes,
                    cii_rating: cii_val,
                    cii_grade: grade,
                    cumulative_cii: cii_val,
                    required_cii: 3.5,
                };

                let _ = cii_tx.send(cii_event).await;
                let _ = agg_tx.send(agg).await;
                debug!("Aggregate window flushed");
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Helper: anomaly check
// ---------------------------------------------------------------------------

async fn check_anomaly(
    channel: &str,
    value: f64,
    buffers: &mut [(&str, StatBuffer)],
    threshold: f64,
    vessel_id: &str,
    tx: &mpsc::Sender<AnomalyEvent>,
) {
    let now = Utc::now();
    for (name, buf) in buffers.iter_mut() {
        if *name == channel {
            let z = buf.z_score(value).unwrap_or(0.0);
            buf.push(now, value);

            if z.abs() > threshold {
                let summary = buf.summary().unwrap_or(StatSummary {
                    mean: 0.0,
                    min: 0.0,
                    max: 0.0,
                    std: 0.0,
                    count: 0,
                });

                let event = AnomalyEvent {
                    id: Uuid::new_v4(),
                    vessel_id: vessel_id.to_string(),
                    timestamp: now,
                    channel: channel.to_string(),
                    value,
                    z_score: z,
                    mean: summary.mean,
                    std: summary.std,
                    severity: if z.abs() > threshold * 1.5 {
                        AnomalySeverity::Critical
                    } else {
                        AnomalySeverity::Warning
                    },
                };

                let _ = tx.send(event).await;
                warn!("Anomaly detected on {}: value={:.2}, z={:.2}", channel, value, z);
            }
            break;
        }
    }
}

// ---------------------------------------------------------------------------
// Haversine distance (nautical miles)
// ---------------------------------------------------------------------------

pub fn haversine_distance(lat1: f64, lon1: f64, lat2: f64, lon2: f64) -> f64 {
    const R: f64 = 3440.065; // Earth radius in nautical miles
    let d_lat = (lat2 - lat1).to_radians();
    let d_lon = (lon2 - lon1).to_radians();
    let a = (d_lat / 2.0).sin().powi(2)
        + lat1.to_radians().cos() * lat2.to_radians().cos() * (d_lon / 2.0).sin().powi(2);
    let c = 2.0 * a.sqrt().asin();
    R * c
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_stat_summary() {
        let mut buf = StatBuffer::new(10, 60);
        let now = Utc::now();
        for i in 0..5 {
            buf.push(now + Duration::seconds(i as i64), (i + 1) as f64);
        }
        let s = buf.summary().unwrap();
        assert!((s.mean - 3.0).abs() < 0.01);
        assert!((s.min - 1.0).abs() < 0.01);
        assert!((s.max - 5.0).abs() < 0.01);
    }

    #[test]
    fn test_cii_calculation() {
        let cii = calculate_cii(10.0, 3.114, 100.0, 100000.0);
        assert!(cii > 0.0);
    }

    #[test]
    fn test_haversine() {
        let d = haversine_distance(0.0, 0.0, 0.0, 1.0);
        assert!((d - 60.0).abs() < 1.0); // ~60nm per degree at equator
    }
}

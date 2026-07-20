use std::sync::Arc;
use std::time::Duration;

use anyhow::{Context, Result};
use chrono::Utc;
use log::{error, info, warn};
use tokio::sync::mpsc;
use tokio::time;
use tokio_modbus::client::{Context as ModbusContext, Reader};
use tokio_modbus::prelude::*;
use tokio_modbus::Slave;

use crate::config::ModbusEndpoint;
use crate::types::{AuxTelemetry, CargoTelemetry, EngineTelemetry};

// ---------------------------------------------------------------------------
// Register map: (register_address, scale_factor, description)
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct RegisterDef {
    pub address: u16,
    pub scale: f64,
    pub description: &'static str,
}

pub const ENGINE_REGISTERS: &[RegisterDef] = &[
    RegisterDef { address: 0,   scale: 0.125, description: "ME RPM" },
    RegisterDef { address: 2,   scale: 1.0,   description: "ME Power (kW)" },
    RegisterDef { address: 4,   scale: 0.1,   description: "ME Torque (kNm)" },
    RegisterDef { address: 6,   scale: 0.01,  description: "ME Scavenge Air Pressure (bar)" },
    RegisterDef { address: 8,   scale: 0.1,   description: "ME Exhaust Gas Temp (C)" },
    RegisterDef { address: 10,  scale: 0.1,   description: "ME Cylinder 1 Exhaust Temp (C)" },
    RegisterDef { address: 12,  scale: 0.1,   description: "ME Cylinder 2 Exhaust Temp (C)" },
    RegisterDef { address: 14,  scale: 0.1,   description: "ME Cylinder 3 Exhaust Temp (C)" },
    RegisterDef { address: 16,  scale: 0.1,   description: "ME Cylinder 4 Exhaust Temp (C)" },
    RegisterDef { address: 18,  scale: 0.1,   description: "ME Cylinder 5 Exhaust Temp (C)" },
    RegisterDef { address: 20,  scale: 0.1,   description: "ME Cylinder 6 Exhaust Temp (C)" },
    RegisterDef { address: 22,  scale: 0.01,  description: "ME Fuel Oil Flow (kg/h)" },
    RegisterDef { address: 24,  scale: 0.1,   description: "ME Fuel Oil Temp (C)" },
    RegisterDef { address: 26,  scale: 0.01,  description: "ME Fuel Oil Pressure (bar)" },
    RegisterDef { address: 28,  scale: 0.1,   description: "ME Jacket Cooling Water Temp (C)" },
    RegisterDef { address: 30,  scale: 0.01,  description: "ME Lub Oil Pressure (bar)" },
    RegisterDef { address: 32,  scale: 0.1,   description: "ME Lub Oil Temp (C)" },
    RegisterDef { address: 34,  scale: 0.125, description: "AE1 RPM" },
    RegisterDef { address: 36,  scale: 1.0,   description: "AE1 Power (kW)" },
    RegisterDef { address: 38,  scale: 0.125, description: "AE2 RPM" },
    RegisterDef { address: 40,  scale: 1.0,   description: "AE2 Power (kW)" },
    RegisterDef { address: 42,  scale: 1.0,   description: "Shaft Power (kW)" },
    RegisterDef { address: 44,  scale: 0.125, description: "Shaft RPM" },
    RegisterDef { address: 46,  scale: 0.1,   description: "Shaft Torque (kNm)" },
    RegisterDef { address: 48,  scale: 0.1,   description: "Thrust Bearing Temp (C)" },
    RegisterDef { address: 50,  scale: 0.1,   description: "Propeller Pitch (%)" },
    RegisterDef { address: 52,  scale: 0.1,   description: "Propeller Thrust (kN)" },
    RegisterDef { address: 54,  scale: 0.01,  description: "Propeller Slip (%)" },
];

pub const CARGO_REGISTERS: &[RegisterDef] = &[
    RegisterDef { address: 0,   scale: 0.1,   description: "Tank 1 Level (%)" },
    RegisterDef { address: 2,   scale: 0.1,   description: "Tank 2 Level (%)" },
    RegisterDef { address: 4,   scale: 0.1,   description: "Tank 3 Level (%)" },
    RegisterDef { address: 6,   scale: 0.1,   description: "Tank 4 Level (%)" },
    RegisterDef { address: 8,   scale: 0.1,   description: "Tank 1 Temp (C)" },
    RegisterDef { address: 10,  scale: 0.1,   description: "Tank 2 Temp (C)" },
    RegisterDef { address: 12,  scale: 0.1,   description: "Tank 3 Temp (C)" },
    RegisterDef { address: 14,  scale: 0.1,   description: "Tank 4 Temp (C)" },
    RegisterDef { address: 16,  scale: 0.001, description: "Tank 1 Vapor Pressure (bar)" },
    RegisterDef { address: 18,  scale: 0.001, description: "Tank 2 Vapor Pressure (bar)" },
    RegisterDef { address: 20,  scale: 0.001, description: "Tank 3 Vapor Pressure (bar)" },
    RegisterDef { address: 22,  scale: 0.001, description: "Tank 4 Vapor Pressure (bar)" },
    RegisterDef { address: 24,  scale: 0.1,   description: "Tank 1 Liquid Density (kg/m3)" },
    RegisterDef { address: 26,  scale: 0.1,   description: "Tank 2 Liquid Density (kg/m3)" },
    RegisterDef { address: 28,  scale: 0.1,   description: "Tank 3 Liquid Density (kg/m3)" },
    RegisterDef { address: 30,  scale: 0.1,   description: "Tank 4 Liquid Density (kg/m3)" },
    RegisterDef { address: 32,  scale: 0.1,   description: "BOR (kg/h)" },
    RegisterDef { address: 34,  scale: 0.001, description: "BOR Rate (%/day)" },
    RegisterDef { address: 36,  scale: 0.1,   description: "LNG Vapor Temp (C)" },
    RegisterDef { address: 38,  scale: 1.0,   description: "HP Compressor Speed (rpm)" },
    RegisterDef { address: 40,  scale: 0.01,  description: "HP Compressor Discharge Pressure (bar)" },
    RegisterDef { address: 42,  scale: 1.0,   description: "LP Compressor Speed (rpm)" },
    RegisterDef { address: 44,  scale: 0.01,  description: "LP Compressor Suction Pressure (bar)" },
    RegisterDef { address: 46,  scale: 0.1,   description: "Vaporizer Temp (C)" },
    RegisterDef { address: 48,  scale: 0.1,   description: "Gas Heater Temp (C)" },
    RegisterDef { address: 50,  scale: 0.01,  description: "Fuel Gas Pressure (bar)" },
    RegisterDef { address: 52,  scale: 0.1,   description: "Fuel Gas Temp (C)" },
    RegisterDef { address: 54,  scale: 0.01,  description: "O2 (%)" },
    RegisterDef { address: 56,  scale: 0.01,  description: "HC (%)" },
    RegisterDef { address: 58,  scale: 0.01,  description: "CO2 (%)" },
];

pub const AUX_REGISTERS: &[RegisterDef] = &[
    RegisterDef { address: 0,   scale: 0.01,  description: "MSB Frequency (Hz)" },
    RegisterDef { address: 2,   scale: 0.1,   description: "MSB Voltage (V)" },
    RegisterDef { address: 4,   scale: 1.0,   description: "Total Power (kW)" },
    RegisterDef { address: 6,   scale: 1.0,   description: "Power Demand (kW)" },
    RegisterDef { address: 8,   scale: 0.01,  description: "Boiler Pressure (bar)" },
    RegisterDef { address: 10,  scale: 0.1,   description: "Boiler Temp (C)" },
    RegisterDef { address: 12,  scale: 0.1,   description: "Boiler Fuel Flow (kg/h)" },
    RegisterDef { address: 14,  scale: 0.1,   description: "Engine Room Temp (C)" },
    RegisterDef { address: 16,  scale: 0.1,   description: "Engine Room Humidity (%)" },
    RegisterDef { address: 18,  scale: 0.1,   description: "Cargo Control Room Temp (C)" },
    RegisterDef { address: 20,  scale: 0.1,   description: "Bridge Room Temp (C)" },
    RegisterDef { address: 22,  scale: 0.01,  description: "Fire Main Line Pressure (bar)" },
];

// ---------------------------------------------------------------------------
// Raw register read helper
// ---------------------------------------------------------------------------

async fn read_registers(
    ctx: &mut ModbusContext,
    slave_id: u8,
    start: u16,
    count: u16,
) -> Result<Vec<u16>> {
    let slave = Slave(slave_id);
    let mut request_count = count;

    // Modbus maximum is ~125 holding registers per request
    const MAX_BATCH: u16 = 120;
    let mut all_values = Vec::with_capacity(count as usize);

    while request_count > 0 {
        let batch = request_count.min(MAX_BATCH);
        let batch_values = ctx
            .read_holding_registers(slave, start + all_values.len() as u16, batch)
            .await
            .with_context(|| {
                format!(
                    "Failed to read {} holding registers at address {} on slave {}",
                    batch,
                    start + all_values.len() as u16,
                    slave_id
                )
            })?;
        all_values.extend(batch_values);
        request_count -= batch;
    }

    Ok(all_values)
}

// ---------------------------------------------------------------------------
// Parsing functions
// ---------------------------------------------------------------------------

fn parse_engine(regs: &[u16], vessel_id: &str, timestamp: chrono::DateTime<Utc>) -> EngineTelemetry {
    let mut offset = |idx: usize| -> f64 {
        if idx < regs.len() {
            regs[idx] as f64 * ENGINE_REGISTERS[idx].scale
        } else {
            0.0
        }
    };

    EngineTelemetry {
        vessel_id: vessel_id.to_string(),
        timestamp,
        me_rpm: offset(0),
        me_power_kw: offset(1),
        me_torque_nm: offset(2),
        me_scavenge_air_pressure_bar: offset(3),
        me_exhaust_gas_temp_c: offset(4),
        me_cylinder_exhaust_temps_c: vec![offset(5), offset(6), offset(7), offset(8), offset(9), offset(10)],
        me_fuel_oil_flow_rate_kg_h: offset(11),
        me_fuel_oil_temp_c: offset(12),
        me_fuel_oil_pressure_bar: offset(13),
        me_jacket_cooling_water_temp_c: offset(14),
        me_lub_oil_pressure_bar: offset(15),
        me_lub_oil_temp_c: offset(16),
        ae1_rpm: offset(17),
        ae1_power_kw: offset(18),
        ae2_rpm: offset(19),
        ae2_power_kw: offset(20),
        shaft_power_kw: offset(21),
        shaft_rpm: offset(22),
        shaft_torque_nm: offset(23),
        thrust_bearing_temp_c: offset(24),
        propeller_pitch_pct: offset(25),
        propeller_thrust_kn: offset(26),
        propeller_slip_pct: offset(27),
    }
}

fn parse_cargo(regs: &[u16], vessel_id: &str, timestamp: chrono::DateTime<Utc>) -> CargoTelemetry {
    let mut offset = |idx: usize| -> f64 {
        if idx < regs.len() {
            regs[idx] as f64 * CARGO_REGISTERS[idx].scale
        } else {
            0.0
        }
    };

    CargoTelemetry {
        vessel_id: vessel_id.to_string(),
        timestamp,
        tank_levels_pct: vec![offset(0), offset(1), offset(2), offset(3)],
        tank_temps_c: vec![offset(4), offset(5), offset(6), offset(7)],
        tank_vapor_pressures_bar: vec![offset(8), offset(9), offset(10), offset(11)],
        tank_liquid_density_kg_m3: vec![offset(12), offset(13), offset(14), offset(15)],
        bor_kg_h: offset(16),
        bor_rate_pct_per_day: offset(17),
        lng_vapor_temp_c: offset(18),
        hp_compressor_speed_rpm: offset(19),
        hp_compressor_discharge_pressure_bar: offset(20),
        lp_compressor_speed_rpm: offset(21),
        lp_compressor_suction_pressure_bar: offset(22),
        vaporizer_temp_c: offset(23),
        gas_heater_temp_c: offset(24),
        fuel_gas_pressure_bar: offset(25),
        fuel_gas_temp_c: offset(26),
        o2_pct: offset(27),
        hydrocarbon_pct: offset(28),
        co2_pct: offset(29),
    }
}

fn parse_aux(regs: &[u16], vessel_id: &str, timestamp: chrono::DateTime<Utc>) -> AuxTelemetry {
    let mut offset = |idx: usize| -> f64 {
        if idx < regs.len() {
            regs[idx] as f64 * AUX_REGISTERS[idx].scale
        } else {
            0.0
        }
    };

    AuxTelemetry {
        vessel_id: vessel_id.to_string(),
        timestamp,
        main_switchboard_freq_hz: offset(0),
        main_switchboard_voltage_v: offset(1),
        total_power_kw: offset(2),
        power_demand_consumers_kw: offset(3),
        boiler_pressure_bar: offset(4),
        boiler_temp_c: offset(5),
        boiler_fuel_flow_kg_h: offset(6),
        engine_room_temp_c: offset(7),
        engine_room_humidity_pct: offset(8),
        cargo_control_room_temp_c: offset(9),
        bridge_room_temp_c: offset(10),
        fire_main_line_pressure_bar: offset(11),
        ballast_pump_status: false,
        ballast_tank_levels_pct: vec![],
        sprinkler_flow_status: false,
        co2_release_status: false,
        gas_detection_alarm: false,
    }
}

// ---------------------------------------------------------------------------
// Connection helper with reconnection backoff
// ---------------------------------------------------------------------------

async fn connect_modbus(endpoint: &ModbusEndpoint) -> Result<ModbusContext> {
    let addr = format!("{}:{}", endpoint.address, endpoint.port);
    let ctx = tokio_modbus::client::tcp::connect(addr)
        .await
        .with_context(|| format!("Failed to connect to Modbus at {}:{}", endpoint.address, endpoint.port))?;
    Ok(ctx)
}

async fn connect_with_retry(endpoint: &ModbusEndpoint) -> ModbusContext {
    loop {
        match connect_modbus(endpoint).await {
            Ok(ctx) => {
                info!("Connected to Modbus {}:{} (slave {})", endpoint.address, endpoint.port, endpoint.slave_id);
                return ctx;
            }
            Err(e) => {
                error!("Modbus connection failed: {}. Retrying in 5s...", e);
                time::sleep(Duration::from_secs(5)).await;
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Poller task
// ---------------------------------------------------------------------------

pub async fn poll_engine(
    config: Arc<crate::config::Config>,
    tx: mpsc::Sender<EngineTelemetry>,
    shutdown: crate::Shutdown,
) {
    poll_loop(&config.modbus_engine, &config.vessel_id, tx, &shutdown, parse_engine, ENGINE_REGISTERS.len() as u16).await;
}

pub async fn poll_cargo(
    config: Arc<crate::config::Config>,
    tx: mpsc::Sender<CargoTelemetry>,
    shutdown: crate::Shutdown,
) {
    poll_loop(&config.modbus_cargo, &config.vessel_id, tx, &shutdown, parse_cargo, CARGO_REGISTERS.len() as u16).await;
}

pub async fn poll_aux(
    config: Arc<crate::config::Config>,
    tx: mpsc::Sender<AuxTelemetry>,
    shutdown: crate::Shutdown,
) {
    poll_loop(&config.modbus_aux, &config.vessel_id, tx, &shutdown, parse_aux, AUX_REGISTERS.len() as u16).await;
}

type Parser<T> = fn(&[u16], &str, chrono::DateTime<Utc>) -> T;

async fn poll_loop<T: Send + 'static>(
    endpoint: &ModbusEndpoint,
    vessel_id: &str,
    tx: mpsc::Sender<T>,
    shutdown: &crate::Shutdown,
    parser: Parser<T>,
    register_count: u16,
) {
    let mut ctx = connect_with_retry(endpoint).await;
    let mut interval = time::interval(Duration::from_millis(endpoint.poll_interval_ms));

    let vessel_id = vessel_id.to_string();
    let ep = endpoint.clone();

    loop {
        tokio::select! {
            _ = interval.tick() => {}
            _ = shutdown.wait() => {
                info!("Modbus poller {}/{} shutting down", ep.address, ep.port);
                return;
            }
        }

        match read_registers(&mut ctx, ep.slave_id, 0, register_count).await {
            Ok(regs) => {
                let ts = Utc::now();
                let data = parser(&regs, &vessel_id, ts);
                if tx.send(data).await.is_err() {
                    warn!("Modbus poller {}/{}: receiver dropped", ep.address, ep.port);
                    return;
                }
            }
            Err(e) => {
                error!("Modbus read error on {} (slave {}): {}. Reconnecting...", ep.address, ep.slave_id, e);
                ctx = connect_with_retry(&ep).await;
            }
        }
    }
}

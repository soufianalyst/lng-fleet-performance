use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModbusEndpoint {
    pub address: String,
    pub port: u16,
    pub slave_id: u8,
    pub poll_interval_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    pub vessel_id: String,
    pub imo_number: String,

    pub modbus_engine: ModbusEndpoint,
    pub modbus_cargo: ModbusEndpoint,
    pub modbus_aux: ModbusEndpoint,

    pub opcua_endpoint_url: String,

    pub mqtt_broker_url: String,
    pub mqtt_client_id: String,

    pub satellite_mqtt_endpoint: String,
    pub satellite_mqtt_client_id: String,

    pub analytics_window_seconds: u64,
    pub anomaly_zscore_threshold: f64,

    pub data_retention_days: u32,
    pub zstd_compression_level: i32,

    pub satellite_rate_limit_messages_per_min: u32,
    pub heartbeat_interval_seconds: u64,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            vessel_id: "LNG-VESSEL-001".into(),
            imo_number: "IMO-9999999".into(),

            modbus_engine: ModbusEndpoint {
                address: "10.0.1.10".into(),
                port: 502,
                slave_id: 1,
                poll_interval_ms: 1000,
            },
            modbus_cargo: ModbusEndpoint {
                address: "10.0.1.11".into(),
                port: 502,
                slave_id: 2,
                poll_interval_ms: 5000,
            },
            modbus_aux: ModbusEndpoint {
                address: "10.0.1.12".into(),
                port: 502,
                slave_id: 3,
                poll_interval_ms: 60_000,
            },

            opcua_endpoint_url: "opc.tcp://10.0.2.1:4840".into(),

            mqtt_broker_url: "mqtt://localhost:1883".into(),
            mqtt_client_id: "lng-edge-gateway".into(),

            satellite_mqtt_endpoint: "mqtts://shore-broker.lng-fleet.com:8883".into(),
            satellite_mqtt_client_id: "lng-edge-gateway-sat".into(),

            analytics_window_seconds: 300,
            anomaly_zscore_threshold: 3.0,

            data_retention_days: 30,
            zstd_compression_level: 10,

            satellite_rate_limit_messages_per_min: 30,
            heartbeat_interval_seconds: 60,
        }
    }
}

impl Config {
    pub fn load() -> Result<Self> {
        let config_path = std::env::var("EDGE_CONFIG")
            .unwrap_or_else(|_| "config/default.toml".into());

        let cfg = config::Config::builder()
            .add_source(config::File::with_name(&config_path).required(false))
            .add_source(config::Environment::with_prefix("EDGE")
                .separator("__")
                .list_separator(",")
                .try_parsing(true))
            .build()
            .context("Failed to build configuration")?;

        let mut conf: Config = cfg
            .try_deserialize()
            .context("Failed to deserialize configuration")?;

        // Override from environment with explicit key support
        if let Ok(val) = std::env::var("EDGE_VESSEL_ID") {
            conf.vessel_id = val;
        }
        if let Ok(val) = std::env::var("EDGE_IMO_NUMBER") {
            conf.imo_number = val;
        }
        if let Ok(val) = std::env::var("EDGE_MQTT_BROKER_URL") {
            conf.mqtt_broker_url = val;
        }
        if let Ok(val) = std::env::var("EDGE_SATELLITE_MQTT_ENDPOINT") {
            conf.satellite_mqtt_endpoint = val;
        }

        Ok(conf)
    }

    pub fn config_dir() -> &'static Path {
        Path::new("config")
    }
}

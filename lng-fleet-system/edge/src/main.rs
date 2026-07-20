mod analytics;
mod config;
mod eca;
mod modbus;
mod opcua;
mod transmission;
mod types;

use std::sync::Arc;

use anyhow::Result;
use log::{error, info};
use tokio::sync::{mpsc, watch};
use tokio::signal;

/// Shared shutdown signal — broadcast to all tasks.
#[derive(Clone)]
pub struct Shutdown {
    sender: watch::Sender<bool>,
    receiver: watch::Receiver<bool>,
}

impl Shutdown {
    pub fn new() -> Self {
        let (sender, receiver) = watch::channel(false);
        Self { sender, receiver }
    }

    /// Trigger graceful shutdown.
    pub fn trigger(&self) {
        let _ = self.sender.send(true);
    }

    /// Wait until shutdown is signalled.
    pub async fn wait(&self) {
        let mut rx = self.receiver.clone();
        loop {
            rx.changed().await.ok();
            if *rx.borrow() {
                return;
            }
        }
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging
    env_logger::Builder::from_env(
        env_logger::Env::default().default_filter_or("info"),
    )
    .init();

    info!("LNG Edge Gateway starting...");

    // Load configuration
    let config = Arc::new(config::Config::load()?);
    info!(
        "Configuration loaded — vessel: {}, IMO: {}",
        config.vessel_id, config.imo_number
    );

    // Create shutdown signal
    let shutdown = Shutdown::new();

    // -----------------------------------------------------------------------
    // Channel fabric — message buses between tasks
    // -----------------------------------------------------------------------

    // Sensor -> Analytics
    let (engine_tx, engine_rx) = mpsc::channel::<types::EngineTelemetry>(256);
    let (cargo_tx, cargo_rx) = mpsc::channel::<types::CargoTelemetry>(256);
    let (aux_tx, aux_rx) = mpsc::channel::<types::AuxTelemetry>(256);
    let (nav_tx, nav_rx) = mpsc::channel::<types::NavigationTelemetry>(256);

    // Analytics -> Transmission
    let (agg_tx, agg_rx) = mpsc::channel::<types::AggregatedTelemetry>(64);
    let (anomaly_tx, anomaly_rx) = mpsc::channel::<types::AnomalyEvent>(128);
    let (eca_tx, eca_rx) = mpsc::channel::<types::ECAEvent>(64);
    let (cii_tx, cii_rx) = mpsc::channel::<types::CIIEvent>(64);

    // -----------------------------------------------------------------------
    // Concurrent task set
    // -----------------------------------------------------------------------

    let config_main = Arc::clone(&config);
    let shutdown_main = shutdown.clone();
    let main_handle = tokio::spawn(async move {
        info!("Main coordinator running");
        shutdown_main.wait().await;
        info!("Shutdown signalled, terminating tasks");
    });

    // 1. Modbus TCP pollers (3 concurrent)
    let cfg_eng = Arc::clone(&config);
    let sh_eng = shutdown.clone();
    let eng_handle = tokio::spawn(async move {
        modbus::poll_engine(cfg_eng, engine_tx, sh_eng).await;
    });

    let cfg_cargo = Arc::clone(&config);
    let sh_cargo = shutdown.clone();
    let cargo_handle = tokio::spawn(async move {
        modbus::poll_cargo(cfg_cargo, cargo_tx, sh_cargo).await;
    });

    let cfg_aux = Arc::clone(&config);
    let sh_aux = shutdown.clone();
    let aux_handle = tokio::spawn(async move {
        modbus::poll_aux(cfg_aux, aux_tx, sh_aux).await;
    });

    // 2. OPC UA client
    let cfg_nav = Arc::clone(&config);
    let sh_nav = shutdown.clone();
    let nav_handle = tokio::spawn(async move {
        opcua::poll_navigation(cfg_nav, nav_tx, sh_nav).await;
    });

    // 3. Analytics engine
    let cfg_analytics = Arc::clone(&config);
    let sh_analytics = shutdown.clone();
    let analytics_handle = tokio::spawn(async move {
        analytics::analytics_engine(
            cfg_analytics,
            engine_rx,
            cargo_rx,
            aux_rx,
            nav_rx,
            agg_tx,
            anomaly_tx,
            eca_tx,
            cii_tx,
            sh_analytics,
        )
        .await;
    });

    // 4. Satellite transmission manager
    let cfg_tx = Arc::clone(&config);
    let sh_tx = shutdown.clone();
    let tx_handle = tokio::spawn(async move {
        transmission::transmission_manager(
            cfg_tx, agg_rx, anomaly_rx, eca_rx, cii_rx, sh_tx,
        )
        .await;
    });

    // MQTT local edge bus client (Sparkplug B style)
    let mqtt_shutdown = shutdown.clone();
    let cfg_mqtt = Arc::clone(&config);
    let mqtt_handle = tokio::spawn(async move {
        run_local_mqtt_bus(cfg_mqtt, mqtt_shutdown).await;
    });

    // -----------------------------------------------------------------------
    // Graceful shutdown handler (SIGTERM / SIGINT)
    // -----------------------------------------------------------------------

    let sh_signal = shutdown.clone();
    let signal_handle = tokio::spawn(async move {
        match signal::ctrl_c().await {
            Ok(()) => {
                info!("SIGINT received — initiating graceful shutdown");
                sh_signal.trigger();
            }
            Err(e) => {
                error!("Failed to listen for Ctrl-C: {}", e);
            }
        }

        // Also listen for SIGTERM on Unix
        #[cfg(unix)]
        {
            let mut term_signal = signal::unix::signal(signal::unix::SignalKind::terminate())
                .expect("Failed to create SIGTERM signal handler");
            term_signal.recv().await;
            info!("SIGTERM received — initiating graceful shutdown");
            sh_signal.trigger();
        }
    });

    // -----------------------------------------------------------------------
    // Wait for all tasks to complete
    // -----------------------------------------------------------------------

    let results = tokio::join!(
        main_handle,
        eng_handle,
        cargo_handle,
        aux_handle,
        nav_handle,
        analytics_handle,
        tx_handle,
        mqtt_handle,
        signal_handle,
    );

    for (name, result) in [
        ("main", results.0),
        ("modbus_engine", results.1),
        ("modbus_cargo", results.2),
        ("modbus_aux", results.3),
        ("opcua_nav", results.4),
        ("analytics", results.5),
        ("transmission", results.6),
        ("mqtt_bus", results.7),
        ("signal_handler", results.8),
    ] {
        match result {
            Ok(_) => info!("Task {} exited cleanly", name),
            Err(e) => error!("Task {} exited with error: {}", name, e),
        }
    }

    info!("LNG Edge Gateway shutdown complete");
    Ok(())
}

/// Local MQTT edge bus — publishes raw sensor data in Sparkplug B-like format
/// for consumption by other onboard systems (e.g. HMI, alarm panel).
async fn run_local_mqtt_bus(config: Arc<config::Config>, shutdown: Shutdown) {
    use rumqttc::{AsyncClient, Event, MqttOptions, Packet, QoS};

    let client_id = format!("{}-local", config.mqtt_client_id);
    let mut mqttoptions = MqttOptions::new(&client_id, "localhost", 1883);

    // Parse MQTT broker from config
    if let Some(rest) = config.mqtt_broker_url.strip_prefix("mqtt://") {
        if let Some((host, port_str)) = rest.rsplit_once(':') {
            if let Ok(port) = port_str.parse::<u16>() {
                mqttoptions = MqttOptions::new(&client_id, host, port);
            }
        }
    }

    mqttoptions.set_keep_alive(std::time::Duration::from_secs(30));

    let (client, mut eventloop) = AsyncClient::new(mqttoptions, 100);

    // Publish NBIRTH (birth certificate / Sparkplug B style)
    let birth_topic = format!("spBv1.0/lng-fleet/NBIRTH/{}", config.vessel_id);
    let birth_payload = serde_json::json!({
        "vessel_id": config.vessel_id,
        "imo": config.imo_number,
        "timestamp": chrono::Utc::now().to_rfc3339(),
        "version": env!("CARGO_PKG_VERSION"),
        "services": ["modbus", "opcua", "analytics", "transmission"],
    });

    let _ = client
        .publish(birth_topic, QoS::AtLeastOnce, true, birth_payload.to_string())
        .await;

    info!("Local MQTT edge bus connected to {}", config.mqtt_broker_url);

    loop {
        tokio::select! {
            _ = shutdown.wait() => {
                // Send NDEATH
                let death_topic = format!("spBv1.0/lng-fleet/NDEATH/{}", config.vessel_id);
                let _ = client.publish(death_topic, QoS::AtLeastOnce, true, "").await;
                let _ = client.disconnect().await;
                info!("Local MQTT bus disconnected");
                return;
            }
            event = eventloop.poll() => {
                match event {
                    Ok(Event::Incoming(Packet::ConnAck(_))) => {
                        info!("Local MQTT broker connected");
                    }
                    Ok(Event::Disconnected) => {
                        warn!("Local MQTT disconnected, will reconnect...");
                    }
                    Err(e) => {
                        error!("Local MQTT error: {}", e);
                        // reconnect handled by rumqttc auto-reconnect
                    }
                    _ => {}
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn verify_config_defaults() {
        let cfg = config::Config::default();
        assert_eq!(cfg.vessel_id, "LNG-VESSEL-001");
        assert_eq!(cfg.zstd_compression_level, 10);
        assert_eq!(cfg.anomaly_zscore_threshold, 3.0);
    }
}

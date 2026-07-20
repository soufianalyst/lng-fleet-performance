use std::collections::BinaryHeap;
use std::cmp::Ordering;
use std::sync::Arc;
use std::time::{Duration, Instant};

use anyhow::{Context, Result};
use log::{debug, error, info, warn};
use rumqttc::{AsyncClient, Event, MqttOptions, Packet, QoS};
use tokio::sync::mpsc;
use tokio::time;
use uuid::Uuid;

use crate::config::Config;
use crate::types::*;

// ---------------------------------------------------------------------------
// Priority queue entry
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct QueuedMessage {
    pub id: Uuid,
    pub priority: u8,
    pub message: SatelliteMessage,
    pub created_at: chrono::DateTime<chrono::Utc>,
}

impl Eq for QueuedMessage {}

impl PartialEq for QueuedMessage {
    fn eq(&self, other: &Self) -> bool {
        self.priority == other.priority && self.id == other.id
    }
}

impl PartialOrd for QueuedMessage {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl Ord for QueuedMessage {
    fn cmp(&self, other: &Self) -> Ordering {
        // Reverse ordering so lower priority numbers come first
        self.priority
            .cmp(&other.priority)
            .then_with(|| other.created_at.cmp(&self.created_at))
    }
}

// ---------------------------------------------------------------------------
// Rate limiter
// ---------------------------------------------------------------------------

#[derive(Debug)]
pub struct RateLimiter {
    max_per_min: u32,
    tokens: u32,
    last_reset: Instant,
}

impl RateLimiter {
    pub fn new(max_per_min: u32) -> Self {
        Self {
            max_per_min,
            tokens: max_per_min,
            last_reset: Instant::now(),
        }
    }

    pub async fn acquire(&mut self) {
        loop {
            let elapsed = self.last_reset.elapsed();
            if elapsed >= Duration::from_secs(60) {
                self.tokens = self.max_per_min;
                self.last_reset = Instant::now();
            }

            if self.tokens > 0 {
                self.tokens -= 1;
                return;
            }

            // Wait until token bucket refills
            let wait = Duration::from_secs(60) - elapsed;
            time::sleep(wait.min(Duration::from_secs(1))).await;
        }
    }
}

// ---------------------------------------------------------------------------
// Zstd compression
// ---------------------------------------------------------------------------

pub fn compress_payload(data: &[u8], level: i32) -> Result<CompressedPayload> {
    let compressed = zstd::encode_all(data, level)
        .context("Zstd compression failed")?;

    Ok(CompressedPayload {
        vessel_id: String::new(),
        algorithm: "zstd".into(),
        level,
        original_size: data.len(),
        compressed_size: compressed.len(),
        data: compressed,
    })
}

pub fn decompress_payload(payload: &CompressedPayload) -> Result<Vec<u8>> {
    let decompressed = zstd::decode_all(&payload.data[..])
        .context("Zstd decompression failed")?;
    Ok(decompressed)
}

// ---------------------------------------------------------------------------
// Satellite transmission manager
// ---------------------------------------------------------------------------

pub async fn transmission_manager(
    config: Arc<Config>,
    mut agg_rx: mpsc::Receiver<AggregatedTelemetry>,
    mut anomaly_rx: mpsc::Receiver<AnomalyEvent>,
    mut eca_rx: mpsc::Receiver<ECAEvent>,
    mut cii_rx: mpsc::Receiver<CIIEvent>,
    shutdown: crate::Shutdown,
) {
    let mut queue: BinaryHeap<QueuedMessage> = BinaryHeap::new();
    let mut rate_limiter = RateLimiter::new(config.satellite_rate_limit_messages_per_min);

    // MQTT client for satellite uplink
    let (mqtt_client, mut mqtt_eventloop) = create_mqtt_client(&config).await;
    let mut last_heartbeat = Instant::now();
    let heartbeat_interval = Duration::from_secs(config.heartbeat_interval_seconds);

    // Track transmission stats
    let mut tx_count: u64 = 0;
    let mut last_tx_time: Option<chrono::DateTime<chrono::Utc>> = None;
    let start_time = Instant::now();

    info!("Transmission manager started");

    loop {
        tokio::select! {
            biased;

            _ = shutdown.wait() => {
                info!("Transmission manager shutting down. Flushing queue ({} items)...", queue.len());
                flush_queue(&mut queue, &mqtt_client, &config, &mut rate_limiter, &mut tx_count, &mut last_tx_time).await;
                let _ = mqtt_client.disconnect().await;
                return;
            }

            Some(agg) = agg_rx.recv() => {
                let msg = QueuedMessage {
                    id: Uuid::new_v4(),
                    priority: SatelliteMessage::Telemetry(agg.clone()).priority(),
                    message: SatelliteMessage::Telemetry(agg),
                    created_at: chrono::Utc::now(),
                };
                queue.push(msg);
                debug!("Queued telemetry aggregate (queue: {})", queue.len());
            }

            Some(anomaly) = anomaly_rx.recv() => {
                let msg = QueuedMessage {
                    id: Uuid::new_v4(),
                    priority: 0,
                    message: SatelliteMessage::Anomaly(anomaly),
                    created_at: chrono::Utc::now(),
                };
                queue.push(msg);
                info!("Queued anomaly event for immediate transmission");
                // Transmit high-priority messages immediately
                transmit_high_priority(&mut queue, &mqtt_client, &config, &mut rate_limiter, &mut tx_count, &mut last_tx_time).await;
            }

            Some(eca) = eca_rx.recv() => {
                let msg = QueuedMessage {
                    id: Uuid::new_v4(),
                    priority: 0,
                    message: SatelliteMessage::ECA(eca),
                    created_at: chrono::Utc::now(),
                };
                queue.push(msg);
                transmit_high_priority(&mut queue, &mqtt_client, &config, &mut rate_limiter, &mut tx_count, &mut last_tx_time).await;
            }

            Some(cii) = cii_rx.recv() => {
                let msg = QueuedMessage {
                    id: Uuid::new_v4(),
                    priority: 1,
                    message: SatelliteMessage::CII(cii),
                    created_at: chrono::Utc::now(),
                };
                queue.push(msg);
            }
        }

        // Periodic heartbeat
        if last_heartbeat.elapsed() >= heartbeat_interval {
            let heartbeat = Heartbeat {
                vessel_id: config.vessel_id.clone(),
                timestamp: chrono::Utc::now(),
                uptime_seconds: start_time.elapsed().as_secs(),
                services_online: vec![
                    "modbus_engine".into(),
                    "modbus_cargo".into(),
                    "modbus_aux".into(),
                    "opcua".into(),
                    "analytics".into(),
                    "transmission".into(),
                ],
                queue_depth: queue.len(),
                last_transmission: last_tx_time,
            };

            let msg = QueuedMessage {
                id: Uuid::new_v4(),
                priority: 2,
                message: SatelliteMessage::Heartbeat(heartbeat),
                created_at: chrono::Utc::now(),
            };
            queue.push(msg);
            last_heartbeat = Instant::now();
            debug!("Heartbeat queued");
        }

        // Process MQTT events
        while let Ok(event) = mqtt_eventloop.try_recv() {
            match event {
                Event::Incoming(Packet::ConnAck(_)) => {
                    info!("Satellite MQTT connected");
                }
                Event::Disconnected => {
                    warn!("Satellite MQTT disconnected, reconnecting...");
                }
                _ => {}
            }
        }

        // Periodic batch transmission of aggregates
        time::sleep(Duration::from_millis(100)).await;
    }
}

async fn create_mqtt_client(config: &Config) -> (AsyncClient, rumqttc::EventLoop) {
    let mut mqttoptions =
        MqttOptions::new(&config.satellite_mqtt_client_id, &config.satellite_mqtt_endpoint, 1883);
    mqttoptions.set_keep_alive(Duration::from_secs(30));

    // Parse the MQTT broker URL
    if let Some(rest) = config.satellite_mqtt_endpoint.strip_prefix("mqtts://") {
        if let Some((host, port_str)) = rest.rsplit_once(':') {
            if let Ok(port) = port_str.parse::<u16>() {
                mqttoptions = MqttOptions::new(&config.satellite_mqtt_client_id, host, port);
                mqttoptions.set_keep_alive(Duration::from_secs(30));
            }
        }
    } else if let Some(rest) = config.satellite_mqtt_endpoint.strip_prefix("mqtt://") {
        if let Some((host, port_str)) = rest.rsplit_once(':') {
            if let Ok(port) = port_str.parse::<u16>() {
                mqttoptions = MqttOptions::new(&config.satellite_mqtt_client_id, host, port);
                mqttoptions.set_keep_alive(Duration::from_secs(30));
            }
        }
    }

    let (client, eventloop) = AsyncClient::new(mqttoptions, 100);
    (client, eventloop)
}

async fn publish_message(
    client: &AsyncClient,
    topic: &str,
    payload: &[u8],
) -> Result<()> {
    client
        .publish(topic, QoS::AtLeastOnce, false, payload)
        .await
        .context("MQTT publish failed")?;
    Ok(())
}

async fn transmit_high_priority(
    queue: &mut BinaryHeap<QueuedMessage>,
    mqtt_client: &AsyncClient,
    config: &Config,
    rate_limiter: &mut RateLimiter,
    tx_count: &mut u64,
    last_tx_time: &mut Option<chrono::DateTime<chrono::Utc>>,
) {
    // Collect all high-priority messages (priority 0)
    let mut high_pri: Vec<QueuedMessage> = Vec::new();
    while let Some(msg) = queue.peek() {
        if msg.priority == 0 {
            high_pri.push(queue.pop().unwrap());
        } else {
            break;
        }
    }

    for msg in &high_pri {
        rate_limiter.acquire().await;
        let json = match serde_json::to_vec(&msg.message) {
            Ok(j) => j,
            Err(e) => {
                error!("Failed to serialize message: {}", e);
                continue;
            }
        };

        let compressed = match compress_payload(&json, config.zstd_compression_level) {
            Ok(c) => c,
            Err(e) => {
                error!("Compression failed: {}", e);
                continue;
            }
        };

        let topic = format!(
            "lng-fleet/{}/{}",
            config.vessel_id,
            msg.message.message_type()
        );

        if let Err(e) = publish_message(mqtt_client, &topic, &compressed.data).await {
            error!("Failed to publish {}: {}", topic, e);
            // Re-queue on failure
            queue.push(msg.clone());
        } else {
            *tx_count += 1;
            *last_tx_time = Some(chrono::Utc::now());
            debug!("Transmitted {} (tx_count={})", topic, tx_count);
        }
    }
}

async fn flush_queue(
    queue: &mut BinaryHeap<QueuedMessage>,
    mqtt_client: &AsyncClient,
    config: &Config,
    rate_limiter: &mut RateLimiter,
    tx_count: &mut u64,
    last_tx_time: &mut Option<chrono::DateTime<chrono::Utc>>,
) {
    let messages: Vec<QueuedMessage> = queue.drain().collect();
    info!("Flushing {} messages", messages.len());

    for msg in &messages {
        rate_limiter.acquire().await;
        let json = match serde_json::to_vec(&msg.message) {
            Ok(j) => j,
            Err(e) => {
                error!("Serialize error during flush: {}", e);
                continue;
            }
        };

        let compressed = match compress_payload(&json, config.zstd_compression_level) {
            Ok(c) => c,
            Err(e) => {
                error!("Compression error during flush: {}", e);
                continue;
            }
        };

        let topic = format!(
            "lng-fleet/{}/{}",
            config.vessel_id,
            msg.message.message_type()
        );

        if let Err(e) = publish_message(mqtt_client, &topic, &compressed.data).await {
            error!("Flush publish failed for {}: {}", topic, e);
        } else {
            *tx_count += 1;
            *last_tx_time = Some(chrono::Utc::now());
        }
    }
}

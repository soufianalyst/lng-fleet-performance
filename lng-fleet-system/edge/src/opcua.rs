use std::sync::Arc;
use std::time::Duration;

use anyhow::{Context, Result};
use chrono::Utc;
use log::{error, info, warn};
use tokio::sync::mpsc;
use tokio::time;

use crate::types::NavigationTelemetry;

// ---------------------------------------------------------------------------
// OPC UA node IDs for key vessel variables
// ---------------------------------------------------------------------------

pub struct OPCUANode {
    pub ns: u16,
    pub id: &'static str,
    pub description: &'static str,
}

pub const NAV_NODES: &[OPCUANode] = &[
    OPCUANode { ns: 2, id: "GPS.Latitude",      description: "Latitude (deg)" },
    OPCUANode { ns: 2, id: "GPS.Longitude",     description: "Longitude (deg)" },
    OPCUANode { ns: 2, id: "GPS.SOG",            description: "Speed Over Ground (kn)" },
    OPCUANode { ns: 2, id: "GPS.COG",            description: "Course Over Ground (deg)" },
    OPCUANode { ns: 2, id: "GPS.Heading",        description: "Heading (deg)" },
    OPCUANode { ns: 2, id: "Draft.Fore",         description: "Draft Fore (m)" },
    OPCUANode { ns: 2, id: "Draft.Aft",          description: "Draft Aft (m)" },
    OPCUANode { ns: 2, id: "EchoSounder.Depth",  description: "Depth Below Keel (m)" },
    OPCUANode { ns: 2, id: "Weather.WindSpeed",  description: "Wind Speed (kn)" },
    OPCUANode { ns: 2, id: "Weather.WindDir",    description: "Wind Direction (deg)" },
    OPCUANode { ns: 2, id: "Weather.SeaState",   description: "Sea State" },
    OPCUANode { ns: 2, id: "Weather.AirTemp",    description: "Air Temp (C)" },
    OPCUANode { ns: 2, id: "Weather.SeaTemp",    description: "Sea Water Temp (C)" },
];

/// Read a single OPC UA variable as a f64.
async fn read_opcua_variable(
    client: &mut opcua_client::client::Client,
    session: &mut opcua_client::client::Session,
    ns: u16,
    node_id: &str,
) -> Result<f64> {
    use opcua_client::prelude::*;

    let node = NodeId::new(ns, node_id);
    let value = session
        .read(client, node)
        .await
        .with_context(|| format!("Failed to read OPC UA node {}:{}", ns, node_id))?;

    let variant = value
        .ok_or_else(|| anyhow::anyhow!("No value returned for node {}:{}", ns, node_id))?;

    match variant {
        Variant::Double(v) => Ok(v),
        Variant::Float(v) => Ok(v as f64),
        Variant::Int32(v) => Ok(v as f64),
        Variant::UInt32(v) => Ok(v as f64),
        Variant::Int16(v) => Ok(v as f64),
        Variant::UInt16(v) => Ok(v as f64),
        _ => anyhow::bail!("Unsupported variant type for node {}:{}", ns, node_id),
    }
}

// ---------------------------------------------------------------------------
// Connection with retry
// ---------------------------------------------------------------------------

async fn connect_opcua(endpoint: &str) -> Result<(opcua_client::client::Client, opcua_client::client::Session)> {
    use opcua_client::prelude::*;

    let mut client = ClientBuilder::new()
        .application_name("LNG Edge Gateway")
        .application_uri("urn:lng-fleet:edge-gateway")
        .product_uri("https://lng-fleet.com")
        .session_name("lng-edge-session")
        .session_timeout(30000)
        .endpoint(endpoint)
        .client()
        .context("Failed to create OPC UA client")?;

    let session = client
        .connect()
        .await
        .with_context(|| format!("Failed to connect to OPC UA endpoint: {}", endpoint))?;

    info!("Connected to OPC UA server at {}", endpoint);
    Ok((client, session))
}

async fn connect_with_retry(endpoint: &str) -> (opcua_client::client::Client, opcua_client::client::Session) {
    loop {
        match connect_opcua(endpoint).await {
            Ok((client, session)) => return (client, session),
            Err(e) => {
                error!("OPC UA connection failed: {}. Retrying in 10s...", e);
                time::sleep(Duration::from_secs(10)).await;
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Navigation poller
// ---------------------------------------------------------------------------

pub async fn poll_navigation(
    config: Arc<crate::config::Config>,
    tx: mpsc::Sender<NavigationTelemetry>,
    shutdown: crate::Shutdown,
) {
    let endpoint = config.opcua_endpoint_url.clone();
    let vessel_id = config.vessel_id.clone();

    let (mut client, mut session) = connect_with_retry(&endpoint).await;
    let mut interval = time::interval(Duration::from_secs(5));

    loop {
        tokio::select! {
            _ = interval.tick() => {}
            _ = shutdown.wait() => {
                info!("OPC UA navigation poller shutting down");
                let _ = client.disconnect().await;
                return;
            }
        }

        let mut values = Vec::with_capacity(NAV_NODES.len());
        let mut ok = true;

        for node in NAV_NODES {
            match read_opcua_variable(&mut client, &mut session, node.ns, node.id).await {
                Ok(val) => values.push(val),
                Err(e) => {
                    error!("OPC UA read error on {}: {}", node.id, e);
                    ok = false;
                    break;
                }
            }
        }

        if !ok {
            warn!("OPC UA read failure, reconnecting...");
            let _ = client.disconnect().await;
            (client, session) = connect_with_retry(&endpoint).await;
            continue;
        }

        let nav = NavigationTelemetry {
            vessel_id: vessel_id.clone(),
            timestamp: Utc::now(),
            latitude: values[0],
            longitude: values[1],
            speed_over_ground_knots: values[2],
            course_over_ground_deg: values[3],
            heading_deg: values[4],
            draft_fore_m: values[5],
            draft_aft_m: values[6],
            depth_below_keel_m: values[7],
            wind_speed_knots: values[8],
            wind_direction_deg: values[9],
            sea_state: values[10],
            air_temp_c: values[11],
            sea_water_temp_c: values[12],
            eca_zone: None,
        };

        if tx.send(nav).await.is_err() {
            warn!("OPC UA navigation poller: receiver dropped");
            let _ = client.disconnect().await;
            return;
        }
    }
}

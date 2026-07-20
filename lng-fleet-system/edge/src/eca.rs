use std::sync::atomic::{AtomicUsize, Ordering};

use crate::types::{ECAEvent, ECAEventType};
use chrono::Utc;
use uuid::Uuid;

// ---------------------------------------------------------------------------
// ECA Zone bounding boxes (latitude/longitude)
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct ECABoundingBox {
    pub name: &'static str,
    pub description: &'static str,
    pub min_lat: f64,
    pub max_lat: f64,
    pub min_lon: f64,
    pub max_lon: f64,
}

pub const ECA_ZONES: &[ECABoundingBox] = &[
    ECABoundingBox {
        name: "Baltic Sea",
        description: "Baltic Sea ECA (SOx & NOx)",
        min_lat: 53.0,  max_lat: 66.0,
        min_lon: 8.0,   max_lon: 30.0,
    },
    ECABoundingBox {
        name: "North Sea",
        description: "North Sea ECA (SOx & NOx)",
        min_lat: 48.0,  max_lat: 63.0,
        min_lon: -12.0, max_lon: 10.0,
    },
    ECABoundingBox {
        name: "North American",
        description: "North American ECA (SOx, NOx & PM) — US/Canada Atlantic",
        min_lat: 24.0,  max_lat: 60.0,
        min_lon: -90.0, max_lon: -50.0,
    },
    ECABoundingBox {
        name: "US Caribbean",
        description: "US Caribbean ECA (SOx, NOx & PM)",
        min_lat: 8.0,   max_lat: 30.0,
        min_lon: -100.0, max_lon: -60.0,
    },
    ECABoundingBox {
        name: "Mediterranean",
        description: "Mediterranean Sea ECA (SOx) — Med SOx ECA",
        min_lat: 30.0,  max_lat: 46.0,
        min_lon: -6.0,  max_lon: 36.0,
    },
    ECABoundingBox {
        name: "English Channel",
        description: "English Channel — extended North Sea boundary",
        min_lat: 48.5,  max_lat: 52.0,
        min_lon: -6.0,  max_lon: 3.0,
    },
];

/// Returns the name of the ECA zone for the given coordinates, or None.
pub fn point_in_eca(lat: f64, lon: f64) -> Option<&'static str> {
    for zone in ECA_ZONES {
        if lat >= zone.min_lat && lat <= zone.max_lat
            && lon >= zone.min_lon && lon <= zone.max_lon
        {
            return Some(zone.name);
        }
    }
    None
}

// ---------------------------------------------------------------------------
// ECA state tracker — caches last known zone to detect transitions
// ---------------------------------------------------------------------------

/// Thread-safe ECA zone tracker that caches the last known zone.
pub struct ECATracker {
    last_zone: AtomicUsize,
    zone_count: usize,
}

impl ECATracker {
    pub fn new() -> Self {
        Self {
            last_zone: AtomicUsize::new(usize::MAX),
            zone_count: ECA_ZONES.len(),
        }
    }

    /// Check whether the vessel entered or exited an ECA zone.
    /// Returns `None` if no zone transition occurred.
    pub fn check_transition(&self, vessel_id: &str, lat: f64, lon: f64) -> Option<ECAEvent> {
        let now = Utc::now();
        let current = point_in_eca(lat, lon);
        let previous_idx = self.last_zone.load(Ordering::Acquire);
        let previous = if previous_idx < self.zone_count {
            Some(ECA_ZONES[previous_idx].name)
        } else {
            None
        };

        match (previous, current) {
            (None, Some(zone)) => {
                self.last_zone.store(
                    ECA_ZONES.iter().position(|z| z.name == zone).unwrap_or(usize::MAX),
                    Ordering::Release,
                );
                Some(ECAEvent {
                    id: Uuid::new_v4(),
                    vessel_id: vessel_id.to_string(),
                    timestamp: now,
                    event_type: ECAEventType::Enter,
                    zone: zone.to_string(),
                    latitude: lat,
                    longitude: lon,
                })
            }
            (Some(prev_zone), None) => {
                self.last_zone.store(usize::MAX, Ordering::Release);
                Some(ECAEvent {
                    id: Uuid::new_v4(),
                    vessel_id: vessel_id.to_string(),
                    timestamp: now,
                    event_type: ECAEventType::Exit,
                    zone: prev_zone.to_string(),
                    latitude: lat,
                    longitude: lon,
                })
            }
            (Some(_), Some(curr_zone)) => {
                if previous_idx < self.zone_count {
                    let prev_name = ECA_ZONES[previous_idx].name;
                    if prev_name != curr_zone {
                        // Zone change: exit old, enter new
                        self.last_zone.store(
                            ECA_ZONES.iter().position(|z| z.name == curr_zone).unwrap_or(usize::MAX),
                            Ordering::Release,
                        );
                        Some(ECAEvent {
                            id: Uuid::new_v4(),
                            vessel_id: vessel_id.to_string(),
                            timestamp: now,
                            event_type: ECAEventType::Enter,
                            zone: curr_zone.to_string(),
                            latitude: lat,
                            longitude: lon,
                        })
                    } else {
                        None
                    }
                } else {
                    None
                }
            }
            (None, None) => None,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_baltic_sea_in() {
        assert_eq!(point_in_eca(57.0, 18.0), Some("Baltic Sea"));
    }

    #[test]
    fn test_north_sea_in() {
        assert_eq!(point_in_eca(52.0, 2.0), Some("North Sea"));
    }

    #[test]
    fn test_outside_eca() {
        assert_eq!(point_in_eca(-10.0, -100.0), None);
    }
}

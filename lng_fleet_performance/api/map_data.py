import math
import os
from datetime import datetime, timezone
from fastapi import APIRouter
from .deps import get_db
from ..utils.analytics_db import get_analytics_connection

router = APIRouter()


def _get_analytics():
    return get_analytics_connection()


def _get_latest_analytics_positions():
    """Latest telemetry position per analytics vessel: {vessel_num: (lat, lon, sog)}."""
    result = {}
    adb = _get_analytics()
    if adb is None:
        return result
    try:
        cur = adb.cursor()
        cur.execute("""
            SELECT vessel_id, lat_avg, lon_avg, sog_avg
            FROM telemetry_daily
            WHERE (vessel_id, day) IN (
                SELECT vessel_id, MAX(day) FROM telemetry_daily GROUP BY vessel_id
            )
        """)
        for r in cur.fetchall():
            try:
                num = int(r["vessel_id"].split("-")[1])
            except (ValueError, IndexError, AttributeError):
                continue
            result[num] = (r["lat_avg"] or 0.0, r["lon_avg"] or 0.0, r["sog_avg"] or 0.0)
    except Exception:
        pass
    return result


def _haversine(lat1, lon1, lat2, lon2):
    R = 3440.065
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(a))


def _interpolate_route(waypoints, progress_pct):
    if not waypoints:
        return [], waypoints[-1] if waypoints else None
    n = len(waypoints)
    idx = int(progress_pct / 100 * (n - 1))
    idx = min(idx, n - 2)
    frac = (progress_pct / 100 * (n - 1)) - idx
    wp_a = waypoints[idx]
    wp_b = waypoints[min(idx + 1, n - 1)]
    current_lat = wp_a["latitude"] + frac * ((wp_b["latitude"] or 0) - (wp_a["latitude"] or 0))
    current_lon = wp_a["longitude"] + frac * ((wp_b["longitude"] or 0) - (wp_a["longitude"] or 0))
    current_speed = (wp_a["speed_actual_kn"] or 19) + frac * ((wp_b["speed_actual_kn"] or 19) - (wp_a["speed_actual_kn"] or 19))
    current_course = wp_a["course_deg"] or 0
    return waypoints[:idx + 1], {"lat": current_lat, "lon": current_lon, "speed_kn": current_speed, "course": current_course}


@router.get("/fleet-positions")
async def fleet_positions(vessel_id: int = None):
    try:
        db = get_db()
    except Exception as e:
        return {"positions": [], "count": 0, "error": str(e)}
    try:
        return _fleet_positions_impl(db, vessel_id)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"positions": [], "count": 0, "error": str(e)}


def _fleet_positions_impl(db, vessel_id=None):
    # Get all vessels if no vessel_id is specified
    if not vessel_id:
        # Get all vessels from main DB
        vessels = db.fetchall("SELECT v.vessel_id, v.vessel_name, v.imo_number, v.propulsion_type FROM vessels v ORDER BY v.vessel_name")
        
        # Get active voyages from main DB
        active_voyages = db.fetchall(
            """SELECT vg.*, v.vessel_name, v.imo_number, v.propulsion_type
               FROM voyages vg JOIN vessels v ON vg.vessel_id = v.vessel_id
               WHERE vg.status='in_progress'
               ORDER BY vg.created_at DESC""")
        
        # Build mapping of vessel_id to its active voyage
        vessel_to_voyage = {}
        for voy in active_voyages:
            vessel_to_voyage[voy["vessel_id"]] = voy
        
        # Combine all vessels and their active voyages
        analytics_positions = _get_latest_analytics_positions()
        combined_voyages = []
        for vessel in vessels:
            vessel_id_val = vessel["vessel_id"]

            # Use active voyage if available
            if vessel_id_val in vessel_to_voyage:
                combined_voyages.append(vessel_to_voyage[vessel_id_val])
            else:
                # If no active voyage, create a minimal voyage entry for the vessel
                now = datetime.now(timezone.utc)
                # Use latest real telemetry position when available (sea-lane
                # positions from the analytics DB); fall back to a port anchor
                default_lat, default_lon = 25.93, 51.56  # Ras Laffan anchorage
                ap = analytics_positions.get(vessel_id_val)
                if ap and (ap[0] or ap[1]):
                    default_lat, default_lon = ap[0], ap[1]
                
                combined_voyages.append({
                    "vessel_id": vessel_id_val,
                    "vessel_name": vessel["vessel_name"],
                    "imo_number": vessel["imo_number"],
                    "propulsion_type": vessel["propulsion_type"],
                    "voyage_id": None,
                    "voyage_number": None,
                    "load_port": None,
                    "discharge_port": None,
                    "actual_departure": None,
                    "actual_arrival": None,
                    "planned_departure": None,
                    "planned_arrival": None,
                    "status": None,
                    "created_at": now,
                    "updated_at": now,
                    "lon": default_lon,
                    "lat": default_lat,
                })
        
        voyages = combined_voyages
    else:
        # Single vessel request - try to get its data from the vessel registry
        vessel = db.fetchone(
            "SELECT v.vessel_id, v.vessel_name, v.imo_number, v.propulsion_type FROM vessels v WHERE v.vessel_id=?",
            (vessel_id,))
        
        if vessel:
            # Check if it has an active voyage
            voyage = db.fetchone(
                """SELECT vg.*, v2.vessel_name, v2.imo_number, v2.propulsion_type
                   FROM voyages vg JOIN vessels v2 ON vg.vessel_id = v2.vessel_id
                   WHERE vg.vessel_id=? AND vg.status='in_progress'
                   ORDER BY vg.created_at DESC LIMIT 1""",
                (vessel_id,))
            
            if voyage:
                voyages = [voyage]
            else:
                # No active voyage, use vessel data with latest telemetry position
                now = datetime.now(timezone.utc)
                analytics_positions = _get_latest_analytics_positions()
                default_lat, default_lon = 25.93, 51.56  # Ras Laffan anchorage
                ap = analytics_positions.get(vessel_id)
                if ap and (ap[0] or ap[1]):
                    default_lat, default_lon = ap[0], ap[1]
                
                voyages = [{
                    "vessel_id": vessel_id,
                    "vessel_name": vessel["vessel_name"],
                    "imo_number": vessel["imo_number"],
                    "propulsion_type": vessel["propulsion_type"],
                    "voyage_id": None,
                    "voyage_number": None,
                    "load_port": None,
                    "discharge_port": None,
                    "actual_departure": None,
                    "actual_arrival": None,
                    "planned_departure": None,
                    "planned_arrival": None,
                    "status": None,
                    "created_at": now,
                    "updated_at": now,
                    "lon": default_lon,
                    "lat": default_lat,
                }]
        else:
            return {"positions": [], "count": 0, "error": "Vessel not found"}

    # Process all voyages to create positions
    now = datetime.now(timezone.utc)
    positions = []
    for voy in voyages:
        vid = vid_val = voy["voyage_id"]
        
        # Only process waypoints if we have a voyage_id
        if vid is not None:
            waypoints = db.fetchall(
                "SELECT * FROM voyage_waypoints WHERE voyage_id=? ORDER BY sequence_num",
                (vid,))
            if not waypoints:
                continue
            
            dep_str = voy["actual_departure"] or voy["planned_departure"] or ""
            arr_str = voy["actual_arrival"] or voy["planned_arrival"] or ""
            try:
                dep_dt = datetime.fromisoformat(dep_str.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                dep_dt = now
            try:
                arr_dt = datetime.fromisoformat(arr_str.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                arr_dt = now

            total_seconds = max((arr_dt - dep_dt).total_seconds(), 1)
            elapsed = max((now - dep_dt).total_seconds(), 0)
            time_progress = min(elapsed / total_seconds * 100, 95) if total_seconds > 0 else 50
            time_progress = max(time_progress, 5)

            traveled_wps, current_pos = _interpolate_route(waypoints, time_progress)
            if not current_pos:
                last_wp = waypoints[-1]
                current_pos = {"lat": last_wp["latitude"], "lon": last_wp["longitude"],
                               "speed_kn": last_wp["speed_actual_kn"] or 0, "course": last_wp["course_deg"] or 0}
                traveled_wps = waypoints

            full_route = [{
                "lat": w["latitude"], "lon": w["longitude"],
                "in_eca": bool(w["in_eca"]),
                "weather_hs": round(w["weather_hs_m"] or 0, 1),
            } for w in waypoints]

            positions.append({
                "vessel_id": voy["vessel_id"],
                "vessel_name": voy["vessel_name"],
                "imo_number": voy["imo_number"],
                "propulsion_type": voy["propulsion_type"] or "",
                "voyage_id": vid,
                "voyage_number": voy["voyage_number"],
                "load_port": voy["load_port"],
                "discharge_port": voy["discharge_port"],
                "current_position": current_pos,
                "route": full_route,
                "traveled_route": [{
                    "lat": w["latitude"], "lon": w["longitude"],
                } for w in traveled_wps],
                "progress_pct": round(time_progress, 1),
                "cargo_qty": voy["cargo_quantity_mt"] or 0,
                "distance_nm": voy["total_distance_nm"] or 0,
                "fuel_lng_mt": round(voy["total_fuel_lng_mt"] or 0, 1),
            })
        else:
            # For vessels without active voyages, create a static position at their default coordinates
            positions.append({
                "vessel_id": voy["vessel_id"],
                "vessel_name": voy["vessel_name"],
                "imo_number": voy["imo_number"],
                "propulsion_type": voy["propulsion_type"] or "",
                "voyage_id": None,
                "voyage_number": None,
                "load_port": None,
                "discharge_port": None,
                "current_position": {
                    "lat": voy["lat"],
                    "lon": voy["lon"],
                    "speed_kn": 0,
                    "course": 0
                },
                "route": [],
                "traveled_route": [],
                "progress_pct": 0,
                "cargo_qty": 0,
                "distance_nm": 0,
                "fuel_lng_mt": 0,
            })

    return {"positions": positions, "count": len(positions)}

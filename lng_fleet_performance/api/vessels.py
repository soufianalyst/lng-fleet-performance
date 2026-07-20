import os
from fastapi import APIRouter
from .deps import get_db
from ..utils.analytics_db import get_analytics_connection

router = APIRouter()

_ANALYTICS_DB = None


def _get_analytics_vessels():
    global _ANALYTICS_DB
    if _ANALYTICS_DB is None:
        _ANALYTICS_DB = get_analytics_connection()
    if _ANALYTICS_DB is None:
        return []
    try:
        rows = _ANALYTICS_DB.fetchall("SELECT * FROM vessel_registry ORDER BY name")
        mapped = []
        for r in rows:
            d = dict(r)
            mapped.append({
                "vessel_id": d.get("vessel_id"),
                "vessel_name": d.get("name"),
                "imo_number": d.get("imo"),
                "flag_state": d.get("flag"),
                "propulsion_type": d.get("propulsion_type"),
                "cargo_capacity_m3": d.get("cargo_capacity_m3"),
                "engine_mcr_kw": d.get("engine_mcr_kw"),
                "service_speed_kn": d.get("service_speed_kn"),
                "design_speed_kn": d.get("design_speed_kn"),
                "vessel_type": "LNG Carrier",
            })
        return mapped
    except Exception:
        return []


@router.get("/")
async def list_vessels():
    db = get_db()
    vessels = db.fetchall("SELECT * FROM vessels ORDER BY vessel_name")
    analytics_vessels = _get_analytics_vessels()
    
    # Vessel matching by name+IMO (IMO is globally unique per vessel)
    main_vessels_set = set()
    for v in vessels:
        name = dict(v).get("vessel_name", "")
        imo = dict(v).get("imo_number", "")
        main_vessels_set.add((name, imo))
    
    # Add analytics vessels that are unique
    for av in analytics_vessels:
        name = av.get("vessel_name", "")
        imo = av.get("imo_number", "")
        vessel_type = av.get("vessel_type", "")
        
        if (name and imo and vessel_type == "LNG Carrier" and
            (name, imo) not in main_vessels_set):
            vessels.append(av)
            main_vessels_set.add((name, imo))
    
    return {"vessels": vessels, "count": len(vessels)}


@router.get("/{vessel_id}")
async def get_vessel(vessel_id: int):
    db = get_db()
    vessel = db.fetchone("SELECT * FROM vessels WHERE vessel_id=?", (vessel_id,))
    if not vessel:
        analytics = _get_analytics_vessels()
        for av in analytics:
            if str(av.get("vessel_id")) == str(vessel_id):
                return {**av, "tanks": []}
        return {"error": "Vessel not found"}
    tanks = db.fetchall("SELECT * FROM vessel_tanks WHERE vessel_id=?", (vessel_id,))
    return {**dict(vessel), "tanks": tanks}

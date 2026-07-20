from fastapi import APIRouter, Query
from .deps import get_twin

router = APIRouter()


@router.get("/fleet")
async def fleet_health():
    return get_twin().fleet_wide_health()


@router.get("/health/{vessel_id}")
async def vessel_health(vessel_id: int):
    return get_twin().engine_health_assessment(vessel_id)


@router.get("/hull-health/{vessel_id}")
async def hull_health(vessel_id: int):
    return get_twin().hull_health_assessment(vessel_id)


@router.get("/bog-health/{vessel_id}")
async def bog_health(vessel_id: int):
    return get_twin().bog_system_health(vessel_id)


@router.get("/fleet-summary/{vessel_id}")
async def fleet_summary(vessel_id: int):
    return get_twin().fleet_health_summary(vessel_id)


@router.get("/alerts/{vessel_id}")
async def predictive_alerts(vessel_id: int):
    from .deps import get_db
    db = get_db()
    alerts = db.fetchall(
        """SELECT * FROM predictive_alerts WHERE vessel_id=?
           ORDER BY alert_timestamp DESC LIMIT 20""",
        (vessel_id,))
    return {"vessel_id": vessel_id, "alerts": alerts, "count": len(alerts)}


@router.get("/scenario/{vessel_id}")
async def scenario(vessel_id: int, speed_change: float = Query(-5),
                   weather: str = Query("moderate")):
    return get_twin().scenario_simulation(vessel_id, speed_change, weather)

from fastapi import APIRouter
from .deps import get_hull

router = APIRouter()


@router.get("/overview/{vessel_id}")
async def hull_overview(vessel_id: int):
    return get_hull().hull_overview(vessel_id)


@router.get("/trend/{vessel_id}")
async def hull_trend(vessel_id: int):
    return get_hull().hull_trend(vessel_id)


@router.get("/speed-power/{vessel_id}")
async def speed_power(vessel_id: int):
    return get_hull().speed_power_analysis(vessel_id)


@router.get("/trim/{vessel_id}")
async def trim_analysis(vessel_id: int):
    return get_hull().trim_analysis(vessel_id)


@router.get("/cleaning/{vessel_id}")
async def hull_cleaning(vessel_id: int):
    return get_hull().hull_cleaning_estimate(vessel_id)


@router.get("/fleet-comparison")
async def fleet_comparison():
    return get_hull().fleet_hull_comparison()


@router.get("/performance-index")
async def performance_index():
    hull = get_hull()
    rows = hull.db.fetchall("SELECT vessel_id FROM vessels ORDER BY vessel_id")
    return [hull.hull_performance_index(r["vessel_id"]) for r in rows]

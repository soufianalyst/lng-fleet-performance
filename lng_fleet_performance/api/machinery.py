from fastapi import APIRouter, Query
from .deps import get_hull

router = APIRouter()


@router.get("/engine/{voyage_id}")
async def engine_performance(voyage_id: int):
    return get_hull().engine_performance_index(voyage_id)


@router.get("/cylinder/{voyage_id}")
async def cylinder_balance(voyage_id: int):
    return get_hull().cylinder_balance_analysis(voyage_id)


@router.get("/fouling/{vessel_id}")
async def hull_fouling(vessel_id: int):
    return get_hull().hull_fouling_assessment(vessel_id)


@router.get("/shaft-power/{vessel_id}")
async def shaft_power(vessel_id: int):
    return get_hull().shaft_power_measurement(vessel_id)


@router.get("/aux/{vessel_id}")
async def auxiliary_engine(vessel_id: int):
    return get_hull().auxiliary_engine_load_profile(vessel_id)

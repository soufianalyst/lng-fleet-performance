from fastapi import APIRouter, Query
from .deps import get_charter

router = APIRouter()


@router.get("/verify/{voyage_id}")
async def verify(voyage_id: int):
    return get_charter().verify_speed_consumption(voyage_id)


@router.get("/verify-bor/{voyage_id}")
async def verify_bor(voyage_id: int):
    return get_charter().verify_bor(voyage_id)


@router.get("/weather-correction/{voyage_id}")
async def weather_correction(voyage_id: int):
    return get_charter().weather_correct_speed(voyage_id)


@router.get("/weather-consumption/{voyage_id}")
async def weather_consumption(voyage_id: int):
    return get_charter().weather_correct_consumption(voyage_id)


@router.get("/audit/{voyage_id}")
async def audit_trail(voyage_id: int):
    return get_charter().create_audit_trail(voyage_id)


@router.get("/record/{voyage_id}")
async def record_performance(voyage_id: int):
    return get_charter().record_performance(voyage_id)

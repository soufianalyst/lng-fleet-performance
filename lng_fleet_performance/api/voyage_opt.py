from fastapi import APIRouter, Query
from .deps import get_voyage_opt

router = APIRouter()


@router.get("/optimize")
async def optimize_route(
    origin_lat: float = Query(...), origin_lon: float = Query(...),
    dest_lat: float = Query(...), dest_lon: float = Query(...),
    vessel_id: int = Query(None), speed_kn: float = Query(19.0),
    weather_avoidance: bool = Query(True),
):
    return get_voyage_opt().optimize_route(
        origin_lat, origin_lon, dest_lat, dest_lon,
        vessel_id, speed_kn, weather_avoidance)


@router.get("/speed-power/{voyage_id}")
async def speed_power(voyage_id: int):
    return get_voyage_opt().speed_power_analysis(voyage_id)


@router.get("/jit/{voyage_id}")
async def just_in_time(voyage_id: int):
    return get_voyage_opt().jit_arrival_estimate(voyage_id)


@router.get("/fuel-consumption/{voyage_id}")
async def fuel_consumption(voyage_id: int):
    return get_voyage_opt().fuel_consumption_estimate(voyage_id)


@router.get("/weather/{voyage_id}")
async def weather_conditions(voyage_id: int):
    from .deps import get_db
    db = get_db()
    waypoints = db.fetchall(
        "SELECT * FROM voyage_waypoints WHERE voyage_id=? ORDER BY sequence_num",
        (voyage_id,))
    weather_data = []
    for wp in waypoints:
        if wp["wind_speed_kn"] or wp["wave_height_m"]:
            weather_data.append({
                "sequence": wp["sequence_num"],
                "wind_speed_kn": wp["wind_speed_kn"],
                "wave_height_m": wp["wave_height_m"],
                "current_speed_kn": wp["current_speed_kn"],
                "weather_penalty_pct": wp.get("weather_penalty_pct", 0),
            })
    return {"voyage_id": voyage_id, "weather_data": weather_data}

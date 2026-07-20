from fastapi import APIRouter, Query
from .deps import get_eca

router = APIRouter()


@router.get("/check/{lat}/{lon}")
async def check_position(lat: float, lon: float, fuel: str = Query("VLSFO")):
    return get_eca().check_position_compliance(lat, lon, fuel)


@router.get("/fuel-switch/{vessel_id}")
async def fuel_switch(vessel_id: int, lat: float = Query(0), lon: float = Query(0),
                      fuel: str = Query("VLSFO"), speed: float = Query(19)):
    return get_eca().optimize_fuel_switch(vessel_id, lat, lon, fuel, speed)


@router.get("/scrubber/{voyage_id}")
async def scrubber(voyage_id: int):
    return get_eca().scrubber_monitoring(voyage_id)


@router.get("/scrubber/bypass/{voyage_id}")
async def scrubber_bypass(voyage_id: int):
    return get_eca().scrubber_bypass_tracking(voyage_id)


@router.get("/scrubber/hybrid/{voyage_id}")
async def scrubber_hybrid(voyage_id: int):
    return get_eca().hybrid_mode_switching(voyage_id)


@router.get("/scr/{voyage_id}")
async def scr(voyage_id: int):
    return get_eca().scr_performance(voyage_id)


@router.get("/egr/{voyage_id}")
async def egr(voyage_id: int):
    return get_eca().igr_monitoring(voyage_id)


@router.get("/igc/{vessel_id}")
async def igc(vessel_id: int):
    return get_eca().igc_compliance_check(vessel_id)


@router.get("/emissions/{voyage_id}")
async def emissions(voyage_id: int):
    return get_eca().calculate_emissions(voyage_id)


@router.get("/optimization/{vessel_id}")
async def multi_optimization(vessel_id: int, speed: float = Query(19),
                             eua_price: float = Query(80),
                             fueleu_limit: float = Query(91.16)):
    return get_eca().multi_constraint_optimization(vessel_id, speed, eua_price, fueleu_limit)

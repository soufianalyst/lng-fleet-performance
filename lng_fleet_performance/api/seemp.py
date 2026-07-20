from fastapi import APIRouter, Query
from .deps import get_seemp

router = APIRouter()


@router.get("/measures/{vessel_id}")
async def list_measures(vessel_id: int, year: int = Query(None)):
    return get_seemp().get_measures(vessel_id, year)


@router.post("/measures/{vessel_id}")
async def add_measure(vessel_id: int, measure_type: str = Query(...),
                      description: str = Query(...), saving_mt: float = Query(0),
                      year: int = Query(None)):
    return get_seemp().add_measure(
        vessel_id, year or 2025, measure_type, description, saving_mt)


@router.get("/improvement/{vessel_id}")
async def improvement(vessel_id: int, year: int = Query(None)):
    return get_seemp().calculate_improvement(vessel_id, year)


@router.get("/dcs-report/{vessel_id}")
async def dcs_report(vessel_id: int, year: int = Query(None)):
    return get_seemp().generate_dcs_report(vessel_id, year)

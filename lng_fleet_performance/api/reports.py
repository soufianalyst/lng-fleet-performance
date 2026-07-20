from fastapi import APIRouter, Query
from .deps import get_db
from ..utils.reporting import ReportGenerator

router = APIRouter()


@router.get("/voyage/{voyage_id}")
async def voyage_report(voyage_id: int):
    db = get_db()
    reporter = ReportGenerator(db)
    return reporter.voyage_summary(voyage_id)


@router.get("/cii/{vessel_id}")
async def cii_report(vessel_id: int):
    db = get_db()
    reporter = ReportGenerator(db)
    return reporter.vessel_cii_summary(vessel_id)


@router.get("/eca/{vessel_id}")
async def eca_report(vessel_id: int):
    db = get_db()
    reporter = ReportGenerator(db)
    return reporter.eca_compliance_report(vessel_id)


@router.get("/fleet")
async def fleet_report():
    db = get_db()
    reporter = ReportGenerator(db)
    return reporter.fleet_overview()


@router.get("/emissions/{vessel_id}")
async def emissions_report(vessel_id: int, year: int = Query(None)):
    db = get_db()
    reporter = ReportGenerator(db)
    return reporter.emissions_summary(vessel_id, year)


@router.get("/charter/{voyage_id}")
async def charter_report(voyage_id: int):
    db = get_db()
    reporter = ReportGenerator(db)
    return reporter.charter_party_performance(voyage_id)

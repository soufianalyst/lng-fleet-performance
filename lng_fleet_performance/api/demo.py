from fastapi import APIRouter
from .deps import get_db
from ..demo.generate_data import DemoDataGenerator

router = APIRouter()


@router.post("/generate")
async def generate_demo_data():
    db = get_db()
    gen = DemoDataGenerator(db)
    gen.generate_all()
    return {"status": "Demo data generated successfully",
            "message": "5 vessels, 20 voyages, full telemetry seeded"}


@router.post("/reset")
async def reset_database():
    db = get_db()
    db.execute("DELETE FROM voyage_waypoints")
    db.execute("DELETE FROM voyages")
    db.execute("DELETE FROM engine_performance")
    db.execute("DELETE FROM auxiliary_engines")
    db.execute("DELETE FROM cii_assessment")
    db.execute("DELETE FROM eu_ets_records")
    db.execute("DELETE FROM fueleu_records")
    db.execute("DELETE FROM scrubber_data")
    db.execute("DELETE FROM scr_data")
    db.execute("DELETE FROM predictive_alerts")
    db.execute("DELETE FROM certificates")
    db.execute("DELETE FROM eexi_assessment")
    db.execute("DELETE FROM epl_config")
    db.execute("DELETE FROM seemp_measures")
    db.execute("DELETE FROM seemp_reports")
    db.execute("DELETE FROM egr_data")
    db.execute("DELETE FROM igc_compliance_log")
    db.execute("DELETE FROM certificate_expiry_log")
    db.execute("DELETE FROM eu_ets_surrender")
    db.execute("DELETE FROM cargo_records")
    db.execute("DELETE FROM bor_daily_summary")
    db.execute("DELETE FROM vessel_tanks")
    db.execute("DELETE FROM digital_twin_parameters")
    db.execute("DELETE FROM digital_twin_assessments")
    db.execute("DELETE FROM charter_party_audit")
    db.execute("DELETE FROM voyage_weather_data")
    db.execute("DELETE FROM voyage_fuel_switch_log")
    db.execute("DELETE FROM voyage_eca_events")
    return {"status": "Database reset successfully"}

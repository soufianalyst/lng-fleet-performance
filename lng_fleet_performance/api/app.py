from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .deps import get_db, init_modules
from ..database.schema import create_all_tables
from . import vessels, voyages, voyage_opt, cargo, machinery, hull, compliance, eca, certificates, seemp, digital_twin, charter, reports, demo, map_data, fleet_analytics, charterer
import os

app = FastAPI(
    title="LNG Fleet Performance Management System",
    description="API for LNG carrier fleet monitoring, compliance, and optimization",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(vessels.router, prefix="/api/vessels", tags=["Vessels"])
app.include_router(voyages.router, prefix="/api/voyages", tags=["Voyages"])
app.include_router(voyage_opt.router, prefix="/api/voyage-opt", tags=["Voyage Optimization"])
app.include_router(cargo.router, prefix="/api/cargo", tags=["Cargo & BOR"])
app.include_router(machinery.router, prefix="/api/machinery", tags=["Hull & Machinery"])
app.include_router(hull.router, prefix="/api/hull", tags=["Hull Performance"])
app.include_router(compliance.router, prefix="/api/compliance", tags=["CII & Regulatory"])
app.include_router(eca.router, prefix="/api/eca", tags=["ECA & Emissions"])
app.include_router(certificates.router, prefix="/api/certificates", tags=["Certificates"])
app.include_router(seemp.router, prefix="/api/seemp", tags=["SEEMP Part III"])
app.include_router(digital_twin.router, prefix="/api/digital-twin", tags=["Digital Twin"])
app.include_router(charter.router, prefix="/api/charter", tags=["Charter Party"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(demo.router, prefix="/api/demo", tags=["Demo Data"])
app.include_router(map_data.router, prefix="/api/map", tags=["Fleet Map"])
app.include_router(fleet_analytics.router, prefix="/api/analytics", tags=["Fleet Analytics"])
app.include_router(charterer.router, prefix="/api/charterer", tags=["Charterer Analytics"])


@app.on_event("startup")
async def startup():
    db = get_db()
    create_all_tables(db)
    init_modules()

    # Serve frontend static files in production
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "build")
    if os.path.exists(os.path.join(frontend_dir, "index.html")):
        @app.get("/{full_path:path}")
        async def serve_frontend(full_path: str):
            file_path = os.path.join(frontend_dir, full_path)
            if os.path.isfile(file_path):
                return FileResponse(file_path)
            return FileResponse(os.path.join(frontend_dir, "index.html"))


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "2.0.0", "modules": [
        "voyage_optimization", "cargo_monitoring", "hull_machinery",
        "cii_compliance", "digital_twin", "charter_party", "eca_optimization",
        "eexi_compliance", "seemp_compliance", "certificate_manager",
    ]}


@app.get("/api/dashboard")
async def dashboard():
    db = get_db()
    vessels = db.fetchall("SELECT * FROM vessels")
    recent_voyages = db.fetchall(
        """SELECT vg.*, v.vessel_name FROM voyages vg
           JOIN vessels v ON vg.vessel_id = v.vessel_id
           ORDER BY vg.created_at DESC LIMIT 10""")
    cii_latest = db.fetchall(
        """SELECT c.*, v.vessel_name FROM cii_assessment c
           JOIN vessels v ON c.vessel_id = v.vessel_id
           WHERE c.assessment_year = strftime('%Y', 'now')
           ORDER BY c.cii_calculated""")
    cert_alerts = db.fetchall(
        """SELECT * FROM certificates WHERE status='active'
           AND date(expiry_date) <= date('now', '+90 days')""")
    eca_active = db.fetchall("SELECT * FROM eca_zones WHERE status='active'")
    pending_alerts = db.fetchall(
        """SELECT * FROM predictive_alerts WHERE acknowledged=0 AND resolved=0
           ORDER BY created_at DESC LIMIT 20""")
    return {
        "fleet_size": len(vessels),
        "active_vessels": sum(1 for v in vessels if v["vessel_type"] == "LNG Carrier"),
        "recent_voyages": len(recent_voyages),
        "cii_summary": {
            "total_assessed": len(cii_latest),
            "compliant": sum(1 for c in cii_latest if c["cii_rating"] in ("A", "B", "C")),
            "at_risk": sum(1 for c in cii_latest if c["cii_rating"] in ("D", "E")),
        },
        "certificate_alerts": len(cert_alerts),
        "eca_zones_active": len(eca_active),
        "pending_alerts": len(pending_alerts),
        "vessels": [{"id": v["vessel_id"], "name": v["vessel_name"], "imo": v["imo_number"]}
                    for v in vessels],
    }

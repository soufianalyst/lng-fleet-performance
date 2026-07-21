from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .deps import get_db, init_modules
from .auth import router as auth_router, get_current_user, require_admin, seed_admin_user
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

_auth = [Depends(get_current_user)]
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(vessels.router, prefix="/api/vessels", tags=["Vessels"], dependencies=_auth)
app.include_router(voyages.router, prefix="/api/voyages", tags=["Voyages"], dependencies=_auth)
app.include_router(voyage_opt.router, prefix="/api/voyage-opt", tags=["Voyage Optimization"], dependencies=_auth)
app.include_router(cargo.router, prefix="/api/cargo", tags=["Cargo & BOR"], dependencies=_auth)
app.include_router(machinery.router, prefix="/api/machinery", tags=["Hull & Machinery"], dependencies=_auth)
app.include_router(hull.router, prefix="/api/hull", tags=["Hull Performance"], dependencies=_auth)
app.include_router(compliance.router, prefix="/api/compliance", tags=["CII & Regulatory"], dependencies=_auth)
app.include_router(eca.router, prefix="/api/eca", tags=["ECA & Emissions"], dependencies=_auth)
app.include_router(certificates.router, prefix="/api/certificates", tags=["Certificates"], dependencies=_auth)
app.include_router(seemp.router, prefix="/api/seemp", tags=["SEEMP Part III"], dependencies=_auth)
app.include_router(digital_twin.router, prefix="/api/digital-twin", tags=["Digital Twin"], dependencies=_auth)
app.include_router(charter.router, prefix="/api/charter", tags=["Charter Party"], dependencies=_auth)
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"], dependencies=_auth)
app.include_router(demo.router, prefix="/api/demo", tags=["Demo Data"], dependencies=_auth)
app.include_router(map_data.router, prefix="/api/map", tags=["Fleet Map"], dependencies=_auth)
app.include_router(fleet_analytics.router, prefix="/api/analytics", tags=["Fleet Analytics"], dependencies=_auth)
app.include_router(charterer.router, prefix="/api/charterer", tags=["Charterer Analytics"], dependencies=_auth)


@app.on_event("startup")
async def startup():
    import logging
    log = logging.getLogger("uvicorn.error")
    try:
        db = get_db()
        create_all_tables(db)
        log.info("Tables created/verified")

        from ..demo.seed_render import seed_if_empty
        seed_if_empty(db)
        log.info("Seed completed")

        seed_admin_user(db)
        log.info("Admin user ensured")

        init_modules()
        log.info("Database and modules initialized successfully")
    except Exception as e:
        import traceback
        log.error(f"Startup error: {e}")
        log.error(traceback.format_exc())

    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "build")
    index_path = os.path.join(frontend_dir, "index.html")
    log.info(f"Frontend path: {index_path} (exists={os.path.exists(index_path)})")
    if os.path.exists(index_path):
        @app.get("/{full_path:path}")
        async def serve_frontend(full_path: str):
            file_path = os.path.join(frontend_dir, full_path)
            if os.path.isfile(file_path):
                return FileResponse(file_path)
            return FileResponse(index_path)
    else:
        log.warning("Frontend build not found — API-only mode")
        @app.get("/{full_path:path}")
        async def serve_api_root(full_path: str):
            return {"message": "LNG Fleet Performance API", "docs": "/docs", "health": "/api/health"}


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "2.0.0", "modules": [
        "voyage_optimization", "cargo_monitoring", "hull_machinery",
        "cii_compliance", "digital_twin", "charter_party", "eca_optimization",
        "eexi_compliance", "seemp_compliance", "certificate_manager",
    ]}


@app.get("/api/dashboard")
async def dashboard(user=Depends(get_current_user)):
    db = get_db()
    vessels = db.fetchall("SELECT * FROM vessels")
    recent_voyages = db.fetchall(
        """SELECT vg.*, v.vessel_name FROM voyages vg
           JOIN vessels v ON vg.vessel_id = v.vessel_id
           ORDER BY vg.created_at DESC LIMIT 10""")
    cii_latest = db.fetchall(
        """SELECT c.*, v.vessel_name FROM cii_assessment c
           JOIN vessels v ON c.vessel_id = v.vessel_id
           WHERE c.assessment_year = 2025
           ORDER BY c.cii_calculated""")
    cert_alerts = db.fetchall(
        """SELECT * FROM certificates WHERE status='valid'
           AND (expiry_date::date) <= (CURRENT_DATE + INTERVAL '90 days')""")
    eca_active = db.fetchall("SELECT * FROM eca_zones WHERE status='active'")
    pending_alerts = db.fetchall(
        """SELECT * FROM predictive_alerts WHERE acknowledged=0 AND resolved=0
           ORDER BY alert_timestamp DESC LIMIT 20""")
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

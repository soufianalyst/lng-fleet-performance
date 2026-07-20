from fastapi import APIRouter, Query
from .deps import get_cargo, get_db
from ..utils.analytics_db import get_analytics_connection

router = APIRouter()


def _get_analytics():
    return get_analytics_connection()


@router.get("/fleet")
async def cargo_fleet():
    """Fleet-wide cargo summary: latest cargo on board, BOG rate, fill % per vessel."""
    analytics = _get_analytics()
    if analytics is None:
        return {"error": "Analytics DB not available"}
    cur = analytics.cursor()
    cur.execute("""
        SELECT t.vessel_id, t.day, t.cargo_qty_avg, t.bog_rate_avg, t.sog_avg,
               r.name, r.cargo_capacity_m3, r.propulsion_type
        FROM telemetry_daily t
        JOIN vessel_registry r ON r.vessel_id = t.vessel_id
        WHERE (t.vessel_id, t.day) IN (
            SELECT vessel_id, MAX(day) FROM telemetry_daily GROUP BY vessel_id
        )
        ORDER BY t.vessel_id
    """)
    rows = cur.fetchall()
    vessels = []
    for r in rows:
        fill_pct = r["cargo_qty_avg"] or 0
        capacity_mt = (r["cargo_capacity_m3"] or 174000) * 0.45
        cargo_mt = fill_pct / 100.0 * capacity_mt
        bor_pct_day = 0
        if cargo_mt > 100 and r["bog_rate_avg"]:
            bor_pct_day = r["bog_rate_avg"] * 24 / (cargo_mt * 1000) * 100
        vessels.append({
            "vessel_id": r["vessel_id"],
            "vessel_name": r["name"],
            "propulsion_type": r["propulsion_type"],
            "day": r["day"],
            "cargo_mt": round(cargo_mt, 0),
            "fill_pct": round(fill_pct, 1),
            "status": "laden" if fill_pct > 50 else "ballast",
            "bog_kg_h": round(r["bog_rate_avg"] or 0, 0),
            "bor_pct_day": round(bor_pct_day, 4),
            "sog_kn": round(r["sog_avg"] or 0, 1),
        })
    laden = [v for v in vessels if v["status"] == "laden"]
    return {
        "fleet_size": len(vessels),
        "laden_count": len(laden),
        "ballast_count": len(vessels) - len(laden),
        "total_cargo_mt": round(sum(v["cargo_mt"] for v in vessels), 0),
        "avg_bor_pct_day": round(
            sum(v["bor_pct_day"] for v in laden) / len(laden), 4) if laden else 0,
        "vessels": vessels,
    }


@router.get("/bor/{voyage_id}")
async def bor(voyage_id: int):
    db = get_db()
    voyage = db.fetchone("SELECT * FROM voyages WHERE voyage_id=?", (voyage_id,))
    if not voyage:
        return {"error": "Voyage not found"}
    cargo_mass = voyage["cargo_quantity_mt"] or 75000
    bog_flow = cargo_mass * 0.0015 / 24 * 1000
    return get_cargo().calculate_bor_bog_flow(bog_flow, cargo_mass)


@router.get("/bor-energy/{voyage_id}")
async def bor_energy(voyage_id: int, q_in: float = Query(150),
                     q_out: float = Query(80), compression: float = Query(20)):
    db = get_db()
    voyage = db.fetchone("SELECT * FROM voyages WHERE voyage_id=?", (voyage_id,))
    if not voyage:
        return {"error": "Voyage not found"}
    cargo_mass = voyage["cargo_quantity_mt"] or 75000
    return get_cargo().calculate_bor_energy_balance(1, q_in, q_out, compression, cargo_mass)


@router.get("/stratification/{voyage_id}")
async def stratification(voyage_id: int):
    return get_cargo().stratification_analysis(111.0, 111.2, 111.8)


@router.get("/rollover/{voyage_id}")
async def rollover(voyage_id: int):
    return get_cargo().rollover_detection(111.0, 111.2, 111.8)


@router.get("/reliquefaction/{voyage_id}")
async def reliquefaction(voyage_id: int):
    return get_cargo().reliquefaction_performance()


@router.get("/forecast/{voyage_id}")
async def cargo_forecast(voyage_id: int):
    return get_cargo().cargo_condition_forecast()


@router.get("/daily-summary/{voyage_id}")
async def daily_summary(voyage_id: int):
    return get_cargo().daily_bor_summary()

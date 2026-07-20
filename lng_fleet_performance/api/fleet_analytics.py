import os
from fastapi import APIRouter, Query
from typing import Optional
from ..utils.analytics_db import get_analytics_connection

router = APIRouter()


def _db():
    return get_analytics_connection()


@router.get("/fleet-kpi")
async def fleet_kpi():
    db = _db()
    if db is None:
        return {"error": "Analytics database not found. Run the aggregation pipeline first."}

    row = db.fetchone("""
        SELECT
            COUNT(DISTINCT vessel_id) AS total_vessels,
            MIN(day) AS first_day,
            MAX(day) AS last_day,
            COUNT(*) AS total_records,
            SUM(fuel_consumption_total_kg) AS total_fuel_kg,
            SUM(co2_total_mt) AS total_co2_mt,
            SUM(distance_total_nm) AS total_distance_nm,
            AVG(sfoc_avg) AS avg_sfoc,
            AVG(eeoi_avg) AS avg_eeoi,
            AVG(bog_rate_avg) AS avg_bog_rate
        FROM telemetry_daily
    """)
    if not row:
        return {"error": "No data in analytics database"}

    return {
        "total_vessels": row["total_vessels"],
        "fleet_size": row["total_vessels"],
        "date_range": {"first_day": row["first_day"], "last_day": row["last_day"]},
        "total_records": row["total_records"],
        "total_fuel_mt": round((row["total_fuel_kg"] or 0) / 1000, 2),
        "total_co2_mt": round(row["total_co2_mt"] or 0, 2),
        "total_distance_nm": round(row["total_distance_nm"] or 0, 1),
        "avg_sfoc": round(row["avg_sfoc"] or 0, 2),
        "avg_eeoi": round(row["avg_eeoi"] or 0, 4),
        "avg_bog_rate": round(row["avg_bog_rate"] or 0, 4),
    }


@router.get("/fleet-ranking")
async def fleet_ranking(
    metric: str = Query("sfoc"),
    limit: int = Query(50),
):
    db = _db()
    if db is None:
        return {"error": "Analytics database not found. Run the aggregation pipeline first."}

    metric_queries = {
        "sfoc": ("AVG(td.sfoc_avg) AS value", "ASC"),
        "eeoi": ("AVG(td.eeoi_avg) AS value", "ASC"),
        "co2": ("SUM(td.co2_total_mt) AS value", "ASC"),
        "distance": ("SUM(td.distance_total_nm) AS value", "DESC"),
        "fuel_efficiency": (
            "CASE WHEN SUM(td.distance_total_nm) > 0 "
            "THEN SUM(td.fuel_consumption_total_kg) / SUM(td.distance_total_nm) "
            "ELSE 999999 END AS value",
            "ASC",
        ),
        "bog_rate": ("AVG(td.bog_rate_avg) AS value", "ASC"),
    }

    if metric not in metric_queries:
        return {"error": f"Unknown metric '{metric}'. Options: {list(metric_queries.keys())}"}

    select_expr, order_dir = metric_queries[metric]

    rows = db.fetchall(f"""
        SELECT
            vr.vessel_id,
            vr.name,
            vr.imo,
            vr.propulsion_type,
            {select_expr}
        FROM vessel_registry vr
        JOIN telemetry_daily td ON vr.vessel_id = td.vessel_id
        GROUP BY vr.vessel_id
        ORDER BY value {order_dir}
        LIMIT ?
    """, (limit,))

    vessels = []
    for i, r in enumerate(rows, 1):
        val = round(r["value"], 4) if r["value"] is not None else None
        entry = {
            "vessel_id": r["vessel_id"],
            "vessel_name": r["name"],
            "imo_number": r["imo"],
            "propulsion_type": r["propulsion_type"],
            metric: val,
            "value": val,
            "rank": i,
        }
        vessels.append(entry)

    return {"metric": metric, "vessels": vessels}


@router.get("/vessel/{vessel_id}/timeseries")
async def vessel_timeseries(
    vessel_id: str,
    resolution: str = Query("daily"),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
):
    db = _db()
    if db is None:
        return {"error": "Analytics database not found. Run the aggregation pipeline first."}

    table = "telemetry_hourly" if resolution == "hourly" else "telemetry_daily"
    time_col = "hour" if resolution == "hourly" else "day"

    query = f"SELECT * FROM {table} WHERE vessel_id = ?"
    params: list = [vessel_id]

    if start:
        query += f" AND {time_col} >= ?"
        params.append(start)
    if end:
        query += f" AND {time_col} <= ?"
        params.append(end)

    query += f" ORDER BY {time_col} ASC"

    rows = db.fetchall(query, tuple(params))

    series = [dict(r) for r in rows]
    return {"vessel_id": vessel_id, "resolution": resolution, "count": len(series), "series": series}


@router.get("/fleet/timeseries")
async def fleet_timeseries(
    resolution: str = Query("daily"),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
):
    db = _db()
    if db is None:
        return {"error": "Analytics database not found. Run the aggregation pipeline first."}

    query = "SELECT * FROM fleet_daily_summary"
    params: list = []
    conditions = []

    if start:
        conditions.append("day >= ?")
        params.append(start)
    if end:
        conditions.append("day <= ?")
        params.append(end)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY day ASC"

    rows = db.fetchall(query, tuple(params))
    data = []
    for r in rows:
        rec = dict(r)
        rec["date"] = rec.get("day")
        if "total_fuel_kg" in rec:
            rec["total_fuel_mt"] = round((rec["total_fuel_kg"] or 0) / 1000, 4)
        data.append(rec)
    return {"resolution": resolution, "count": len(data), "data": data}


@router.get("/fleet/vessel-comparison")
async def vessel_comparison(
    metric: str = Query("co2"),
):
    db = _db()
    if db is None:
        return {"error": "Analytics database not found. Run the aggregation pipeline first."}

    metric_columns = {
        "co2": "co2_total_mt",
        "fuel": "fuel_consumption_total_kg",
        "sfoc": "sfoc_avg",
        "eeoi": "eeoi_avg",
        "bog_rate": "bog_rate_avg",
        "distance": "distance_total_nm",
        "sog_avg": "sog_avg",
        "engine_load": "engine_load_avg",
        "nox": "nox_total_kg",
        "sox": "sox_total_kg",
        "wave_height": "wave_height_avg",
        "wind_speed": "wind_speed_avg",
        "alarms": "alarm_count",
    }

    col = metric_columns.get(metric)
    if not col:
        return {"error": f"Unknown metric '{metric}'. Options: {list(metric_columns.keys())}"}

    vessels = db.fetchall("SELECT vessel_id, name FROM vessel_registry ORDER BY name")

    result_vessels = []
    for v in vessels:
        rows = db.fetchall(
            f"SELECT day, {col} AS value FROM telemetry_daily WHERE vessel_id = ? ORDER BY day",
            (v["vessel_id"],),
        )
        result_vessels.append({
            "vessel_id": v["vessel_id"],
            "name": v["name"],
            "days": [{"day": r["day"], "value": round(r["value"], 4) if r["value"] is not None else None} for r in rows],
        })

    return {"metric": metric, "column": col, "vessels": result_vessels}


@router.get("/route-stats")
async def route_stats():
    db = _db()
    if db is None:
        return {"error": "Analytics database not found. Run the aggregation pipeline first."}

    rows = db.fetchall("""
        SELECT
            vr.vessel_id,
            vr.name,
            vr.imo,
            vr.propulsion_type,
            COUNT(td.day) AS total_days,
            SUM(td.distance_total_nm) AS total_distance,
            AVG(td.sog_avg) AS avg_speed,
            SUM(td.fuel_consumption_total_kg) AS total_fuel,
            SUM(td.co2_total_mt) AS total_co2,
            AVG(td.engine_load_avg) AS avg_engine_load
        FROM vessel_registry vr
        LEFT JOIN telemetry_daily td ON vr.vessel_id = td.vessel_id
        GROUP BY vr.vessel_id
        ORDER BY vr.name
    """)

    stats = []
    for r in rows:
        stats.append({
            "vessel_id": r["vessel_id"],
            "name": r["name"],
            "imo": r["imo"],
            "propulsion_type": r["propulsion_type"],
            "total_days": r["total_days"],
            "total_distance": round(r["total_distance"] or 0, 1),
            "avg_speed": round(r["avg_speed"] or 0, 2),
            "total_fuel": round(r["total_fuel"] or 0, 2),
            "total_co2": round(r["total_co2"] or 0, 2),
            "avg_engine_load": round(r["avg_engine_load"] or 0, 2),
        })

    return {"count": len(stats), "stats": stats}

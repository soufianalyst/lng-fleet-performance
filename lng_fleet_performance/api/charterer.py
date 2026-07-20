import os
import math
import statistics
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import APIRouter, Query
from typing import Optional
from ..utils.analytics_db import get_analytics_connection

router = APIRouter()

_ANALYTICS_DB = None
_FLEET_DB = None

BUNKER_PRICES = {
    "LNG": {"Q1": 550, "Q2": 580, "Q3": 620, "Q4": 600},
    "MGO": {"Q1": 750, "Q2": 780, "Q3": 820, "Q4": 800},
}
FREIGHT_RATE_USD_PER_TONNE_NM = 0.0018
EU_ETS_PRICE_EUR = 85
EUR_USD = 1.08
CANAL_TOLL_SUEZ_USD = 750000
CANAL_TOLL_PANAMA_USD = 400000
DAILY_OPEX_USD = 25000
LAYTIME_ALLOWED_HOURS = 36
PORT_COST_AVG_USD = 150000
DEMO_RATE_USD_PER_MT = 3.5

SFOC_REFERENCE_G_KWH = 170

CII_BOUNDARIES = {
    "A": 0.80,
    "B": 0.89,
    "C": 1.00,
    "D": 1.10,
}


def _get_analytics_db():
    global _ANALYTICS_DB
    if _ANALYTICS_DB is None:
        _ANALYTICS_DB = get_analytics_connection()
    return _ANALYTICS_DB


def _get_fleet_db():
    global _FLEET_DB
    if _FLEET_DB is None:
        from ..database.connection import DatabaseManager
        project_root = os.path.dirname(os.path.dirname(__file__))
        fleet_db_path = os.path.join(project_root, "lng_fleet.db")
        if not os.path.exists(fleet_db_path):
            return None
        _FLEET_DB = DatabaseManager(fleet_db_path)
    return _FLEET_DB


def _analytics_db():
    db = _get_analytics_db()
    if db is None:
        return None
    return db


def _fleet_db():
    db = _get_fleet_db()
    if db is None:
        return None
    return db


def _quarter_from_date(day_str: str) -> str:
    try:
        dt = datetime.strptime(day_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        return "Q1"
    month = dt.month
    if month <= 3:
        return "Q1"
    elif month <= 6:
        return "Q2"
    elif month <= 9:
        return "Q3"
    return "Q4"


def _round(val, decimals=2):
    if val is None:
        return 0
    return round(val, decimals)


def _vessel_registry_map(db):
    rows = db.fetchall("SELECT * FROM vessel_registry")
    return {r["vessel_id"]: dict(r) for r in rows}


@router.get("/voyage-pnl")
async def voyage_pnl():
    db = _analytics_db()
    if db is None:
        return {"error": "Analytics database not found. Run the aggregation pipeline first."}

    vessels = _vessel_registry_map(db)
    all_rows = db.fetchall("""
        SELECT td.*, vr.name, vr.cargo_capacity_m3, vr.service_speed_kn
        FROM telemetry_daily td
        JOIN vessel_registry vr ON td.vessel_id = vr.vessel_id
        ORDER BY td.vessel_id, td.day
    """)

    vessel_days = defaultdict(list)
    for r in all_rows:
        vessel_days[r["vessel_id"]].append(dict(r))

    results = []
    for vid, days in vessel_days.items():
        reg = vessels.get(vid, {})
        cargo_cap = reg.get("cargo_capacity_m3", 174000)

        total_days = 0
        total_revenue = 0.0
        total_fuel_cost = 0.0
        total_port_costs = 0.0
        total_opex = 0.0
        total_distance = 0.0

        voyage_leg_days = 0
        voyage_leg_revenue = 0.0
        voyage_leg_fuel = 0.0
        voyage_leg_port = 0.0
        voyage_leg_opex = 0.0
        voyage_leg_distance = 0.0
        in_leg = False

        for d in days:
            cargo_pct = d.get("cargo_qty_avg") or 0
            dist = d.get("distance_total_nm") or 0
            in_voyage = cargo_pct > 30 and dist > 0

            if in_voyage:
                if not in_leg:
                    in_leg = True
                    voyage_leg_days = 0
                    voyage_leg_revenue = 0.0
                    voyage_leg_fuel = 0.0
                    voyage_leg_port = 0.0
                    voyage_leg_opex = 0.0
                    voyage_leg_distance = 0.0

                day_revenue = (cargo_pct / 100) * cargo_cap * 450 / 1000 * DEMO_RATE_USD_PER_MT
                fuel_kg = d.get("fuel_consumption_total_kg") or 0
                quarter = _quarter_from_date(d.get("day", ""))
                day_fuel_cost = fuel_kg * BUNKER_PRICES["LNG"][quarter] / 1000

                voyage_leg_days += 1
                voyage_leg_revenue += day_revenue
                voyage_leg_fuel += day_fuel_cost
                voyage_leg_opex += DAILY_OPEX_USD
                voyage_leg_distance += dist

                total_days += 1
                total_revenue += day_revenue
                total_fuel_cost += day_fuel_cost
                total_opex += DAILY_OPEX_USD
                total_distance += dist
            else:
                if in_leg and voyage_leg_days > 0:
                    total_port_costs += PORT_COST_AVG_USD
                    voyage_leg_port += PORT_COST_AVG_USD
                in_leg = False

        if in_leg and voyage_leg_days > 0:
            total_port_costs += PORT_COST_AVG_USD

        net_profit = total_revenue - total_fuel_cost - total_port_costs - total_opex
        total_cost = total_fuel_cost + total_port_costs + total_opex
        roi_pct = (net_profit / total_cost * 100) if total_cost > 0 else 0
        cost_per_nm = (total_fuel_cost / total_distance) if total_distance > 0 else 0

        total_cargo_mt = 0
        for d in days:
            cargo_pct = d.get("cargo_qty_avg") or 0
            total_cargo_mt += (cargo_pct / 100) * cargo_cap * 450 / 1000
        revenue_per_tonne = (total_revenue / total_cargo_mt) if total_cargo_mt > 0 else 0

        results.append({
            "vessel_id": vid,
            "vessel_name": reg.get("name", vid),
            "total_days": total_days,
            "revenue": _round(total_revenue),
            "fuel_cost": _round(total_fuel_cost),
            "port_cost": _round(total_port_costs),
            "opex": _round(total_opex),
            "net_profit": _round(net_profit),
            "roi_pct": _round(roi_pct, 1),
            "cost_per_nm": _round(cost_per_nm),
            "revenue_per_tonne_usd": _round(revenue_per_tonne),
        })

    fleet_total_revenue = _round(sum(v["revenue"] for v in results))
    fleet_total_fuel_cost = _round(sum(v["fuel_cost"] for v in results))
    fleet_net_profit = _round(sum(v["net_profit"] for v in results))
    total_cost = fleet_total_fuel_cost + _round(sum(v["port_cost"] for v in results)) + _round(sum(v["opex"] for v in results))
    fleet_roi = _round((fleet_net_profit / total_cost * 100) if total_cost > 0 else 0, 1)

    return {
        "vessels": results,
        "total_revenue": fleet_total_revenue,
        "total_fuel_cost": fleet_total_fuel_cost,
        "net_profit": fleet_net_profit,
        "roi_pct": fleet_roi,
    }


@router.get("/voyage-pnl/{vessel_id}")
async def voyage_pnl_detail(vessel_id: str):
    db = _analytics_db()
    if db is None:
        return {"error": "Analytics database not found. Run the aggregation pipeline first."}

    vessels = _vessel_registry_map(db)
    reg = vessels.get(vessel_id, {})
    cargo_cap = reg.get("cargo_capacity_m3", 174000)

    rows = db.fetchall("""
        SELECT * FROM telemetry_daily
        WHERE vessel_id = ?
        ORDER BY day
    """, (vessel_id,))

    daily = []
    for r in rows:
        r = dict(r)
        cargo_pct = r.get("cargo_qty_avg") or 0
        fuel_kg = r.get("fuel_consumption_total_kg") or 0
        quarter = _quarter_from_date(r.get("day", ""))
        dist = r.get("distance_total_nm") or 0
        in_voyage = cargo_pct > 30 and dist > 0

        revenue = (cargo_pct / 100) * cargo_cap * 450 / 1000 * DEMO_RATE_USD_PER_MT if in_voyage else 0
        fuel_cost = fuel_kg * BUNKER_PRICES["LNG"][quarter] / 1000
        port_cost = PORT_COST_AVG_USD if not in_voyage else 0
        opex = DAILY_OPEX_USD
        net_pnl = revenue - fuel_cost - port_cost - opex

        daily.append({
            "day": r["day"],
            "revenue_usd": _round(revenue),
            "fuel_cost_usd": _round(fuel_cost),
            "port_cost_usd": _round(port_cost),
            "opex_usd": _round(opex),
            "net_pnl_usd": _round(net_pnl),
        })

    return {"vessel_id": vessel_id, "name": reg.get("name", vessel_id), "days": daily}


@router.get("/cp-compliance")
async def cp_compliance():
    db = _analytics_db()
    if db is None:
        return {"error": "Analytics database not found. Run the aggregation pipeline first."}

    vessels = _vessel_registry_map(db)

    rows = db.fetchall("""
        SELECT vr.vessel_id, vr.name, vr.service_speed_kn, vr.engine_mcr_kw,
               AVG(td.sog_avg) AS avg_speed,
               AVG(td.fuel_consumption_total_kg / NULLIF(td.distance_total_nm, 0) * td.sog_avg) AS avg_consumption_kg_h,
               AVG(td.sog_avg + 0.5 * td.wind_speed_avg + 0.3 * td.wave_height_avg) AS avg_weather_corrected_speed,
               SUM(CASE WHEN td.sog_avg + 0.5 * td.wind_speed_avg + 0.3 * td.wave_height_avg >= vr.service_speed_kn * 0.95 THEN 1 ELSE 0 END) AS compliant_days,
               COUNT(*) AS total_days
        FROM vessel_registry vr
        JOIN telemetry_daily td ON vr.vessel_id = td.vessel_id
        GROUP BY vr.vessel_id
    """)

    results = []
    for r in rows:
        r = dict(r)
        warranted_speed = r["service_speed_kn"] or 19.5
        warranted_consumption = (r["engine_mcr_kw"] or 80000) * SFOC_REFERENCE_G_KWH / 1e6

        actual_speed = r["avg_speed"] or 0
        actual_consumption = r["avg_consumption_kg_h"] or 0

        speed_deviation = ((actual_speed - warranted_speed) / warranted_speed * 100) if warranted_speed else 0
        consumption_deviation = ((actual_consumption - warranted_consumption) / warranted_consumption * 100) if warranted_consumption else 0

        total_days = r["total_days"] or 1
        compliant_days = r["compliant_days"] or 0
        compliant_pct = (compliant_days / total_days * 100) if total_days else 0

        results.append({
            "vessel_id": r["vessel_id"],
            "vessel_name": r["name"],
            "actual_speed": _round(actual_speed),
            "warranted_speed": _round(warranted_speed),
            "weather_corrected_speed": _round(r["avg_weather_corrected_speed"] or 0),
            "speed_deviation_pct": _round(speed_deviation, 1),
            "consumption_deviation_pct": _round(consumption_deviation, 1),
        })

    avg_speed_dev = _round(statistics.mean([v["speed_deviation_pct"] for v in results]), 1) if results else 0
    avg_consumption_dev = _round(statistics.mean([v["consumption_deviation_pct"] for v in results]), 1) if results else 0
    compliant_count = sum(1 for v in results if v["speed_deviation_pct"] <= 5)
    non_compliant_count = len(results) - compliant_count

    return {
        "vessels": results,
        "avg_speed_dev": avg_speed_dev,
        "avg_consumption_dev": avg_consumption_dev,
        "compliant_count": compliant_count,
        "non_compliant_count": non_compliant_count,
    }


@router.get("/cp-compliance/{vessel_id}")
async def cp_compliance_detail(vessel_id: str):
    db = _analytics_db()
    if db is None:
        return {"error": "Analytics database not found. Run the aggregation pipeline first."}

    vessels = _vessel_registry_map(db)
    reg = vessels.get(vessel_id, {})
    warranted_speed = reg.get("service_speed_kn") or 19.5
    mcr_kw = reg.get("engine_mcr_kw") or 80000
    warranted_consumption = mcr_kw * SFOC_REFERENCE_G_KWH / 1e6

    rows = db.fetchall("""
        SELECT * FROM telemetry_daily
        WHERE vessel_id = ?
        ORDER BY day
    """, (vessel_id,))

    daily = []
    for r in rows:
        r = dict(r)
        actual_speed = r.get("sog_avg") or 0
        wind = r.get("wind_speed_avg") or 0
        wave = r.get("wave_height_avg") or 0
        fuel_kg = r.get("fuel_consumption_total_kg") or 0
        dist = r.get("distance_total_nm") or 0
        hours = 24

        actual_consumption = (fuel_kg / dist * actual_speed) if dist > 0 and actual_speed > 0 else 0

        weather_corrected_speed = actual_speed + 0.5 * wind + 0.3 * wave
        speed_deviation = ((actual_speed - warranted_speed) / warranted_speed * 100) if warranted_speed else 0
        consumption_deviation = ((actual_consumption - warranted_consumption) / warranted_consumption * 100) if warranted_consumption else 0
        compliant = weather_corrected_speed >= warranted_speed * 0.95

        daily.append({
            "day": r["day"],
            "actual_speed": _round(actual_speed),
            "warranted_speed": _round(warranted_speed),
            "weather_corrected_speed": _round(weather_corrected_speed),
            "speed_deviation_pct": _round(speed_deviation, 1),
            "actual_consumption": _round(actual_consumption),
            "warranted_consumption": _round(warranted_consumption),
            "consumption_deviation_pct": _round(consumption_deviation, 1),
            "compliant": compliant,
        })

    return {"vessel_id": vessel_id, "name": reg.get("name", vessel_id), "daily": daily}


@router.get("/bunker-costs")
async def bunker_costs():
    try:
        db = _analytics_db()
        if db is None:
            return {"error": "Analytics database not found. Run the aggregation pipeline first."}

        vessels = _vessel_registry_map(db)

        rows = db.fetchall("""
            SELECT vr.vessel_id, vr.name, vr.cargo_capacity_m3,
                   SUM(td.fuel_consumption_total_kg) AS total_fuel_kg,
                   SUM(td.distance_total_nm) AS total_distance,
                   SUM(td.fuel_consumption_total_kg / 1000 * CASE
                       WHEN CAST(strftime('%m', td.day) AS INTEGER) BETWEEN 1 AND 3 THEN 550
                       WHEN CAST(strftime('%m', td.day) AS INTEGER) BETWEEN 4 AND 6 THEN 580
                       WHEN CAST(strftime('%m', td.day) AS INTEGER) BETWEEN 7 AND 9 THEN 620
                       ELSE 600 END) AS total_fuel_cost,
                   SUM((td.cargo_qty_avg / 100.0) * vr.cargo_capacity_m3 * 450 / 1000) AS total_cargo_mt
            FROM vessel_registry vr
            JOIN telemetry_daily td ON vr.vessel_id = td.vessel_id
            GROUP BY vr.vessel_id
        """)

        monthly_costs = db.fetchall("""
            SELECT td.vessel_id,
                   strftime('%Y-%m', td.day) AS month,
                   SUM(td.fuel_consumption_total_kg / 1000 * CASE
                       WHEN CAST(strftime('%m', td.day) AS INTEGER) BETWEEN 1 AND 3 THEN 550
                       WHEN CAST(strftime('%m', td.day) AS INTEGER) BETWEEN 4 AND 6 THEN 580
                       WHEN CAST(strftime('%m', td.day) AS INTEGER) BETWEEN 7 AND 9 THEN 620
                       ELSE 600 END) AS cost_usd
            FROM telemetry_daily td
            GROUP BY td.vessel_id, month
            ORDER BY td.vessel_id, month
        """)

        monthly_map = defaultdict(list)
        for mc in monthly_costs:
            monthly_map[mc["vessel_id"]].append({"month": mc["month"], "cost_usd": _round(mc["cost_usd"])})

        results = []
        for r in rows:
            r = dict(r)
            total_fuel_kg = r["total_fuel_kg"] or 0
            total_fuel_mt = total_fuel_kg / 1000
            total_cost = r["total_fuel_cost"] or 0
            total_dist = r["total_distance"] or 0
            total_cargo = r["total_cargo_mt"] or 0

            results.append({
                "vessel_id": r["vessel_id"],
                "vessel_name": r["name"],
                "fuel_cost": _round(total_cost),
                "total_fuel_mt": _round(total_fuel_mt),
                "avg_cost_per_nm_usd": _round(total_cost / total_dist) if total_dist > 0 else 0,
                "avg_cost_per_tonne_cargo_usd": _round(total_cost / total_cargo) if total_cargo > 0 else 0,
                "fuel_cost_trend": monthly_map.get(r["vessel_id"], []),
            })

        fleet_total_fuel_mt = _round(sum(v["total_fuel_mt"] for v in results))
        fleet_total_fuel_cost = _round(sum(v["fuel_cost"] for v in results))
        avg_cost_per_nm = _round(sum(v["avg_cost_per_nm_usd"] for v in results) / len(results), 2) if results else 0
        avg_cost_per_tonne = _round(sum(v["avg_cost_per_tonne_cargo_usd"] for v in results) / len(results), 2) if results else 0

        return {
            "vessels": results,
            "total_fuel_mt": fleet_total_fuel_mt,
            "total_fuel_cost": fleet_total_fuel_cost,
            "avg_cost_per_nm": avg_cost_per_nm,
            "avg_cost_per_tonne": avg_cost_per_tonne,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e), "type": type(e).__name__}


@router.get("/bog-impact")
async def bog_impact():
    try:
        db = _analytics_db()
        if db is None:
            return {"error": "Analytics database not found. Run the aggregation pipeline first."}

        vessels = _vessel_registry_map(db)

        rows = db.fetchall("""
            SELECT vr.vessel_id, vr.name, vr.cargo_capacity_m3,
                   AVG(td.bog_rate_avg) AS avg_bog_rate,
                   SUM(td.fuel_consumption_total_kg) AS total_fuel_kg,
                   SUM((td.cargo_qty_avg / 100.0) * vr.cargo_capacity_m3 * 450 / 1000) AS total_cargo_mt
            FROM vessel_registry vr
            JOIN telemetry_daily td ON vr.vessel_id = td.vessel_id
            GROUP BY vr.vessel_id
        """)

        monthly_bog = db.fetchall("""
            SELECT td.vessel_id,
                   strftime('%Y-%m', td.day) AS month,
                   AVG(td.bog_rate_avg) AS bog_rate,
                   SUM(td.fuel_consumption_total_kg) AS fuel_kg,
                   SUM((td.cargo_qty_avg / 100.0) * vr.cargo_capacity_m3 * 450 / 1000) AS cargo_mt
            FROM vessel_registry vr
            JOIN telemetry_daily td ON vr.vessel_id = td.vessel_id
            GROUP BY td.vessel_id, month
            ORDER BY td.vessel_id, month
        """)

        monthly_map = defaultdict(list)
        for mb in monthly_bog:
            cargo_mt = mb["cargo_mt"] or 1
            bog_pct = (mb["fuel_kg"] or 0) / cargo_mt * 100 if cargo_mt else 0
            monthly_map[mb["vessel_id"]].append({
                "month": mb["month"],
                "bog_rate": _round(mb["bog_rate"] or 0, 4),
                "bog_pct": _round(bog_pct, 2),
            })

        results = []
        fleet_bog_mt = 0.0
        fleet_bog_cost = 0.0
        for r in rows:
            r = dict(r)
            cargo_cap = r["cargo_capacity_m3"] or 174000
            avg_bog = r["avg_bog_rate"] or 0
            total_cargo = r["total_cargo_mt"] or 1

            bog_mt = (avg_bog * 24 / 1000) if avg_bog else 0
            bog_pct = (bog_mt / total_cargo * 100) if total_cargo else 0
            bog_cost = avg_bog * 24 / 1000 * cargo_cap * 450 / 1000 * DEMO_RATE_USD_PER_MT * 365

            fleet_bog_mt += bog_mt
            fleet_bog_cost += bog_cost

            results.append({
                "vessel_id": r["vessel_id"],
                "vessel_name": r["name"],
                "bog_pct": _round(bog_pct, 2),
                "bog_cost_usd": _round(bog_cost),
                "avg_bog_rate_kg_h": _round(avg_bog, 4),
                "bog_trend": monthly_map.get(r["vessel_id"], []),
            })

        fleet_bog_pct_of_cargo = _round(statistics.mean([v["bog_pct"] for v in results]), 2) if results else 0

        return {
            "vessels": results,
            "total_bog_mt": _round(fleet_bog_mt),
            "bog_pct_of_cargo": fleet_bog_pct_of_cargo,
            "total_bog_cost": _round(fleet_bog_cost),
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e), "type": type(e).__name__}


@router.get("/offhire-risk")
async def offhire_risk():
    db = _analytics_db()
    if db is None:
        return {"error": "Analytics database not found. Run the aggregation pipeline first."}

    vessels = _vessel_registry_map(db)

    vessel_ids = [v["vessel_id"] for v in db.fetchall("SELECT vessel_id FROM vessel_registry ORDER BY vessel_id")]

    results = []
    for vid in vessel_ids:
        reg = vessels.get(vid, {})
        rows = db.fetchall("""
            SELECT * FROM telemetry_daily
            WHERE vessel_id = ?
            ORDER BY day
        """, (vid,))

        if len(rows) < 60:
            continue

        all_days = [dict(r) for r in rows]
        first_30 = all_days[:30]
        last_30 = all_days[-30:]

        avg_speed_first = statistics.mean([d.get("sog_avg") or 0 for d in first_30])
        avg_speed_last = statistics.mean([d.get("sog_avg") or 0 for d in last_30])
        speed_degradation = max(0, (avg_speed_first - avg_speed_last) / avg_speed_first * 100) if avg_speed_first else 0

        avg_sfoc_first = statistics.mean([d.get("sfoc_avg") or 0 for d in first_30])
        avg_sfoc_last = statistics.mean([d.get("sfoc_avg") or 0 for d in last_30])
        sfoc_degradation = max(0, (avg_sfoc_last - avg_sfoc_first) / avg_sfoc_first * 100) if avg_sfoc_first else 0

        total_alarms_last_30 = sum(d.get("alarm_count") or 0 for d in last_30)
        alarm_score = min(100, total_alarms_last_30 * 2)

        load_values = [d.get("engine_load_avg") or 0 for d in last_30]
        load_std = statistics.stdev(load_values) if len(load_values) > 1 else 0
        engine_stability = min(100, load_std * 10)

        imo = reg.get("imo") or "9999999"
        try:
            imo_num = int(imo)
        except (ValueError, TypeError):
            imo_num = 9999999
        age_score = min(100, max(0, (imo_num - 9000000) / 10000))

        risk_score = (
            speed_degradation * 0.30 +
            sfoc_degradation * 0.25 +
            alarm_score * 0.20 +
            engine_stability * 0.15 +
            age_score * 0.10
        )

        if risk_score < 25:
            risk_level = "low"
        elif risk_score < 50:
            risk_level = "medium"
        else:
            risk_level = "high"

        mid = len(all_days) // 2
        first_half_speed = statistics.mean([d.get("sog_avg") or 0 for d in all_days[:mid]])
        second_half_speed = statistics.mean([d.get("sog_avg") or 0 for d in all_days[mid:]])
        if second_half_speed > first_half_speed * 1.02:
            trend = "improving"
        elif second_half_speed < first_half_speed * 0.98:
            trend = "worsening"
        else:
            trend = "stable"

        results.append({
            "vessel_id": vid,
            "vessel_name": reg.get("name", vid),
            "risk_score": _round(risk_score, 1),
            "risk_level": risk_level,
            "speed_degradation_pct": _round(speed_degradation, 1),
            "sfoc_degradation_pct": _round(sfoc_degradation, 1),
            "alarms": _round(alarm_score, 1),
            "trend": trend,
        })

    results.sort(key=lambda x: x["risk_score"], reverse=True)
    high_risk = sum(1 for v in results if v["risk_level"] == "high")
    medium_risk = sum(1 for v in results if v["risk_level"] == "medium")
    low_risk = sum(1 for v in results if v["risk_level"] == "low")
    avg_risk = _round(statistics.mean([v["risk_score"] for v in results]), 1) if results else 0

    return {
        "vessels": results,
        "high_risk": high_risk,
        "medium_risk": medium_risk,
        "low_risk": low_risk,
        "avg_risk_score": avg_risk,
    }


@router.get("/carbon-cost")
async def carbon_cost():
    db = _analytics_db()
    if db is None:
        return {"error": "Analytics database not found. Run the aggregation pipeline first."}

    vessels = _vessel_registry_map(db)

    rows = db.fetchall("""
        SELECT vr.vessel_id, vr.name, vr.cargo_capacity_m3,
               SUM(td.co2_total_mt) AS total_co2_mt,
               SUM(td.distance_total_nm) AS total_distance,
               SUM((td.cargo_qty_avg / 100.0) * vr.cargo_capacity_m3 * 450 / 1000) AS total_cargo_mt
        FROM vessel_registry vr
        JOIN telemetry_daily td ON vr.vessel_id = td.vessel_id
        GROUP BY vr.vessel_id
    """)

    results = []
    for r in rows:
        r = dict(r)
        co2 = r["total_co2_mt"] or 0
        dist = r["total_distance"] or 0
        cargo = r["total_cargo_mt"] or 1

        eu_ets_eur = co2 * EU_ETS_PRICE_EUR
        eu_ets_usd = eu_ets_eur * EUR_USD

        cii_raw = co2 / (dist * cargo) if dist > 0 and cargo > 0 else 999
        if cii_raw <= CII_BOUNDARIES["A"]:
            cii_rating = "A"
        elif cii_raw <= CII_BOUNDARIES["B"]:
            cii_rating = "B"
        elif cii_raw <= CII_BOUNDARIES["C"]:
            cii_rating = "C"
        elif cii_raw <= CII_BOUNDARIES["D"]:
            cii_rating = "D"
        else:
            cii_rating = "E"

        carbon_cost_per_nm = (eu_ets_usd / dist) if dist > 0 else 0
        carbon_cost_per_tonne = (eu_ets_usd / cargo) if cargo > 0 else 0

        results.append({
            "vessel_id": r["vessel_id"],
            "vessel_name": r["name"],
            "co2_mt": _round(co2),
            "ets_cost": _round(eu_ets_usd),
            "cii_rating": cii_rating,
            "cii_score": _round(cii_raw, 4),
            "cost_per_nm": _round(carbon_cost_per_nm),
            "carbon_cost_per_tonne_cargo": _round(carbon_cost_per_tonne),
        })

    fleet_total_co2 = _round(sum(v["co2_mt"] for v in results))
    fleet_eu_ets_cost = _round(sum(v["ets_cost"] for v in results))
    avg_carbon_cost = _round(statistics.mean([v["cost_per_nm"] for v in results]), 2) if results else 0
    cii_compliant_count = sum(1 for v in results if v["cii_rating"] in ("A", "B", "C"))

    return {
        "vessels": results,
        "total_co2_mt": fleet_total_co2,
        "eu_ets_cost": fleet_eu_ets_cost,
        "avg_carbon_cost_per_nm": avg_carbon_cost,
        "cii_compliant_count": cii_compliant_count,
    }


@router.get("/utilization")
async def utilization():
    try:
        db = _analytics_db()
        if db is None:
            return {"error": "Analytics database not found. Run the aggregation pipeline first."}

        vessels = _vessel_registry_map(db)

        rows = db.fetchall("""
            SELECT td.*, vr.name
            FROM telemetry_daily td
            JOIN vessel_registry vr ON td.vessel_id = vr.vessel_id
            WHERE td.day >= date((SELECT MAX(day) FROM telemetry_daily), '-30 days')
            ORDER BY td.vessel_id, td.day
        """)

        vessel_days = defaultdict(list)
        for r in rows:
            vessel_days[r["vessel_id"]].append(dict(r))

        results = []
        for vid, days in vessel_days.items():
            reg = vessels.get(vid, {})
            latest = days[-1] if days else {}

            cargo_pct = latest.get("cargo_qty_avg") or 0
            sog = latest.get("sog_avg") or 0
            lat = latest.get("lat_avg")
            lon = latest.get("lon_avg")

            if cargo_pct > 30 and sog > 5:
                status = "laden"
            elif cargo_pct <= 30 and sog > 5:
                status = "ballast"
            elif sog <= 2:
                status = "port"
            else:
                status = "idle"

            laden_ballast_days = sum(1 for d in days if (d.get("cargo_qty_avg") or 0) > 30 and (d.get("sog_avg") or 0) > 5 or (d.get("cargo_qty_avg") or 0) <= 30 and (d.get("sog_avg") or 0) > 5)
            util_30d = (laden_ballast_days / 30 * 100) if days else 0

            results.append({
                "vessel_id": vid,
                "vessel_name": reg.get("name", vid),
                "status": status,
                "cargo_pct": _round(cargo_pct, 1),
                "speed": _round(sog),
                "utilization_30d_pct": _round(util_30d, 1),
            })

        fleet_utilization = _round(statistics.mean([v["utilization_30d_pct"] for v in results]), 1) if results else 0
        laden_count = sum(1 for v in results if v["status"] == "laden")
        ballast_count = sum(1 for v in results if v["status"] == "ballast")
        idle_count = sum(1 for v in results if v["status"] in ("idle", "port"))

        return {
            "vessels": results,
            "fleet_utilization_pct": fleet_utilization,
            "laden_count": laden_count,
            "ballast_count": ballast_count,
            "idle_count": idle_count,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e), "type": type(e).__name__}


@router.get("/utilization/timeseries")
async def utilization_timeseries(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
):
    db = _analytics_db()
    if db is None:
        return {"error": "Analytics database not found. Run the aggregation pipeline first."}

    query = """
        SELECT td.day,
               SUM(CASE WHEN td.cargo_qty_avg > 30 AND td.sog_avg > 5 THEN 1 ELSE 0 END) AS laden,
               SUM(CASE WHEN td.cargo_qty_avg <= 30 AND td.sog_avg > 5 THEN 1 ELSE 0 END) AS ballast,
               SUM(CASE WHEN td.sog_avg <= 2 THEN 1 ELSE 0 END) AS port,
               SUM(CASE WHEN td.cargo_qty_avg <= 30 AND td.sog_avg <= 5 AND td.sog_avg > 2 THEN 1 ELSE 0 END) AS idle,
               COUNT(*) AS total
        FROM telemetry_daily td
    """
    params: list = []
    conditions = []

    if start:
        conditions.append("td.day >= ?")
        params.append(start)
    if end:
        conditions.append("td.day <= ?")
        params.append(end)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " GROUP BY td.day ORDER BY td.day"

    rows = db.fetchall(query, tuple(params))

    daily = []
    for r in rows:
        r = dict(r)
        total = r["total"] or 1
        laden = r["laden"] or 0
        ballast = r["ballast"] or 0
        active = laden + ballast
        util_pct = (active / total * 100) if total else 0

        daily.append({
            "day": r["day"],
            "laden_count": laden,
            "ballast_count": r["ballast"] or 0,
            "idle_count": r["idle"] or 0,
            "port_count": r["port"] or 0,
            "fleet_utilization_pct": _round(util_pct, 1),
        })

    return {"count": len(daily), "daily": daily}


@router.get("/voyage-compare")
async def voyage_compare(
    vessel_ids: str = Query(..., description="Comma-separated vessel IDs"),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
):
    db = _analytics_db()
    if db is None:
        return {"error": "Analytics database not found. Run the aggregation pipeline first."}

    vessels = _vessel_registry_map(db)
    ids = [v.strip() for v in vessel_ids.split(",") if v.strip()]
    # Normalize integer vessel IDs (1, 2, 3) to analytics format (LNG-001, LNG-002, LNG-003)
    ids = [f"LNG-{int(v):03d}" if v.isdigit() else v for v in ids]

    results = []
    for vid in ids:
        reg = vessels.get(vid, {})
        cargo_cap = reg.get("cargo_capacity_m3", 174000)

        query = "SELECT * FROM telemetry_daily WHERE vessel_id = ?"
        params: list = [vid]

        if start:
            query += " AND day >= ?"
            params.append(start)
        if end:
            query += " AND day <= ?"
            params.append(end)

        query += " ORDER BY day"
        rows = db.fetchall(query, tuple(params))

        total_fuel_kg = 0
        total_co2 = 0
        total_dist = 0
        total_fuel_cost = 0
        total_revenue = 0
        speed_sum = 0
        sfoc_sum = 0
        bog_sum = 0
        count = 0

        for r in rows:
            r = dict(r)
            fuel_kg = r.get("fuel_consumption_total_kg") or 0
            dist = r.get("distance_total_nm") or 0
            cargo_pct = r.get("cargo_qty_avg") or 0
            quarter = _quarter_from_date(r.get("day", ""))

            total_fuel_kg += fuel_kg
            total_co2 += r.get("co2_total_mt") or 0
            total_dist += dist
            total_fuel_cost += fuel_kg * BUNKER_PRICES["LNG"][quarter] / 1000

            if cargo_pct > 30 and dist > 0:
                total_revenue += (cargo_pct / 100) * cargo_cap * 450 / 1000 * DEMO_RATE_USD_PER_MT

            speed_sum += r.get("sog_avg") or 0
            sfoc_sum += r.get("sfoc_avg") or 0
            bog_sum += r.get("bog_rate_avg") or 0
            count += 1

        net_pnl = total_revenue - total_fuel_cost - DAILY_OPEX_USD * count
        avg_speed = (speed_sum / count) if count else 0
        avg_sfoc = (sfoc_sum / count) if count else 0
        avg_bog = (bog_sum / count) if count else 0

        results.append({
            "vessel_id": vid,
            "vessel_name": reg.get("name", vid),
            "avg_speed": _round(avg_speed),
            "fuel_mt": _round(total_fuel_kg / 1000),
            "co2": _round(total_co2),
            "distance": _round(total_dist),
            "sfoc": _round(avg_sfoc),
            "bog_rate": _round(avg_bog, 4),
            "fuel_cost": _round(total_fuel_cost),
            "revenue": _round(total_revenue),
            "net_pnl": _round(net_pnl),
        })

    return {"vessels": results}


@router.get("/benchmark")
async def benchmark():
    db = _analytics_db()
    if db is None:
        return {"error": "Analytics database not found. Run the aggregation pipeline first."}

    vessels = _vessel_registry_map(db)

    MARKET_AVG = {
        "sfoc": 162,
        "eeoi": 0.0042,
        "bog_rate": 0.15,
        "speed": 19.5,
    }

    rows = db.fetchall("""
        SELECT vr.vessel_id, vr.name,
               AVG(td.sfoc_avg) AS sfoc,
               AVG(td.eeoi_avg) AS eeoi,
               AVG(td.bog_rate_avg) AS bog_rate,
               AVG(td.sog_avg) AS speed
        FROM vessel_registry vr
        JOIN telemetry_daily td ON vr.vessel_id = td.vessel_id
        GROUP BY vr.vessel_id
    """)

    results = []
    for r in rows:
        r = dict(r)
        sfoc = r["sfoc"] or 0
        eeoi = r["eeoi"] or 0
        bog = r["bog_rate"] or 0
        speed = r["speed"] or 0

        sfoc_vs = ((sfoc - MARKET_AVG["sfoc"]) / MARKET_AVG["sfoc"] * 100) if MARKET_AVG["sfoc"] else 0
        eeoi_vs = ((eeoi - MARKET_AVG["eeoi"]) / MARKET_AVG["eeoi"] * 100) if MARKET_AVG["eeoi"] else 0
        bog_vs = ((bog - MARKET_AVG["bog_rate"]) / MARKET_AVG["bog_rate"] * 100) if MARKET_AVG["bog_rate"] else 0
        speed_vs = ((speed - MARKET_AVG["speed"]) / MARKET_AVG["speed"] * 100) if MARKET_AVG["speed"] else 0

        sfoc_score = max(0, 100 - abs(sfoc_vs))
        eeoi_score = max(0, 100 - abs(eeoi_vs))
        bog_score = max(0, 100 - abs(bog_vs))
        speed_score = max(0, 100 - abs(speed_vs))
        overall = (sfoc_score + eeoi_score + bog_score + speed_score) / 4

        results.append({
            "vessel_id": r["vessel_id"],
            "vessel_name": r["name"],
            "sfoc": _round(sfoc),
            "sfoc_vs_market": _round(sfoc_vs, 1),
            "eeoi": _round(eeoi, 4),
            "eeoi_vs_market": _round(eeoi_vs, 1),
            "bog": _round(bog, 4),
            "bog_vs_market": _round(bog_vs, 1),
            "speed": _round(speed),
            "speed_vs_market": _round(speed_vs, 1),
            "overall_rank": _round(overall, 1),
        })

    results.sort(key=lambda x: x["overall_rank"], reverse=True)
    for i, r in enumerate(results, 1):
        r["overall_rank"] = i

    market_avg = {
        "sfoc": MARKET_AVG["sfoc"],
        "eeoi": MARKET_AVG["eeoi"],
        "bog": MARKET_AVG["bog_rate"],
        "speed": MARKET_AVG["speed"],
    }

    return {"market_avg": market_avg, "vessels": results}


@router.get("/laytime")
async def laytime():
    db = _analytics_db()
    if db is None:
        return {"error": "Analytics database not found. Run the aggregation pipeline first."}

    vessels = _vessel_registry_map(db)
    vessel_ids = [v["vessel_id"] for v in db.fetchall("SELECT vessel_id FROM vessel_registry ORDER BY vessel_id")]

    results = []
    for vid in vessel_ids:
        reg = vessels.get(vid, {})
        rows = db.fetchall("""
            SELECT * FROM telemetry_daily
            WHERE vessel_id = ?
            ORDER BY day
        """, (vid,))

        all_days = [dict(r) for r in rows]

        port_stays = []
        current_stay = 0
        for d in all_days:
            sog = d.get("sog_avg") or 0
            if sog <= 2:
                current_stay += 1
            else:
                if current_stay > 0:
                    port_stays.append(current_stay)
                current_stay = 0
        if current_stay > 0:
            port_stays.append(current_stay)

        total_port_days = sum(port_stays)
        avg_port_stay = (total_port_days / len(port_stays)) if port_stays else 0
        port_calls = len(port_stays)
        laytime_allowed = port_calls * LAYTIME_ALLOWED_HOURS
        laytime_used = total_port_days * 24
        laytime_deviation = ((laytime_used - laytime_allowed) / laytime_allowed * 100) if laytime_allowed > 0 else 0

        avg_stay_hours = avg_port_stay * 24
        demurrage_risk = "high" if avg_stay_hours > LAYTIME_ALLOWED_HOURS * 1.2 else "low"

        results.append({
            "vessel_id": vid,
            "vessel_name": reg.get("name", vid),
            "port_days": total_port_days,
            "avg_stay": _round(avg_port_stay, 1),
            "port_calls": port_calls,
            "allowed_hours": laytime_allowed,
            "used_hours": _round(laytime_used),
            "deviation_pct": _round(laytime_deviation, 1),
            "demurrage_risk": demurrage_risk,
        })

    fleet_total_port_days = sum(v["port_days"] for v in results)
    fleet_avg_port_stay = _round(statistics.mean([v["avg_stay"] for v in results]), 1) if results else 0
    fleet_total_port_calls = sum(v["port_calls"] for v in results)
    high_risk_count = sum(1 for v in results if v["demurrage_risk"] == "high")

    return {
        "vessels": results,
        "total_port_days": fleet_total_port_days,
        "avg_port_stay": fleet_avg_port_stay,
        "total_port_calls": fleet_total_port_calls,
        "high_risk_count": high_risk_count,
    }

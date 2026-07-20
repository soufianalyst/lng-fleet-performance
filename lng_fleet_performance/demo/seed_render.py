"""Seed the main DB from hardcoded static data.

No database reads needed — all data generated from static_data.py.
Uses psycopg2.extras.execute_values for fast bulk inserts.
"""
import os
import json
import random
import math
from datetime import datetime, timedelta, timezone


def _get_pg_conn():
    url = os.environ.get("DATABASE_URL")
    if not url:
        return None
    try:
        import psycopg2
        conn = psycopg2.connect(url)
        conn.autocommit = True
        return conn
    except Exception as e:
        print(f"[seed] PostgreSQL connection failed: {e}")
        return None


def seed_if_empty(db):
    """Check if main DB is empty; if so, seed from static data."""
    try:
        row = db.fetchone("SELECT COUNT(*) as cnt FROM vessels")
        cnt = dict(row).get("cnt", 0) if row else 0
    except Exception:
        cnt = 0
    if cnt > 0:
        print(f"[seed] Main DB already has {cnt} vessels — skipping")
        return False

    pg_conn = _get_pg_conn()
    if pg_conn is None:
        print("[seed] No PostgreSQL — skipping seed")
        return False

    print("[seed] Main DB empty — seeding from static data...")

    try:
        from .static_data import (
            generate_all_vessel_rows, generate_all_tank_rows,
            generate_all_voyage_rows, generate_all_waypoint_rows,
            generate_all_certificate_rows, generate_all_cii_rows,
            generate_all_hull_rows, generate_all_digital_twin_rows,
            generate_all_alert_rows, generate_all_charter_party_rows,
        )
        from psycopg2.extras import execute_values

        cur = pg_conn.cursor()

        eca_rows = _generate_eca()
        execute_values(cur, """INSERT INTO eca_zones
            (zone_name, zone_type, sox_limit_pct, nox_tier, effective_date,
             boundary_polygon, status) VALUES %s
            ON CONFLICT (zone_name) DO UPDATE SET zone_type=EXCLUDED.zone_type""",
            eca_rows, page_size=50)
        print(f"  [seed] eca_zones: {len(eca_rows)}")

        vessel_rows = generate_all_vessel_rows()
        execute_values(cur, """INSERT INTO vessels
            (vessel_id, imo_number, vessel_name, vessel_type, flag_state,
             classification_society, gross_tonnage, deadweight_tonnage,
             cargo_capacity_m3, number_of_tanks, propulsion_type,
             engine_manufacturer, engine_model, engine_mcr_kw,
             service_speed_kn, design_speed_kn, eexi_value, eedi_value,
             cii_reference_value, year_of_build, scrubber_equipped,
             reliquefaction_plant) VALUES %s
            ON CONFLICT (imo_number) DO NOTHING""", vessel_rows, page_size=50)
        print(f"  [seed] vessels: {len(vessel_rows)}")

        tank_rows = generate_all_tank_rows()
        execute_values(cur, """INSERT INTO vessel_tanks
            (vessel_id, tank_name, tank_position, capacity_m3,
             design_pressure_bar, design_temperature_k, insulation_type)
            VALUES %s ON CONFLICT (vessel_id, tank_name) DO NOTHING""",
            tank_rows, page_size=100)
        print(f"  [seed] vessel_tanks: {len(tank_rows)}")

        voyage_rows, wp_meta = generate_all_voyage_rows()
        execute_values(cur, """INSERT INTO voyages
            (vessel_id, voyage_number, charterer, load_port, discharge_port,
             cargo_quantity_mt, cargo_type, planned_departure, actual_departure,
             planned_arrival, actual_arrival, status, route_type,
             total_distance_nm, total_fuel_lng_mt, total_bog_mt, co2_total_mt,
             eca_time_hours, eu_ets_applicable) VALUES %s
            ON CONFLICT (vessel_id, voyage_number) DO NOTHING""", voyage_rows, page_size=100)
        print(f"  [seed] voyages: {len(voyage_rows)}")

        cur.execute("SELECT voyage_id, vessel_id, voyage_number FROM voyages ORDER BY voyage_id")
        vmap = {(r[1], r[2]): r[0] for r in cur.fetchall()}

        wp_rows = generate_all_waypoint_rows(vmap, wp_meta)
        if wp_rows:
            execute_values(cur, """INSERT INTO voyage_waypoints
                (voyage_id, sequence_num, latitude, longitude, waypoint_name,
                 speed_planned_kn, speed_actual_kn, course_deg, in_eca,
                 weather_hs_m, wind_speed_kn) VALUES %s""",
                wp_rows, page_size=200)
        print(f"  [seed] voyage_waypoints: {len(wp_rows)}")

        cert_rows = generate_all_certificate_rows()
        execute_values(cur, """INSERT INTO certificates
            (vessel_id, cert_type, cert_number, issuing_authority,
             issue_date, expiry_date, status, notes) VALUES %s""",
            cert_rows, page_size=100)
        print(f"  [seed] certificates: {len(cert_rows)}")

        cii_rows = generate_all_cii_rows()
        execute_values(cur, """INSERT INTO cii_assessment
            (vessel_id, assessment_year, assessment_date, annual_co2_mt,
             annual_cargo_mt_nm, cii_calculated, cii_rating,
             distance_sailed_nm, cargo_carried_mt,
             port_time_hours, sea_time_hours, fuel_lng_mt, bog_consumed_mt,
             cii_required, rating_boundary_a, rating_boundary_b,
             rating_boundary_c, rating_boundary_d) VALUES %s""",
            [(d[0], 2025, d[1], d[2], d[3], d[4], d[5],
              d[6], d[7], d[8], d[9], d[10], d[11],
              6.40, 5.05, 5.70, 6.40, 7.15) for d in cii_rows],
            page_size=50)
        print(f"  [seed] cii_assessment: {len(cii_rows)}")

        hull_rows = generate_all_hull_rows()
        execute_values(cur, """INSERT INTO hull_performance
            (vessel_id, record_date, speed_kn, shaft_power_kw,
             wind_speed_kn, wind_direction_deg, sea_state,
             water_temp_k, draft_fwd_m, draft_aft_m, trim_m,
             reference_power_kw, power_deviation_pct,
             equivalent_roughness_mm, fouling_level, qpc_trending) VALUES %s""",
            hull_rows, page_size=100)
        print(f"  [seed] hull_performance: {len(hull_rows)}")

        dt_rows = generate_all_digital_twin_rows()
        execute_values(cur, """INSERT INTO digital_twin_state
            (vessel_id, record_timestamp, engine_health_index,
             hull_health_index, bog_system_health,
             predicted_rul_engine_days, predicted_rul_hull_days,
             anomaly_score, model_version) VALUES %s""",
            dt_rows, page_size=100)
        print(f"  [seed] digital_twin_state: {len(dt_rows)}")

        alert_rows = generate_all_alert_rows()
        execute_values(cur, """INSERT INTO predictive_alerts
            (vessel_id, alert_timestamp, alert_type, severity, component,
             description, predicted_failure_days, confidence_pct,
             recommended_action, acknowledged, resolved) VALUES %s""",
            alert_rows, page_size=50)
        print(f"  [seed] predictive_alerts: {len(alert_rows)}")

        cur.execute("SELECT voyage_id FROM voyages ORDER BY voyage_id LIMIT 100")
        voyage_ids = [r[0] for r in cur.fetchall()]
        cp_rows = generate_all_charter_party_rows(voyage_ids)
        execute_values(cur, """INSERT INTO charter_party
            (voyage_id, charterer, charter_type, speed_warranted_kn,
             consumption_warranted_mt_day, consumption_tolerance_pct,
             bor_warranted_pct_day, bor_tolerance_pct, sea_margin_pct,
             weather_exclusion_beaufort, off_hire_rate_usd_day,
             performance_warranty, contract_start, contract_end) VALUES %s""",
            cp_rows, page_size=50)
        print(f"  [seed] charter_party: {len(cp_rows)}")

        cur.execute("SELECT COUNT(*) FROM vessels")
        count = cur.fetchone()[0]
        print(f"[seed] Done — {count} vessels seeded")
        return True
    except Exception as e:
        print(f"[seed] Error during seeding: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        pg_conn.close()


def _generate_eca():
    from ..utils.geofencing import PREDEFINED_ECA_ZONES
    rows = []
    for z in PREDEFINED_ECA_ZONES:
        poly = json.dumps(z.boundary_polygon) if z.boundary_polygon else ""
        rows.append((z.zone_name, z.zone_type, z.sox_limit_pct,
                     z.nox_tier, z.effective_date, poly, z.status))
    return rows

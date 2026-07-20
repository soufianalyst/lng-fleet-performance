"""Seed the main DB from PostgreSQL analytics data on first startup.

When the main DB is empty (no vessels), reads vessel_registry from
the same PostgreSQL database and populates the main tables so the
frontend works.
"""
import os
import random
import math
from datetime import datetime, timedelta, timezone


def _get_pg_cur():
    """Get a cursor from the DATABASE_URL connection."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        return None, None
    try:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(url)
        conn.autocommit = True
        return conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    except Exception as e:
        print(f"[seed] PostgreSQL connection failed: {e}")
        return None, None


def seed_if_empty(db):
    """Check if main DB is empty; if so, seed from vessel_registry."""
    try:
        row = db.fetchone("SELECT COUNT(*) as cnt FROM vessels")
        cnt = dict(row).get("cnt", 0) if row else 0
    except Exception:
        cnt = 0
    if cnt > 0:
        print(f"[seed] Main DB already has {cnt} vessels — skipping")
        return False

    pg_conn, cur = _get_pg_cur()
    if cur is None:
        print("[seed] No PostgreSQL — skipping seed")
        return False

    print("[seed] Main DB empty — seeding from vessel_registry...")

    try:
        _seed_eca_zones(db, cur)
        _seed_vessels(db, cur)
        _seed_tanks(db, cur)
        _seed_voyages(db, cur)
        _seed_certificates(db, cur)
        _seed_cii(db, cur)
        _seed_hull_performance(db, cur)
        _seed_digital_twin(db, cur)
        _seed_predictive_alerts(db, cur)
        _seed_charter_parties(db, cur)

        row = db.fetchone("SELECT COUNT(*) as cnt FROM vessels")
        count = dict(row).get("cnt", 0) if row else 0
        print(f"[seed] Done — {count} vessels seeded")
        return True
    except Exception as e:
        print(f"[seed] Error during seeding: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        pg_conn.close()


def _seed_eca_zones(db, pg_cur):
    from ..utils.geofencing import PREDEFINED_ECA_ZONES
    for zone in PREDEFINED_ECA_ZONES:
        zone.save(db)


def _seed_vessels(db, pg_cur):
    pg_cur.execute("SELECT * FROM vessel_registry ORDER BY name")
    rows = pg_cur.fetchall()

    flags = ["MH", "PA", "NO", "SG", "GB", "BS", "HK", "MT", "LR", "IT",
             "NL", "DE", "JM", "GR", "KY"]
    engine_mfr = {"ME-GI": "MAN Energy Solutions", "X-DF": "WinGD"}
    engine_model = {"ME-GI": "ME-GI 7G80", "X-DF": "X-DF 7G80"}

    for d in rows:
        vessel_id_str = d.get("vessel_id", "")
        try:
            vessel_id_num = int(vessel_id_str.split("-")[1])
        except (ValueError, IndexError):
            continue

        prop = d.get("propulsion_type", "ME-GI")
        flag = flags[vessel_id_num % len(flags)]

        db.execute("""
            INSERT INTO vessels
            (vessel_id, imo_number, vessel_name, vessel_type, flag_state,
             classification_society, gross_tonnage, deadweight_tonnage,
             cargo_capacity_m3, number_of_tanks, propulsion_type,
             engine_manufacturer, engine_model, engine_mcr_kw,
             service_speed_kn, design_speed_kn, eexi_value, eedi_value,
             cii_reference_value, year_of_build, scrubber_equipped,
             reliquefaction_plant)
            VALUES (?, ?, ?, 'LNG Carrier', ?, 'DNV', ?, ?, ?, 4, ?,
                    ?, ?, ?, ?, ?, ?, ?, 0.96, 2020, 0, 1)
            ON CONFLICT (imo_number) DO NOTHING
        """, (
            vessel_id_num,
            d.get("imo", f"980{vessel_id_num:04d}"),
            d.get("name", f"LNG Vessel {vessel_id_num}"),
            flag,
            (d.get("cargo_capacity_m3") or 170000) * 0.48,
            d.get("cargo_capacity_m3") or 170000,
            d.get("engine_mcr_kw") or 25000,
            prop,
            engine_mfr.get(prop, "MAN Energy Solutions"),
            engine_model.get(prop, "ME-GI 7G80"),
            d.get("engine_mcr_kw") or 25000,
            d.get("service_speed_kn") or 19.5,
            (d.get("service_speed_kn") or 19.5) + 0.5,
            4.80 + (vessel_id_num % 10) * 0.01,
            4.80 + (vessel_id_num % 10) * 0.01 * 0.95,
        ))


def _seed_tanks(db, pg_cur):
    pg_cur.execute("SELECT vessel_id, cargo_capacity_m3 FROM vessel_registry ORDER BY vessel_id")
    for row in pg_cur.fetchall():
        try:
            vid_num = int(row["vessel_id"].split("-")[1])
        except (ValueError, IndexError):
            continue
        capacity = row["cargo_capacity_m3"] or 170000
        tank_cap = capacity / 4
        for i in range(1, 5):
            try:
                db.execute("""
                    INSERT INTO vessel_tanks
                    (vessel_id, tank_name, tank_position, capacity_m3,
                     design_pressure_bar, design_temperature_k, insulation_type)
                    VALUES (?, ?, ?, ?, 1.2, 111.0, 'membrane')
                    ON CONFLICT (vessel_id, tank_name) DO NOTHING
                """, (vid_num, f"Tank {i}",
                      "port" if i <= 2 else "starboard",
                      round(tank_cap, 1)))
            except Exception:
                pass


def _seed_voyages(db, pg_cur):
    pg_cur.execute("""
        SELECT vessel_id, lat_avg, lon_avg, sog_avg, fuel_consumption_total_kg,
               co2_total_mt, distance_total_nm, bog_rate_avg, cargo_qty_avg,
               nox_total_kg
        FROM telemetry_daily
        WHERE (vessel_id, day) IN (
            SELECT vessel_id, MAX(day) FROM telemetry_daily
            GROUP BY vessel_id
        )
    """)
    latest_telemetry = {row["vessel_id"]: row for row in pg_cur.fetchall()}

    ports = [
        ("Ras Laffan", 25.93, 51.56), ("Qatar", 25.29, 51.53),
        ("Ain Sukhna", 29.60, 32.34), ("Dahej", 21.71, 72.56),
        ("Mumbai", 18.95, 72.84), ("Kochi", 9.97, 76.27),
        ("Arzew", 35.85, -0.29), ("Sines", 37.97, -8.87),
        ("Zeebrugge", 51.33, 3.18), ("Soyo", -6.13, 12.37),
        ("Sabine Pass", 29.73, -93.86), ("Freeport TX", 28.95, -95.31),
        ("Ichthys", -12.44, 130.44), ("Gorgon", -20.80, 115.36),
        ("Tangguh", -2.80, 132.38), ("Gladstone", -23.84, 151.27),
        ("Hamad", 25.29, 51.53), ("Basrah", 30.51, 47.81),
    ]

    pg_cur.execute("SELECT vessel_id, name, propulsion_type FROM vessel_registry ORDER BY vessel_id")
    vessel_info = {row["vessel_id"]: (row["name"], row["propulsion_type"]) for row in pg_cur.fetchall()}

    now = datetime.now(timezone.utc)

    for vid_str, tel_data in latest_telemetry.items():
        try:
            vid_num = int(vid_str.split("-")[1])
        except (ValueError, IndexError):
            continue

        vname, prop = vessel_info.get(vid_str, (f"Vessel {vid_num}", "ME-GI"))

        for voyage_idx in range(3):
            days_ago = 30 + voyage_idx * 35
            dep_date = now - timedelta(days=days_ago)
            arr_date = dep_date + timedelta(days=12 + voyage_idx * 2)

            load_idx = (vid_num + voyage_idx) % len(ports)
            disc_idx = (vid_num + voyage_idx + 3) % len(ports)
            load_port = ports[load_idx][0]
            disc_port = ports[disc_idx][0]

            load_lat, load_lon = ports[load_idx][1], ports[load_idx][2]
            disc_lat, disc_lon = ports[disc_idx][1], ports[disc_idx][2]

            dlat = disc_lat - load_lat
            dlon = disc_lon - load_lon
            dist_nm = math.sqrt(dlat**2 + dlon**2) * 60

            cargo_mt = 70000 + (vid_num * 1000) % 15000
            fuel_lng = cargo_mt * 0.0012 * (dist_nm / 1000) * 8
            bog_mt = cargo_mt * 0.0004 * ((arr_date - dep_date).total_seconds() / 86400)

            status = "completed" if voyage_idx > 0 else "in_progress"
            actual_dep = dep_date.isoformat()
            actual_arr = arr_date.isoformat() if status == "completed" else None
            planned_arr = arr_date.isoformat()

            voyage_num = f"V-{vid_num:03d}-2025-{voyage_idx + 1:03d}"

            try:
                db.execute("""
                    INSERT INTO voyages
                    (vessel_id, voyage_number, charterer, load_port, discharge_port,
                     cargo_quantity_mt, cargo_type, planned_departure, actual_departure,
                     planned_arrival, actual_arrival, status, route_type,
                     total_distance_nm, total_fuel_lng_mt, total_bog_mt, co2_total_mt,
                     eca_time_hours, eu_ets_applicable)
                    VALUES (?, ?, ?, ?, ?, ?, 'LNG', ?, ?, ?, ?, ?, 'weather_optimized',
                            ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (vessel_id, voyage_number) DO NOTHING
                """, (
                    vid_num, voyage_num, f"Charterer {vid_num % 5 + 1}",
                    load_port, disc_port, cargo_mt,
                    dep_date.isoformat(), actual_dep, planned_arr, actual_arr,
                    status, round(dist_nm, 0), round(fuel_lng, 1),
                    round(bog_mt, 1), round(fuel_lng * 2.75, 1),
                    12.0 if voyage_idx % 3 == 0 else 0,
                    1 if disc_port in ("Sines", "Zeebrugge", "Arzew", "Ain Sukhna") else 0,
                ))
                row = db.fetchone("SELECT currval(pg_get_serial_sequence('voyages', 'voyage_id')) as id")
                if row:
                    vid = dict(row)["id"]
                    _create_waypoints(db, vid, load_lat, load_lon, disc_lat, disc_lon, 10 + voyage_idx * 2)
            except Exception:
                pass


def _create_waypoints(db, voyage_id, lat1, lon1, lat2, lon2, num_wp):
    for i in range(num_wp):
        frac = i / (num_wp - 1)
        lat = lat1 + frac * (lat2 - lat1) + random.uniform(-0.5, 0.5)
        lon = lon1 + frac * (lon2 - lon1) + random.uniform(-0.5, 0.5)
        speed = 17.5 + random.uniform(-1.5, 2.0)
        course = math.degrees(math.atan2(lon2 - lon1, lat2 - lat1)) % 360
        try:
            db.execute("""
                INSERT INTO voyage_waypoints
                (voyage_id, sequence_num, latitude, longitude, waypoint_name,
                 speed_planned_kn, speed_actual_kn, course_deg, in_eca,
                 weather_hs_m, wind_speed_kn)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                voyage_id, i + 1, round(lat, 4), round(lon, 4),
                f"WP-{i + 1:03d}", round(speed, 1), round(speed + random.uniform(-0.5, 0.5), 1),
                round(course, 1), 1 if abs(lat) > 35 else 0,
                round(random.uniform(0.5, 4.0), 1),
                round(random.uniform(5, 25), 1),
            ))
        except Exception:
            pass


def _seed_certificates(db, pg_cur):
    pg_cur.execute("SELECT vessel_id FROM vessel_registry ORDER BY vessel_id")
    cert_types = [
        ("IAPP", "International Air Pollution Prevention Certificate"),
        ("EIAPP", "Engine International Air Pollution Prevention Certificate"),
        ("IEE", "International Energy Efficiency Certificate"),
        ("IGC", "International Gas Carrier Code Certificate"),
        ("ISM", "International Safety Management Certificate"),
        ("ISPS", "International Ship Security Certificate"),
    ]
    now = datetime.now(timezone.utc)

    for row in pg_cur.fetchall():
        try:
            vid_num = int(row["vessel_id"].split("-")[1])
        except (ValueError, IndexError):
            continue

        for cert_type, cert_name in cert_types:
            issue = now - timedelta(days=random.randint(100, 700))
            expiry = issue + timedelta(days=365 * 5)
            days_left = (expiry - now).days
            status = "valid" if days_left > 0 else "expired"

            if days_left < 120:
                expiry = now + timedelta(days=random.randint(30, 200))
                days_left = (expiry - now).days
                status = "valid"

            try:
                db.execute("""
                    INSERT INTO certificates
                    (vessel_id, cert_type, cert_number, issuing_authority,
                     issue_date, expiry_date, status, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    vid_num, cert_type,
                    f"{cert_type}-{vid_num:03d}-{random.randint(1000, 9999)}",
                    "DNV", issue.strftime("%Y-%m-%d"),
                    expiry.strftime("%Y-%m-%d"), status,
                    f"{cert_name} - auto-generated"
                ))
            except Exception:
                pass


def _seed_cii(db, pg_cur):
    pg_cur.execute("""
        SELECT vessel_id, AVG(avg_speed) as avg_spd,
               SUM(total_fuel_kg) as total_fuel,
               SUM(total_co2_mt) as total_co2,
               SUM(total_distance_nm) as total_dist
        FROM telemetry_daily
        GROUP BY vessel_id
    """)
    cii_data = pg_cur.fetchall()

    now = datetime.now(timezone.utc)
    boundaries = {"A": 5.05, "B": 5.70, "C": 6.40, "D": 7.15}

    for d in cii_data:
        try:
            vid_num = int(d["vessel_id"].split("-")[1])
        except (ValueError, IndexError):
            continue

        total_co2 = d.get("total_co2") or 10000
        total_dist = d.get("total_dist") or 50000
        dwt = 80000 + (vid_num * 500) % 15000

        aer = (total_co2 * 1e6) / (dwt * max(total_dist, 1))
        cii_val = round(aer, 2)

        if cii_val <= boundaries["A"]:
            rating = "A"
        elif cii_val <= boundaries["B"]:
            rating = "B"
        elif cii_val <= boundaries["C"]:
            rating = "C"
        elif cii_val <= boundaries["D"]:
            rating = "D"
        else:
            rating = "E"

        try:
            db.execute("""
                INSERT INTO cii_assessment
                (vessel_id, assessment_year, assessment_date, annual_co2_mt,
                 annual_cargo_mt_nm, cii_calculated, cii_required, cii_rating,
                 rating_boundary_a, rating_boundary_b, rating_boundary_c,
                 rating_boundary_d, distance_sailed_nm, cargo_carried_mt,
                 port_time_hours, sea_time_hours, fuel_lng_mt, bog_consumed_mt)
                VALUES (?, 2025, ?, ?, ?, ?, 6.40, ?, 5.05, 5.70, 6.40, 7.15,
                        ?, ?, ?, ?, ?, ?)
            """, (
                vid_num, now.strftime("%Y-%m-%d"),
                round(total_co2, 1), round(total_dist * dwt * 0.001, 0),
                cii_val, rating,
                round(total_dist, 0), round(total_dist * dwt * 0.001 * 0.85, 0),
                round(random.uniform(500, 1500), 0), round(random.uniform(1500, 4000), 0),
                round(total_co2 * 0.15, 1), round(total_co2 * 0.002, 1),
            ))
        except Exception:
            pass


def _seed_hull_performance(db, pg_cur):
    pg_cur.execute("""
        SELECT vessel_id, AVG(sog_avg) as avg_speed, AVG(shaft_power_kw_avg) as avg_power,
               AVG(trim_avg) as avg_trim
        FROM telemetry_daily
        GROUP BY vessel_id
    """)
    for row in pg_cur.fetchall():
        try:
            vid_num = int(row["vessel_id"].split("-")[1])
        except (ValueError, IndexError):
            continue

        speed = row["avg_speed"] or 18.0
        power = row["avg_power"] or 20000
        trim = row["avg_trim"] or 2.0

        ref_power = 75 * (speed ** 3)
        dev_pct = ((power - ref_power) / max(ref_power, 1)) * 100
        roughness = 0.20 + max(0, dev_pct) * 0.002
        fouling = "clean" if dev_pct < 5 else ("light" if dev_pct < 15 else "moderate")

        now = datetime.now(timezone.utc)
        for days_ago in [0, 30, 60, 90]:
            d = now - timedelta(days=days_ago)
            try:
                db.execute("""
                    INSERT INTO hull_performance
                    (vessel_id, record_date, speed_kn, shaft_power_kw,
                     wind_speed_kn, wind_direction_deg, sea_state,
                     water_temp_k, draft_fwd_m, draft_aft_m, trim_m,
                     reference_power_kw, power_deviation_pct,
                     equivalent_roughness_mm, fouling_level, qpc_trending)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    vid_num, d.strftime("%Y-%m-%d"),
                    round(speed + random.uniform(-0.5, 0.5), 1),
                    round(power + random.uniform(-500, 500), 0),
                    round(random.uniform(5, 20), 1),
                    round(random.uniform(0, 360), 0),
                    random.randint(3, 6),
                    round(288 + random.uniform(-3, 3), 1),
                    round(8.5 + random.uniform(-0.3, 0.3), 2),
                    round(9.5 + random.uniform(-0.3, 0.3), 2),
                    round(trim + random.uniform(-0.2, 0.2), 2),
                    round(ref_power, 0), round(dev_pct, 1),
                    round(roughness + random.uniform(-0.02, 0.02), 3),
                    fouling, round(0.70 + random.uniform(-0.05, 0.05), 3),
                ))
            except Exception:
                pass


def _seed_digital_twin(db, pg_cur):
    pg_cur.execute("SELECT vessel_id FROM vessel_registry ORDER BY vessel_id")
    now = datetime.now(timezone.utc)

    for row in pg_cur.fetchall():
        try:
            vid_num = int(row["vessel_id"].split("-")[1])
        except (ValueError, IndexError):
            continue

        for days_ago in [0, 7, 14, 30]:
            d = now - timedelta(days=days_ago)
            try:
                db.execute("""
                    INSERT INTO digital_twin_state
                    (vessel_id, record_timestamp, engine_health_index,
                     hull_health_index, bog_system_health,
                     predicted_rul_engine_days, predicted_rul_hull_days,
                     anomaly_score, model_version)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'v2.1')
                """, (
                    vid_num, d.isoformat(),
                    round(0.82 + random.uniform(-0.1, 0.15), 3),
                    round(0.88 + random.uniform(-0.08, 0.1), 3),
                    round(0.85 + random.uniform(-0.1, 0.12), 3),
                    round(random.uniform(180, 600), 0),
                    round(random.uniform(200, 800), 0),
                    round(random.uniform(0, 0.3), 3),
                ))
            except Exception:
                pass


def _seed_predictive_alerts(db, pg_cur):
    pg_cur.execute("SELECT vessel_id FROM vessel_registry ORDER BY vessel_id LIMIT 15")
    now = datetime.now(timezone.utc)
    alert_types = [
        ("hull_fouling", "medium", "hull", "Hull fouling degradation detected"),
        ("bor_increase", "low", "cargo", "BOR rate slightly elevated"),
        ("engine_efficiency", "low", "engine", "SFOC deviation above baseline"),
        ("cii_projection", "high", "compliance", "CII rating projected to fall to D"),
        ("certificate_expiry", "medium", "certificates", "IEE certificate expiring within 90 days"),
    ]

    for row in pg_cur.fetchall():
        try:
            vid_num = int(row["vessel_id"].split("-")[1])
        except (ValueError, IndexError):
            continue

        atype, severity, component, desc = random.choice(alert_types)
        try:
            db.execute("""
                INSERT INTO predictive_alerts
                (vessel_id, alert_timestamp, alert_type, severity, component,
                 description, predicted_failure_days, confidence_pct,
                 recommended_action, acknowledged, resolved)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
            """, (
                vid_num, now.isoformat(), atype, severity, component, desc,
                random.randint(30, 180), round(random.uniform(60, 95), 1),
                f"Schedule inspection for {component}"
            ))
        except Exception:
            pass


def _seed_charter_parties(db, pg_cur):
    try:
        voyages = db.fetchall("SELECT voyage_id, vessel_id FROM voyages LIMIT 100")
        charterers = ["Shell International", "BP Gas Marketing", "TotalEnergies LNG",
                      "Qatargas Marketing", "Cheniere Marketing"]
        now = datetime.now(timezone.utc)

        for voy in voyages:
            vid = dict(voy)["voyage_id"]
            try:
                db.execute("""
                    INSERT INTO charter_party
                    (voyage_id, charterer, charter_type, speed_warranted_kn,
                     consumption_warranted_mt_day, consumption_tolerance_pct,
                     bor_warranted_pct_day, bor_tolerance_pct, sea_margin_pct,
                     weather_exclusion_beaufort, off_hire_rate_usd_day,
                     performance_warranty, contract_start, contract_end)
                    VALUES (?, ?, 'voyage', ?, 85.0, 3.0, 0.06, 1.5, 15.0, 6, 35000,
                            'Speed and consumption warranty per BIMCO SHELLTIME4',
                            ?, ?)
                """, (
                    vid, random.choice(charterers),
                    round(18.5 + random.uniform(0, 2), 1),
                    (now - timedelta(days=60)).isoformat(),
                    (now + timedelta(days=300)).isoformat(),
                ))
            except Exception:
                pass
    except Exception:
        pass

#!/usr/bin/env python3
"""
Aggregate raw 30-second LNG telemetry data into analytics-ready hourly/daily tables.

Reads from:  output/sqlite/lng_telemetry.db (50 raw tables)
Writes to:   output/lng_fleet_analytics.db
"""

import os
import sys
import time
import sqlite3
import yaml
from pathlib import Path


RAW_DB = "output/sqlite/lng_telemetry.db"
ANALYTICS_DB = "output/lng_fleet_analytics.db"
VESSEL_CONFIG = "config/vessels.yaml"
NUM_VESSELS = 50
TIMESTEP_SECONDS = 30
TIMESTAMP_OFFSET = 1751328000  # Unix epoch for 2025-07-01T00:00:00Z — offsets raw data to realistic dates


def load_vessel_configs(path: str) -> list[dict]:
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    return data.get("vessels", data) if isinstance(data, dict) else data


def create_vessel_registry(conn: sqlite3.Connection, vessels: list[dict]):
    conn.execute("DROP TABLE IF EXISTS vessel_registry")
    conn.execute("""
        CREATE TABLE vessel_registry (
            vessel_id TEXT PRIMARY KEY,
            name TEXT,
            imo TEXT,
            flag TEXT,
            propulsion_type TEXT,
            cargo_capacity_m3 REAL,
            engine_mcr_kw REAL,
            service_speed_kn REAL
        )
    """)
    rows = []
    for v in vessels:
        rows.append((
            v.get("id", ""),
            v.get("name", ""),
            str(v.get("imo", "")),
            v.get("flag", ""),
            v.get("type", v.get("propulsion_type", "")),
            v.get("cargo_capacity_m3", 0),
            v.get("engine_mcr_kw", 0),
            v.get("service_speed_kn", 0),
        ))
    conn.executemany(
        "INSERT INTO vessel_registry VALUES (?,?,?,?,?,?,?,?)", rows
    )
    conn.commit()
    print(f"  vessel_registry: {len(rows)} vessels loaded")


def get_alarm_columns_for_table(raw_conn: sqlite3.Connection, table: str) -> list[str]:
    cursor = raw_conn.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cursor.fetchall()]
    return [c for c in cols if c.startswith("alarm_")]


def build_alarm_case(alarm_cols: list[str], prefix: str = "") -> str:
    if not alarm_cols:
        return "0"
    conditions = " + ".join(
        [f"CASE WHEN {prefix}{c} IS NOT NULL AND {prefix}{c} != '' THEN 1 ELSE 0 END" for c in alarm_cols]
    )
    return conditions


def aggregate_hourly(src: sqlite3.Connection, dst: sqlite3.Connection, alarm_cols: list[str]):
    raw_path = str(Path(src.db_path) if hasattr(src, 'db_path') else "")
    dst.execute("DROP TABLE IF EXISTS telemetry_hourly")
    dst.execute("""
        CREATE TABLE telemetry_hourly (
            vessel_id TEXT,
            hour TEXT,
            lat_avg REAL,
            lon_avg REAL,
            sog_avg REAL,
            sog_max REAL,
            wind_speed_avg REAL,
            wind_speed_max REAL,
            wave_height_avg REAL,
            wave_height_max REAL,
            sea_temp_avg REAL,
            air_temp_avg REAL,
            engine_load_avg REAL,
            engine_load_max REAL,
            shaft_power_kw_avg REAL,
            fuel_consumption_total_kg REAL,
            sfoc_avg REAL,
            exhaust_temp_avg REAL,
            bog_rate_avg REAL,
            bog_rate_max REAL,
            cargo_qty_avg REAL,
            draft_avg REAL,
            trim_avg REAL,
            co2_total_mt REAL,
            nox_total_kg REAL,
            sox_total_kg REAL,
            ch4_total_kg REAL,
            distance_total_nm REAL,
            eeoi_avg REAL,
            alarm_count INTEGER
        )
    """)
    dst.commit()

    t0 = time.time()
    total_rows = 0
    # Per-vessel cargo capacity (mt) for fill% and laden-day detection
    capacities_mt = {}
    min_cargos = {}
    for row in dst.execute("SELECT vessel_id, cargo_capacity_m3 FROM vessel_registry"):
        cap_mt = (row[1] or 174000) * 0.45
        capacities_mt[row[0]] = cap_mt
        min_cargos[row[0]] = cap_mt * 0.30  # 30% of capacity in mt for laden detection
    for i in range(1, NUM_VESSELS + 1):
        table = f"telemetry_lng_{i:03d}"
        vessel_id = f"LNG-{i:03d}"
        cap_mt = capacities_mt.get(vessel_id, 78300)
        min_cargo = min_cargos.get(vessel_id, 23500)
        try:
            src.execute(f"SELECT COUNT(*) FROM {table}")
        except sqlite3.OperationalError:
            print(f"  [{i:03d}] {table} not found, skipping")
            continue
        table_alarm_cols = get_alarm_columns_for_table(src, table)
        alarm_expr = build_alarm_case(table_alarm_cols)
        insert_sql = f"""
            INSERT INTO telemetry_hourly
            SELECT
                '{vessel_id}' AS vessel_id,
                substr(replace(datetime(timestamp + {TIMESTAMP_OFFSET}, 'unixepoch'), ' ', 'T'), 1, 13) || ':00:00' AS hour,
                AVG(lat) AS lat_avg,
                AVG(lon) AS lon_avg,
                AVG(sog) AS sog_avg,
                MAX(sog) AS sog_max,
                AVG(wind_speed_kn) AS wind_speed_avg,
                MAX(wind_speed_kn) AS wind_speed_max,
                AVG(wave_height_m) AS wave_height_avg,
                MAX(wave_height_m) AS wave_height_max,
                AVG(sea_temp_c) AS sea_temp_avg,
                AVG(air_temp_c) AS air_temp_avg,
                AVG(engine_load_pct) AS engine_load_avg,
                MAX(engine_load_pct) AS engine_load_max,
                AVG(shaft_power_kw) AS shaft_power_kw_avg,
                (MAX(total_fuel_lng_mt)-MIN(total_fuel_lng_mt)+MAX(total_fuel_mgo_mt)-MIN(total_fuel_mgo_mt))*1000 AS fuel_consumption_total_kg,
                AVG(CASE WHEN sfoc_actual > 50 THEN sfoc_actual END) AS sfoc_avg,
                AVG(exhaust_temp_c) AS exhaust_temp_avg,
                AVG(bog_generation_kg_h) AS bog_rate_avg,
                MAX(bog_generation_kg_h) AS bog_rate_max,
                AVG(cargo_qty_mt) / {cap_mt} * 100 AS cargo_qty_avg,
                AVG((draft_f_m + draft_a_m) / 2.0) AS draft_avg,
                AVG(trim_m) AS trim_avg,
                MAX(total_co2_mt)-MIN(total_co2_mt) AS co2_total_mt,
                (MAX(total_nox_mt)-MIN(total_nox_mt))*1000 AS nox_total_kg,
                (MAX(total_sox_mt)-MIN(total_sox_mt))*1000 AS sox_total_kg,
                (MAX(total_ch4_mt)-MIN(total_ch4_mt))*1000 AS ch4_total_kg,
                MAX(distance_sailed_nm)-MIN(distance_sailed_nm) AS distance_total_nm,
                CASE WHEN MAX(distance_sailed_nm)-MIN(distance_sailed_nm) > 10
                          AND AVG(cargo_qty_mt) > {min_cargo}
                     THEN (MAX(total_co2_mt)-MIN(total_co2_mt))*1e6
                          / (AVG(cargo_qty_mt)*(MAX(distance_sailed_nm)-MIN(distance_sailed_nm)))
                     ELSE NULL END AS eeoi_avg,
                {alarm_expr} AS alarm_count
            FROM raw.{table}
            GROUP BY substr(replace(datetime(timestamp + {TIMESTAMP_OFFSET}, 'unixepoch'), ' ', 'T'), 1, 13) || ':00:00'
        """
        dst.execute(insert_sql)
        inserted = dst.execute("SELECT changes()").fetchone()[0]
        total_rows += inserted
        elapsed = time.time() - t0
        rate = total_rows / elapsed if elapsed > 0 else 0
        print(f"  [{i:03d}] {vessel_id}: {inserted:,} hourly rows  (total {total_rows:,} @ {rate:,.0f} rows/s)")

    dst.commit()
    print(f"  telemetry_hourly: {total_rows:,} rows total in {time.time()-t0:.1f}s")


def aggregate_daily(src: sqlite3.Connection, dst: sqlite3.Connection, alarm_cols: list[str]):
    dst.execute("DROP TABLE IF EXISTS telemetry_daily")
    dst.execute("""
        CREATE TABLE telemetry_daily (
            vessel_id TEXT,
            day TEXT,
            lat_avg REAL,
            lon_avg REAL,
            sog_avg REAL,
            sog_max REAL,
            wind_speed_avg REAL,
            wind_speed_max REAL,
            wave_height_avg REAL,
            wave_height_max REAL,
            sea_temp_avg REAL,
            air_temp_avg REAL,
            engine_load_avg REAL,
            engine_load_max REAL,
            shaft_power_kw_avg REAL,
            fuel_consumption_total_kg REAL,
            sfoc_avg REAL,
            exhaust_temp_avg REAL,
            bog_rate_avg REAL,
            bog_rate_max REAL,
            cargo_qty_avg REAL,
            draft_avg REAL,
            trim_avg REAL,
            co2_total_mt REAL,
            nox_total_kg REAL,
            sox_total_kg REAL,
            ch4_total_kg REAL,
            distance_total_nm REAL,
            eeoi_avg REAL,
            alarm_count INTEGER
        )
    """)
    dst.commit()

    t0 = time.time()
    total_rows = 0
    cap_mt_daily = {}
    min_cargos_daily = {}
    for row in dst.execute("SELECT vessel_id, cargo_capacity_m3 FROM vessel_registry"):
        cap_mt = (row[1] or 174000) * 0.45
        cap_mt_daily[row[0]] = cap_mt
        min_cargos_daily[row[0]] = cap_mt * 0.30
    for i in range(1, NUM_VESSELS + 1):
        table = f"telemetry_lng_{i:03d}"
        vessel_id = f"LNG-{i:03d}"
        cap_mt = cap_mt_daily.get(vessel_id, 78300)
        min_cargo = min_cargos_daily.get(vessel_id, 23500)
        try:
            src.execute(f"SELECT COUNT(*) FROM {table}")
        except sqlite3.OperationalError:
            continue
        table_alarm_cols = get_alarm_columns_for_table(src, table)
        alarm_expr = build_alarm_case(table_alarm_cols)
        insert_sql = f"""
            INSERT INTO telemetry_daily
            SELECT
                '{vessel_id}' AS vessel_id,
                datetime(timestamp + {TIMESTAMP_OFFSET}, 'unixepoch', 'start of day') AS day,
                AVG(lat) AS lat_avg,
                AVG(lon) AS lon_avg,
                AVG(sog) AS sog_avg,
                MAX(sog) AS sog_max,
                AVG(wind_speed_kn) AS wind_speed_avg,
                MAX(wind_speed_kn) AS wind_speed_max,
                AVG(wave_height_m) AS wave_height_avg,
                MAX(wave_height_m) AS wave_height_max,
                AVG(sea_temp_c) AS sea_temp_avg,
                AVG(air_temp_c) AS air_temp_avg,
                AVG(engine_load_pct) AS engine_load_avg,
                MAX(engine_load_pct) AS engine_load_max,
                AVG(shaft_power_kw) AS shaft_power_kw_avg,
                (MAX(total_fuel_lng_mt)-MIN(total_fuel_lng_mt)+MAX(total_fuel_mgo_mt)-MIN(total_fuel_mgo_mt))*1000 AS fuel_consumption_total_kg,
                AVG(CASE WHEN sfoc_actual > 50 THEN sfoc_actual END) AS sfoc_avg,
                AVG(exhaust_temp_c) AS exhaust_temp_avg,
                AVG(bog_generation_kg_h) AS bog_rate_avg,
                MAX(bog_generation_kg_h) AS bog_rate_max,
                AVG(cargo_qty_mt) / {cap_mt} * 100 AS cargo_qty_avg,
                AVG((draft_f_m + draft_a_m) / 2.0) AS draft_avg,
                AVG(trim_m) AS trim_avg,
                MAX(total_co2_mt)-MIN(total_co2_mt) AS co2_total_mt,
                (MAX(total_nox_mt)-MIN(total_nox_mt))*1000 AS nox_total_kg,
                (MAX(total_sox_mt)-MIN(total_sox_mt))*1000 AS sox_total_kg,
                (MAX(total_ch4_mt)-MIN(total_ch4_mt))*1000 AS ch4_total_kg,
                MAX(distance_sailed_nm)-MIN(distance_sailed_nm) AS distance_total_nm,
                CASE WHEN MAX(distance_sailed_nm)-MIN(distance_sailed_nm) > 50
                          AND AVG(cargo_qty_mt) > {min_cargo}
                     THEN (MAX(total_co2_mt)-MIN(total_co2_mt))*1e6
                          / (AVG(cargo_qty_mt)*(MAX(distance_sailed_nm)-MIN(distance_sailed_nm)))
                     ELSE NULL END AS eeoi_avg,
                {alarm_expr} AS alarm_count
            FROM raw.{table}
            GROUP BY datetime(timestamp + {TIMESTAMP_OFFSET}, 'unixepoch', 'start of day')
        """
        dst.execute(insert_sql)
        inserted = dst.execute("SELECT changes()").fetchone()[0]
        total_rows += inserted
        elapsed = time.time() - t0
        rate = total_rows / elapsed if elapsed > 0 else 0
        print(f"  [{i:03d}] {vessel_id}: {inserted:,} daily rows  (total {total_rows:,} @ {rate:,.0f} rows/s)")

    dst.commit()
    print(f"  telemetry_daily: {total_rows:,} rows total in {time.time()-t0:.1f}s")


def aggregate_fleet_daily(dst: sqlite3.Connection):
    dst.execute("DROP TABLE IF EXISTS fleet_daily_summary")
    dst.execute("""
        CREATE TABLE fleet_daily_summary (
            day TEXT,
            total_vessels INTEGER,
            avg_speed REAL,
            total_fuel_kg REAL,
            total_co2_mt REAL,
            total_distance_nm REAL,
            avg_bog_rate REAL,
            avg_engine_load REAL,
            avg_sfoc REAL,
            avg_eeoi REAL
        )
    """)

    insert_sql = """
        INSERT INTO fleet_daily_summary
        SELECT
            day,
            COUNT(DISTINCT vessel_id) AS total_vessels,
            AVG(sog_avg) AS avg_speed,
            SUM(fuel_consumption_total_kg) AS total_fuel_kg,
            SUM(co2_total_mt) AS total_co2_mt,
            SUM(distance_total_nm) AS total_distance_nm,
            AVG(bog_rate_avg) AS avg_bog_rate,
            AVG(engine_load_avg) AS avg_engine_load,
            AVG(sfoc_avg) AS avg_sfoc,
            AVG(eeoi_avg) AS avg_eeoi
        FROM telemetry_daily
        GROUP BY day
        ORDER BY day
    """

    dst.execute(insert_sql)
    dst.commit()
    count = dst.execute("SELECT COUNT(*) FROM fleet_daily_summary").fetchone()[0]
    print(f"  fleet_daily_summary: {count} rows")


def create_indexes(dst: sqlite3.Connection):
    print("Creating indexes...")
    t0 = time.time()
    dst.execute("CREATE INDEX IF NOT EXISTS idx_hourly_vessel_hour ON telemetry_hourly(vessel_id, hour)")
    dst.execute("CREATE INDEX IF NOT EXISTS idx_daily_vessel_day ON telemetry_daily(vessel_id, day)")
    dst.execute("CREATE INDEX IF NOT EXISTS idx_fleet_daily_day ON fleet_daily_summary(day)")
    dst.commit()
    print(f"  Indexes created in {time.time()-t0:.1f}s")


def print_summary(dst: sqlite3.Connection):
    print("\n=== Analytics DB Summary ===")
    tables = ["vessel_registry", "telemetry_hourly", "telemetry_daily", "fleet_daily_summary"]
    for t in tables:
        try:
            count = dst.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"  {t:30s} {count:>12,} rows")
        except Exception:
            print(f"  {t:30s} (missing)")

    print("\nDate range (hourly):")
    row = dst.execute(
        "SELECT MIN(hour), MAX(hour) FROM telemetry_hourly"
    ).fetchone()
    if row[0]:
        print(f"  {row[0]}  to  {row[1]}")

    print("\nFleet totals (all time):")
    row = dst.execute("""
        SELECT
            SUM(fuel_consumption_total_kg),
            SUM(co2_total_mt),
            SUM(distance_total_nm)
        FROM telemetry_daily
    """).fetchone()
    if row[0]:
        print(f"  Total fuel:  {row[0]:>15,.0f} kg")
        print(f"  Total CO2:   {row[1]:>15,.1f} mt")
        print(f"  Total dist:  {row[2]:>15,.0f} nm")


def main():
    script_dir = Path(__file__).resolve().parent
    raw_db = script_dir / RAW_DB
    analytics_db = script_dir / ANALYTICS_DB
    vessel_config = script_dir / VESSEL_CONFIG

    if not raw_db.exists():
        print(f"ERROR: Raw database not found at {raw_db}")
        print("Run the data generator first.")
        sys.exit(1)

    if not vessel_config.exists():
        print(f"ERROR: Vessel config not found at {vessel_config}")
        sys.exit(1)

    analytics_db.parent.mkdir(parents=True, exist_ok=True)

    print(f"Raw DB:     {raw_db}  ({raw_db.stat().st_size / 1e6:.0f} MB)")
    print(f"Analytics:  {analytics_db}")

    raw_conn = sqlite3.connect(str(raw_db))
    raw_conn.execute("PRAGMA journal_mode=WAL")
    raw_conn.execute("PRAGMA cache_size=-200000")

    dst_conn = sqlite3.connect(str(analytics_db))
    dst_conn.execute("PRAGMA journal_mode=WAL")
    dst_conn.execute("PRAGMA synchronous=NORMAL")
    dst_conn.execute("PRAGMA cache_size=-200000")

    t_start = time.time()

    print("\n[1/7] Loading vessel configs...")
    vessels = load_vessel_configs(str(vessel_config))
    create_vessel_registry(dst_conn, vessels)

    print("\n[2/7] Attaching raw database...")
    dst_conn.execute(f"ATTACH DATABASE '{raw_db}' AS raw")
    print(f"  Attached: {raw_db}")

    print("\n[3/7] Detecting alarm columns...")
    alarm_cols = get_alarm_columns_for_table(raw_conn, "telemetry_lng_001")
    if alarm_cols:
        print(f"  Found {len(alarm_cols)} alarm columns: {', '.join(alarm_cols)}")
    else:
        print("  No alarm columns detected, alarm_count will be 0")

    print("\n[4/7] Aggregating hourly telemetry...")
    aggregate_hourly(raw_conn, dst_conn, alarm_cols)

    print("\n[5/7] Aggregating daily telemetry...")
    aggregate_daily(raw_conn, dst_conn, alarm_cols)

    print("\n[6/7] Building fleet daily summary...")
    aggregate_fleet_daily(dst_conn)

    print("\n[7/7] Creating indexes...")
    create_indexes(dst_conn)

    print_summary(dst_conn)

    raw_conn.close()
    dst_conn.close()

    total_time = time.time() - t_start
    final_size = analytics_db.stat().st_size / 1e6
    print(f"\nDone in {total_time:.1f}s. Analytics DB: {final_size:.0f} MB")


if __name__ == "__main__":
    main()

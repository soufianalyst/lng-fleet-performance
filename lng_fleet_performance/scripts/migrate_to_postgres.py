#!/usr/bin/env python3
"""Migrate analytics data from SQLite to PostgreSQL.

Usage:
    DATABASE_URL="postgresql://user:pass@host/dbname" python scripts/migrate_to_postgres.py

Reads from: ../lng-data-generator/output/lng_fleet_analytics.db (SQLite)
Writes to: PostgreSQL (DATABASE_URL env var)
"""
import os
import sys
import sqlite3
import psycopg2
import psycopg2.extras
import time


def create_tables(pg_conn):
    """Create analytics tables in PostgreSQL (matching SQLite schema)."""
    cur = pg_conn.cursor()

    cur.execute("DROP TABLE IF EXISTS fleet_daily_summary CASCADE")
    cur.execute("DROP TABLE IF EXISTS telemetry_daily CASCADE")
    cur.execute("DROP TABLE IF EXISTS telemetry_hourly CASCADE")
    cur.execute("DROP TABLE IF EXISTS vessel_registry CASCADE")

    cur.execute("""
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

    cur.execute("""
        CREATE TABLE telemetry_hourly (
            vessel_id TEXT,
            hour TEXT,
            lat_avg REAL, lon_avg REAL,
            sog_avg REAL, sog_max REAL,
            wind_speed_avg REAL, wind_speed_max REAL,
            wave_height_avg REAL, wave_height_max REAL,
            sea_temp_avg REAL, air_temp_avg REAL,
            engine_load_avg REAL, engine_load_max REAL,
            shaft_power_kw_avg REAL,
            fuel_consumption_total_kg REAL,
            sfoc_avg REAL, exhaust_temp_avg REAL,
            bog_rate_avg REAL, bog_rate_max REAL,
            cargo_qty_avg REAL,
            draft_avg REAL, trim_avg REAL,
            co2_total_mt REAL,
            nox_total_kg REAL, sox_total_kg REAL, ch4_total_kg REAL,
            distance_total_nm REAL,
            eeoi_avg REAL,
            alarm_count INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE telemetry_daily (
            vessel_id TEXT,
            day TEXT,
            lat_avg REAL, lon_avg REAL,
            sog_avg REAL, sog_max REAL,
            wind_speed_avg REAL, wind_speed_max REAL,
            wave_height_avg REAL, wave_height_max REAL,
            sea_temp_avg REAL, air_temp_avg REAL,
            engine_load_avg REAL, engine_load_max REAL,
            shaft_power_kw_avg REAL,
            fuel_consumption_total_kg REAL,
            sfoc_avg REAL, exhaust_temp_avg REAL,
            bog_rate_avg REAL, bog_rate_max REAL,
            cargo_qty_avg REAL,
            draft_avg REAL, trim_avg REAL,
            co2_total_mt REAL,
            nox_total_kg REAL, sox_total_kg REAL, ch4_total_kg REAL,
            distance_total_nm REAL,
            eeoi_avg REAL,
            alarm_count INTEGER
        )
    """)

    cur.execute("""
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

    pg_conn.commit()
    print("  Tables created in PostgreSQL")


def migrate_table(sqlite_path, pg_conn, table_name, batch_size=5000):
    """Migrate a single table from SQLite to PostgreSQL."""
    src = sqlite3.connect(sqlite_path)
    src.row_factory = sqlite3.Row
    cur_src = src.cursor()

    cur_src.execute(f"SELECT COUNT(*) FROM {table_name}")
    total = cur_src.fetchone()[0]
    print(f"  {table_name}: {total:,} rows to migrate")

    cur_src.execute(f"SELECT * FROM {table_name}")
    pg_cur = pg_conn.cursor()

    migrated = 0
    t0 = time.time()

    while True:
        rows = cur_src.fetchmany(batch_size)
        if not rows:
            break

        columns = rows[0].keys()
        col_list = ", ".join(columns)
        placeholders = ", ".join(["%s"] * len(columns))
        insert_sql = f"INSERT INTO {table_name} ({col_list}) VALUES ({placeholders})"

        data = []
        for row in rows:
            data.append(tuple(row[c] for c in columns))

        psycopg2.extras.execute_batch(pg_cur, insert_sql, data, page_size=batch_size)
        migrated += len(rows)
        elapsed = time.time() - t0
        rate = migrated / elapsed if elapsed > 0 else 0
        print(f"\r  {table_name}: {migrated:,}/{total:,} ({100*migrated/total:.0f}%) @ {rate:,.0f} rows/s", end="", flush=True)

    pg_conn.commit()
    src.close()
    elapsed = time.time() - t0
    print(f"\n  {table_name}: done in {elapsed:.1f}s")


def create_indexes(pg_conn):
    """Create indexes for query performance."""
    cur = pg_conn.cursor()
    print("  Creating indexes...")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_hourly_vessel_hour ON telemetry_hourly(vessel_id, hour)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_daily_vessel_day ON telemetry_daily(vessel_id, day)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fleet_daily_day ON fleet_daily_summary(day)")
    pg_conn.commit()
    print("  Indexes created")


def main():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        print("Usage: DATABASE_URL='postgresql://...' python scripts/migrate_to_postgres.py")
        sys.exit(1)

    sqlite_path = os.path.join(os.path.dirname(__file__), "..", "..", "lng-data-generator", "output", "lng_fleet_analytics.db")
    if not os.path.exists(sqlite_path):
        print(f"ERROR: SQLite analytics DB not found at {sqlite_path}")
        sys.exit(1)

    print(f"SQLite:  {sqlite_path} ({os.path.getsize(sqlite_path)/1e6:.0f} MB)")
    print(f"PostgreSQL: {database_url[:50]}...")

    pg_conn = psycopg2.connect(database_url)
    pg_conn.autocommit = True

    t0 = time.time()
    print("\n[1/5] Creating tables...")
    create_tables(pg_conn)

    print("\n[2/5] Migrating vessel_registry...")
    migrate_table(sqlite_path, pg_conn, "vessel_registry")

    print("\n[3/5] Migrating telemetry_hourly...")
    migrate_table(sqlite_path, pg_conn, "telemetry_hourly")

    print("\n[4/5] Migrating telemetry_daily...")
    migrate_table(sqlite_path, pg_conn, "telemetry_daily")

    print("\n[5/5] Migrating fleet_daily_summary...")
    migrate_table(sqlite_path, pg_conn, "fleet_daily_summary")

    create_indexes(pg_conn)

    pg_conn.close()
    elapsed = time.time() - t0
    print(f"\nMigration complete in {elapsed:.1f}s")


if __name__ == "__main__":
    main()

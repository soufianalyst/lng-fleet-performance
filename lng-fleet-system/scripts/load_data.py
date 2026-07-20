#!/usr/bin/env python3
"""Load synthetic CSV data into PostgreSQL with column mapping for vessels."""
import csv
import os

DB_URL = os.environ.get("DB_URL", "postgresql://lngfleet:lngfleet_dev@localhost:5434/lngfleet")

try:
    import psycopg2
except ImportError:
    os.system("pip install psycopg2-binary -q")
    import psycopg2

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "synthetic-data-generator", "output")

COLUMN_MAPS = {
    "vessels": lambda row: {
        "id": row["id"],
        "imo_number": int(row["imo"]) if row["imo"] else None,
        "name": row["name"],
        "flag": row["flag"],
        "vessel_type": "LNG_CARRIER",
        "cargo_capacity_m3": float(row["capacity_m3"]) if row["capacity_m3"] else None,
        "build_year": int(row["build_year"]) if row["build_year"] else None,
        "engine_type": row["engine_type"],
        "lng_tank_type": row["tank_type"],
        "design_draft_m": float(row["design_draft_m"]) if row["design_draft_m"] else None,
        "design_speed_kn": float(row["design_speed_kn"]) if row["design_speed_kn"] else None,
    },
    "cii_records": lambda row: {
        "id": row["id"],
        "vessel_id": row["vessel_id"],
        "year": int(row["year"]),
        "month": int(row["month"]),
        "attained_cii": float(row["cii_calculated"]) if row["cii_calculated"] else 0,
        "required_cii": float(row["cii_required_c"]) if row["cii_required_c"] else 0,
        "rating": row["cii_rating"],
        "distance_nm": 0,
        "fuel_consumption_tonne": float(row["co2_total_t"]) * 0.3 if row["co2_total_t"] else 0,
        "co2_emissions_tonne": float(row["co2_total_t"]) if row["co2_total_t"] else 0,
        "capacity_cbm": 170000,
        "forecast": False,
    },
}

TABLES = ["vessels", "voyages", "charter_parties", "charter_verifications",
          "telemetry", "bog_records", "cii_records", "eca_events",
          "maintenance_predictions"]

def load_csv(conn, table, csv_file):
    with open(csv_file) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if not rows:
        return 0

    if table in COLUMN_MAPS:
        mapper = COLUMN_MAPS[table]
        col_map = mapper(rows[0]) if callable(mapper) else mapper
        cols = ", ".join(col_map.keys())
        placeholders = ", ".join(["%s"] * len(col_map))
        insert_sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
        
        cur = conn.cursor()
        count = 0
        errors = 0
        for row in rows:
            try:
                mapped = mapper(row)
                values = list(mapped.values())
                values = [v if v != '' else None for v in values]
                cur.execute(insert_sql, values)
                count += 1
            except Exception as e:
                errors += 1
                if errors <= 2:
                    print(f"    Error: {e}")
            if count % 5000 == 0 and count > 0:
                conn.commit()
        conn.commit()
        cur.close()
        if errors:
            print(f" ({errors} errors)", end="")
        return count

    raw_cols = list(rows[0].keys())
    cols = ", ".join(raw_cols)
    placeholders = ", ".join(["%s"] * len(raw_cols))
    insert_sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
    
    cur = conn.cursor()
    count = 0
    errors = 0
    for row in rows:
        values = list(row.values())
        values = [v if v != '' else None for v in values]
        try:
            cur.execute(insert_sql, values)
            count += 1
        except Exception as e:
            errors += 1
            if errors <= 2:
                print(f"    Error: {e}")
        if count % 5000 == 0 and count > 0:
            conn.commit()
    conn.commit()
    cur.close()
    if errors:
        print(f" ({errors} errors)", end="")
    return count

def main():
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    
    for table in TABLES:
        csv_file = os.path.join(DATA_DIR, f"{table}.csv")
        if not os.path.exists(csv_file):
            continue
        print(f"Loading {table}...", end=" ", flush=True)
        count = load_csv(conn, table, csv_file)
        print(f" {count} rows")
    
    conn.close()
    print("\nDone!")

if __name__ == "__main__":
    main()

import sqlite3
import os
from typing import List, Dict, Any


class SQLiteWriter:
    def __init__(self, output_dir: str, db_name: str = "lng_telemetry.db"):
        self.db_path = os.path.join(output_dir, "sqlite", db_name)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA cache_size=-64000")
        self._tables_created = set()
        self._table_columns = {}
        self._counts = {}

    def write_batch(self, vessel_id: str, records: List[Dict[str, Any]]):
        if not records:
            return
        table = f"telemetry_{vessel_id.replace('-', '_').lower()}"
        if table not in self._tables_created:
            self._create_table(table, records[0])
            self._tables_created.add(table)
            self._table_columns[table] = set(records[0].keys())
        existing = self._table_columns[table]
        for r in records:
            for k in r:
                if k not in existing:
                    self._add_column(table, k, type(r[k]))
                    existing.add(k)
        columns = list(existing)
        placeholders = ",".join(["?"] * len(columns))
        col_names = ",".join(columns)
        rows = [tuple(r.get(c, "") for c in columns) for r in records]
        self.conn.executemany(f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})", rows)
        self.conn.commit()
        self._counts[vessel_id] = self._counts.get(vessel_id, 0) + len(records)

    def _add_column(self, table_name: str, col_name: str, col_type):
        type_str = "INTEGER" if col_type == bool else "INTEGER" if col_type == int else "REAL" if col_type == float else "TEXT"
        try:
            self.conn.execute(f'ALTER TABLE {table_name} ADD COLUMN "{col_name}" {type_str}')
            self.conn.commit()
        except Exception:
            pass

    def _create_table(self, table_name: str, sample: Dict[str, Any]):
        col_defs = []
        for col, val in sample.items():
            if isinstance(val, bool):
                col_defs.append(f'"{col}" INTEGER')
            elif isinstance(val, int):
                col_defs.append(f'"{col}" INTEGER')
            elif isinstance(val, float):
                col_defs.append(f'"{col}" REAL')
            else:
                col_defs.append(f'"{col}" TEXT')
        sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(col_defs)})"
        self.conn.execute(sql)
        self.conn.commit()

    def finalize(self):
        self.conn.close()

    def get_counts(self) -> Dict[str, int]:
        return dict(self._counts)

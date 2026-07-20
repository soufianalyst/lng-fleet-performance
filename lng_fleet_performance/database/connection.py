import sqlite3
import os
import hashlib
import json
from datetime import datetime
from contextlib import contextmanager
from typing import Optional


class DatabaseManager:
    def __init__(self, db_path: str = "lng_fleet.db"):
        self.db_path = db_path
        self._initialize()

    def _initialize(self):
        with self.get_connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA busy_timeout=5000")

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor

    def fetchone(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        with self.get_connection() as conn:
            return conn.execute(query, params).fetchone()

    def fetchall(self, query: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self.get_connection() as conn:
            return conn.execute(query, params).fetchall()

    def executemany(self, query: str, params_list: list[tuple]):
        with self.get_connection() as conn:
            conn.executemany(query, params_list)

    def insert_returning_id(self, query: str, params: tuple = ()) -> int:
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.lastrowid

    def audit_hash(self, data: dict) -> str:
        canonical = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def log_audit(self, table: str, record_id: int, action: str, data: dict):
        h = self.audit_hash(data)
        self.execute(
            """INSERT INTO audit_log (table_name, record_id, action, data_hash, timestamp_utc)
               VALUES (?, ?, ?, ?, ?)""",
            (table, record_id, action, h, datetime.utcnow().isoformat()),
        )

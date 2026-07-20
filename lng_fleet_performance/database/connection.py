import os
import re
import hashlib
import json
from datetime import datetime
from contextlib import contextmanager
from typing import Optional

DATABASE_URL = os.environ.get("DATABASE_URL", "")
USING_POSTGRES = bool(DATABASE_URL)


class DatabaseManager:
    def __init__(self, db_path: str = "lng_fleet.db"):
        self.db_path = db_path
        self._pg_conn = None
        if USING_POSTGRES:
            self._init_postgres()
        else:
            self._init_sqlite()

    def _init_postgres(self):
        import psycopg2
        self._pg_conn = psycopg2.connect(DATABASE_URL)
        self._pg_conn.autocommit = True

    def _init_sqlite(self):
        import sqlite3
        import time
        for attempt in range(5):
            try:
                conn = sqlite3.connect(self.db_path, timeout=15)
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA foreign_keys=ON")
                conn.execute("PRAGMA busy_timeout=10000")
                conn.close()
                return
            except Exception:
                if attempt < 4:
                    time.sleep(0.5 * (attempt + 1))
                else:
                    raise

    def _pg_convert(self, query: str) -> str:
        """Convert SQLite SQL to PostgreSQL."""
        q = query
        q = q.replace("?", "%s")
        q = re.sub(r'\bINSERT\s+OR\s+IGNORE\b', 'INSERT', q, flags=re.IGNORECASE)
        q = re.sub(r'\bINSERT\s+OR\s+REPLACE\b', 'INSERT', q, flags=re.IGNORECASE)
        q = re.sub(r"strftime\('%Y',\s*(\w+(?:\.\w+)?)\)", r"EXTRACT(YEAR FROM \1::timestamp)", q, flags=re.IGNORECASE)
        q = re.sub(r"strftime\('%m',\s*(\w+(?:\.\w+)?)\)", r"EXTRACT(MONTH FROM \1::timestamp)", q, flags=re.IGNORECASE)
        q = re.sub(r"strftime\('%Y-%m',\s*(\w+(?:\.\w+)?)\)", r"TO_CHAR(\1::timestamp, 'YYYY-MM')", q, flags=re.IGNORECASE)
        q = re.sub(r"date\('now'\)", "CURRENT_DATE", q, flags=re.IGNORECASE)
        q = re.sub(r"date\('now',\s*'\+(\d+)\s+days?'\)", r"(CURRENT_DATE + INTERVAL '\1 days')", q, flags=re.IGNORECASE)
        q = re.sub(r"datetime\('now'\)", "(NOW() AT TIME ZONE 'UTC')::text", q, flags=re.IGNORECASE)
        if "INSERT" in q.upper() and "ON CONFLICT" not in q.upper():
            tbl_match = re.search(r'INSERT\s+INTO\s+(\w+)', q, re.IGNORECASE)
            if tbl_match:
                q = q.rstrip().rstrip(';') + " ON CONFLICT DO NOTHING"
        return q

    @contextmanager
    def get_connection(self):
        if USING_POSTGRES:
            yield self._pg_conn
        else:
            import sqlite3
            conn = sqlite3.connect(self.db_path, timeout=15)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA busy_timeout=10000")
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def execute(self, query: str, params: tuple = ()):
        if USING_POSTGRES:
            cur = self._pg_conn.cursor()
            converted = self._pg_convert(query)
            cur.execute(converted, params)
            return _PgCursorWrapper(cur, converted, self._pg_conn)
        else:
            with self.get_connection() as conn:
                return conn.execute(query, params)

    def fetchone(self, query: str, params: tuple = ()):
        if USING_POSTGRES:
            import psycopg2.extras
            cur = self._pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(self._pg_convert(query), params)
            return cur.fetchone()
        else:
            with self.get_connection() as conn:
                return conn.execute(query, params).fetchone()

    def fetchall(self, query: str, params: tuple = ()):
        if USING_POSTGRES:
            import psycopg2.extras
            cur = self._pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(self._pg_convert(query), params)
            return cur.fetchall()
        else:
            with self.get_connection() as conn:
                return conn.execute(query, params).fetchall()

    def executemany(self, query: str, params_list: list[tuple]):
        if USING_POSTGRES:
            import psycopg2.extras
            cur = self._pg_conn.cursor()
            psycopg2.extras.execute_batch(cur, self._pg_convert(query), params_list)
        else:
            with self.get_connection() as conn:
                conn.executemany(query, params_list)

    def insert_returning_id(self, query: str, params: tuple = ()) -> int:
        if USING_POSTGRES:
            cur = self._pg_conn.cursor()
            converted = self._pg_convert(query)
            tbl = re.search(r'INSERT\s+INTO\s+(\w+)', converted, re.IGNORECASE)
            if tbl:
                cur.execute(converted + f" RETURNING {tbl.group(1)}_id", params)
                row = cur.fetchone()
                return row[0] if row else 0
            cur.execute(converted, params)
            return 0
        else:
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


class _PgCursorWrapper:
    """Wraps psycopg2 cursor to add .lastrowid for INSERT statements."""

    def __init__(self, cursor, query, conn):
        self._cursor = cursor
        self.lastrowid = 0
        if query.strip().upper().startswith("INSERT"):
            tbl = re.search(r'INSERT\s+INTO\s+(\w+)', query, re.IGNORECASE)
            if tbl:
                tbl_name = tbl.group(1)
                try:
                    cur2 = conn.cursor()
                    cur2.execute(f"SELECT currval(pg_get_serial_sequence('{tbl_name}', '{tbl_name}_id'))")
                    self.lastrowid = cur2.fetchone()[0]
                except Exception:
                    try:
                        cur2 = conn.cursor()
                        cur2.execute("SELECT lastval()")
                        self.lastrowid = cur2.fetchone()[0]
                    except Exception:
                        self.lastrowid = 0

    def __getattr__(self, name):
        return getattr(self._cursor, name)

import os
import hashlib
import json
from datetime import datetime
from contextlib import contextmanager
from typing import Optional

DATABASE_URL = os.environ.get("DATABASE_URL", "")
USING_POSTGRES = bool(DATABASE_URL)


class DatabaseManager:
    """Dual SQLite/PostgreSQL database manager.

    When DATABASE_URL env var is set, connects to PostgreSQL.
    Otherwise uses local SQLite file.
    """

    def __init__(self, db_path: str = "lng_fleet.db"):
        self.db_path = db_path
        self._pg_conn = None
        if USING_POSTGRES:
            self._init_postgres()
        else:
            self._init_sqlite()

    def _init_postgres(self):
        import psycopg2
        import psycopg2.extras
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

    def _convert_query(self, query: str) -> str:
        """Convert SQLite syntax to PostgreSQL syntax."""
        if not USING_POSTGRES:
            return query
        q = query.replace("?", "%s")
        import re
        q = re.sub(r'\bINSERT\s+OR\s+IGNORE\b', 'INSERT', q, flags=re.IGNORECASE)
        q = re.sub(r'\bINSERT\s+OR\s+REPLACE\b', 'INSERT', q, flags=re.IGNORECASE)
        # Convert strftime('%Y', col) -> EXTRACT(YEAR FROM col::timestamp)
        q = re.sub(r"strftime\('%Y',\s*(\w+(?:\.\w+)?)\)", r"EXTRACT(YEAR FROM \1::timestamp)", q, flags=re.IGNORECASE)
        q = re.sub(r"strftime\('%m',\s*(\w+(?:\.\w+)?)\)", r"EXTRACT(MONTH FROM \1::timestamp)", q, flags=re.IGNORECASE)
        q = re.sub(r"strftime\('%Y-%m',\s*(\w+(?:\.\w+)?)\)", r"TO_CHAR(\1::timestamp, 'YYYY-MM')", q, flags=re.IGNORECASE)
        # Convert date('now') -> CURRENT_DATE
        q = re.sub(r"date\('now'\)", "CURRENT_DATE", q, flags=re.IGNORECASE)
        q = re.sub(r"date\('now',\s*'\+(\d+)\s+days?'\)", r"(CURRENT_DATE + INTERVAL '\1 days')", q, flags=re.IGNORECASE)
        # Convert datetime('now') -> (NOW() AT TIME ZONE 'UTC')::text
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
            import psycopg2.extras
            import re
            cur = self._pg_conn.cursor()
            cur.execute(self._convert_query(query), params)
            return _PgCursor(cur, query)
        else:
            import sqlite3
            with self.get_connection() as conn:
                cursor = conn.execute(query, params)
                return cursor

    def fetchone(self, query: str, params: tuple = ()):
        if USING_POSTGRES:
            import psycopg2.extras
            cur = self._pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(self._convert_query(query), params)
            row = cur.fetchone()
            if row is None:
                return None
            return _PgRow(row)
        else:
            import sqlite3
            with self.get_connection() as conn:
                return conn.execute(query, params).fetchone()

    def fetchall(self, query: str, params: tuple = ()):
        if USING_POSTGRES:
            import psycopg2.extras
            cur = self._pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(self._convert_query(query), params)
            return [_PgRow(row) for row in cur.fetchall()]
        else:
            import sqlite3
            with self.get_connection() as conn:
                return conn.execute(query, params).fetchall()

    def executemany(self, query: str, params_list: list[tuple]):
        if USING_POSTGRES:
            import psycopg2.extras
            cur = self._pg_conn.cursor()
            psycopg2.extras.execute_batch(cur, self._convert_query(query), params_list)
        else:
            import sqlite3
            with self.get_connection() as conn:
                conn.executemany(query, params_list)

    def insert_returning_id(self, query: str, params: tuple = ()) -> int:
        if USING_POSTGRES:
            cur = self._pg_conn.cursor()
            cur.execute(self._convert_query(query) + " RETURNING *", params)
            return cur.lastrowid or 0
        else:
            import sqlite3
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


class _PgCursor:
    """Wraps psycopg2 cursor to provide .lastrowid (via RETURNING or currval)."""

    def __init__(self, cursor, original_query):
        self._cursor = cursor
        self._lastrowid = 0
        import re
        if original_query.strip().upper().startswith("INSERT"):
            tbl = re.search(r'INSERT\s+INTO\s+(\w+)', original_query, re.IGNORECASE)
            if tbl:
                tbl_name = tbl.group(1)
                try:
                    cur2 = self._cursor.connection.cursor()
                    cur2.execute(f"SELECT currval(pg_get_serial_sequence('{tbl_name}', '{tbl_name}_id'))")
                    self._lastrowid = cur2.fetchone()[0]
                except Exception:
                    try:
                        cur2 = self._cursor.connection.cursor()
                        cur2.execute(f"SELECT lastval()")
                        self._lastrowid = cur2.fetchone()[0]
                    except Exception:
                        self._lastrowid = 0

    @property
    def lastrowid(self):
        return self._lastrowid

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class _PgRow:
    """Wraps psycopg2 RealDictRow to behave like sqlite3.Row."""

    def __init__(self, row):
        self._row = row

    def __getitem__(self, key):
        return self._row[key]

    def __contains__(self, key):
        return key in self._row

    def get(self, key, default=None):
        return self._row.get(key, default)

    def keys(self):
        return self._row.keys()

    def __iter__(self):
        return iter(self._row.keys())

    def __repr__(self):
        return repr(self._row)

    def __len__(self):
        return len(self._row)

"""Centralized analytics DB connection — supports both SQLite (local) and PostgreSQL (Render).

When DATABASE_URL env var is set, connects to PostgreSQL.
Otherwise falls back to local SQLite file.

Usage:
    from utils.analytics_db import get_analytics_connection, get_analytics_db
"""
import os
import re
import sqlite3
import psycopg2
import psycopg2.extras

_ANALYTICS_CONN = None


def translate_sql_for_pg(query):
    """Translate SQLite-specific SQL functions to PostgreSQL equivalents."""
    # strftime('%Y-%m', expr) → TO_CHAR(expr::date, 'YYYY-MM')
    query = re.sub(r"strftime\('%Y-%m',\s*([^)]+)\)", r"TO_CHAR(\1::date, 'YYYY-MM')", query)
    # strftime('%Y', expr) → TO_CHAR(expr::date, 'YYYY')
    query = re.sub(r"strftime\('%Y',\s*([^)]+)\)", r"TO_CHAR(\1::date, 'YYYY')", query)
    # strftime('%m', expr) → EXTRACT(MONTH FROM expr::date)
    query = re.sub(r"strftime\('%m',\s*([^)]+)\)", r"EXTRACT(MONTH FROM \1::date)", query)
    # date('now') → CURRENT_DATE (before single-arg date() regex)
    query = query.replace("date('now')", "CURRENT_DATE")
    # date(expr, '-N days') → (expr::date) - INTERVAL 'N days'
    # date(expr, '+N days') → (expr::date) + INTERVAL 'N days'
    def _replace_date(m):
        expr = m.group(1)
        sign = m.group(2)
        amount = m.group(3)
        unit = m.group(4)
        op = '-' if sign == '-' else '+'
        return f"({expr}::date) {op} INTERVAL '{amount} {unit}'"
    query = re.sub(r"date\(([^,]+),\s*'([+-])(\d+)\s+(day|days)'\)", _replace_date, query)
    # date(expr) → expr::date (single-arg date(), but not date('now') which is already replaced)
    query = re.sub(r"\bdate\(([^')]+)\)", r"(\1)::date", query)
    return query

SQLITE_PATHS = [
    os.path.join(os.path.dirname(__file__), "..", "..", "lng-data-generator", "output", "lng_fleet_analytics.db"),
    os.path.join(os.path.dirname(__file__), "..", "..", "lng_fleet_performance", "lng_fleet_analytics.db"),
]


class DictCursorWrapper:
    """Wraps a psycopg2 cursor to provide sqlite3.Row-like dict access."""

    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, query, params=None):
        q = translate_sql_for_pg(query)
        self._cursor.execute(q.replace("?", "%s") if params else q, params)
        return self

    def fetchall(self):
        return [DictRowWrapper(row) for row in self._cursor.fetchall()]

    def fetchone(self):
        row = self._cursor.fetchone()
        return DictRowWrapper(row) if row else None

    @property
    def description(self):
        return self._cursor.description

    def __iter__(self):
        for row in self._cursor:
            yield DictRowWrapper(row)


class DictRowWrapper:
    """Wraps a psycopg2 RealDictRow to provide sqlite3.Row-like access."""

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

    def __repr__(self):
        return repr(self._row)


class PostgreSQLConnection:
    """Wrapper around psycopg2 connection that mimics sqlite3 connection interface."""

    IS_POSTGRESQL = True

    def __init__(self, dsn):
        self._conn = psycopg2.connect(dsn)
        self._conn.autocommit = True

    def cursor(self):
        return DictCursorWrapper(
            self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        )

    def execute(self, query, params=None):
        cur = self.cursor()
        cur.execute(query, params)
        return cur

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


class AnalyticsDB:
    """DatabaseManager-compatible wrapper for analytics DB.

    Provides .fetchone(query, params) and .fetchall(query, params)
    that work with both SQLite and PostgreSQL connections.
    """

    def __init__(self, conn):
        self._conn = conn
        self._is_pg = getattr(conn, 'IS_POSTGRESQL', False)

    def _translate(self, query):
        if self._is_pg:
            return translate_sql_for_pg(query)
        return query

    def fetchone(self, query, params=()):
        cur = self._conn.cursor()
        q = self._translate(query)
        cur.execute(q.replace("?", "%s") if params else q, params)
        return cur.fetchone()

    def fetchall(self, query, params=()):
        cur = self._conn.cursor()
        q = self._translate(query)
        cur.execute(q.replace("?", "%s") if params else q, params)
        return cur.fetchall()

    def execute(self, query, params=()):
        cur = self._conn.cursor()
        q = self._translate(query)
        cur.execute(q.replace("?", "%s") if params else q, params)
        return cur

    def cursor(self):
        """For code that calls conn.cursor().execute() directly."""
        return self._conn.cursor()


def get_analytics_connection():
    """Get or create the analytics database connection.

    Uses DATABASE_URL env var for PostgreSQL, falls back to local SQLite.
    Returns an AnalyticsDB wrapper that supports both:
      - .fetchone(query, params) / .fetchall(query, params) — DatabaseManager style
      - .cursor().execute(query) — raw cursor style
    """
    global _ANALYTICS_CONN
    if _ANALYTICS_CONN is not None:
        return _ANALYTICS_CONN

    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        print(f"[analytics_db] Connecting to PostgreSQL: {database_url[:40]}...")
        raw_conn = PostgreSQLConnection(database_url)
        _ANALYTICS_CONN = AnalyticsDB(raw_conn)
        print("[analytics_db] Connected to PostgreSQL")
    else:
        for path in SQLITE_PATHS:
            resolved = os.path.normpath(path)
            if os.path.exists(resolved):
                print(f"[analytics_db] Connecting to SQLite: {resolved}")
                conn = sqlite3.connect(resolved)
                conn.row_factory = sqlite3.Row
                _ANALYTICS_CONN = AnalyticsDB(conn)
                return _ANALYTICS_CONN
        print("[analytics_db] WARNING: No analytics DB found")
        _ANALYTICS_CONN = None

    return _ANALYTICS_CONN


def get_analytics_cursor():
    """Get a cursor from the analytics DB connection."""
    conn = get_analytics_connection()
    if conn is None:
        return None
    return conn.cursor()

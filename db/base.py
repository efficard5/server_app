"""
db/base.py
──────────
PostgreSQL connection management using psycopg2.
"""

import os
import psycopg2
from psycopg2 import pool
from contextlib import contextmanager

# ── Connection Configuration ─────────────────────────────────────────────────
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_NAME = os.getenv("POSTGRES_DB", "pmo_db")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

# ── Connection Pool ──────────────────────────────────────────────────────────
_pool = None

def get_pool():
    global _pool
    if _pool is None:
        try:
            _pool = pool.SimpleConnectionPool(
                1, 20,
                host=DB_HOST,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASS,
                port=DB_PORT
            )
        except Exception as e:
            print(f"Error creating PostgreSQL pool: {e}")
            raise
    return _pool

@contextmanager
def get_connection():
    p = get_pool()
    conn = p.getconn()
    try:
        yield conn
    finally:
        p.putconn(conn)

@contextmanager
def get_cursor(commit=False):
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            yield cursor
            if commit:
                conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

def execute_query(query, params=None, fetch=False, commit=None):
    """Utility to execute a query and optionally fetch results."""
    # Auto-commit if it's a data-modifying query or if explicitly requested
    if commit is None:
        is_modifying = any(x in query.upper() for x in ["INSERT", "UPDATE", "DELETE", "ALTER", "CREATE", "DROP"])
        commit = is_modifying or (not fetch)
    
    with get_cursor(commit=commit) as cursor:
        cursor.execute(query, params)
        if fetch:
            return cursor.fetchall()
        return None

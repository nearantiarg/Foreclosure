"""Database access — Supabase client + direct psycopg helper.

SECURITY: The service-role key is used ONLY here (server-side). This module
is never imported by frontend code. Never log keys. Never return the client
or connection string to an API caller.
"""
from __future__ import annotations

from typing import Any

from .config import Settings, get_settings

_supabase_client: Any = None


def get_supabase_client(settings: Settings | None = None):
    """Return a Supabase client using the SERVICE_ROLE key (server-side only).

    Returns None when credentials are missing — callers must handle the
    unconfigured case with a 503, not with fake data.
    """
    global _supabase_client
    s = settings or get_settings()
    if not s.SUPABASE_URL or not s.SUPABASE_SERVICE_ROLE_KEY:
        return None
    if _supabase_client is not None:
        return _supabase_client
    try:
        from supabase import create_client

        _supabase_client = create_client(s.SUPABASE_URL, s.SUPABASE_SERVICE_ROLE_KEY)
    except Exception:
        return None
    return _supabase_client


def get_db_connection(settings: Settings | None = None):
    """Direct psycopg connection for PostGIS / COUNT(*) analytics.

    Returns None when SUPABASE_DB_URL is missing. Caller closes it.
    """
    s = settings or get_settings()
    if not s.SUPABASE_DB_URL:
        return None
    try:
        import psycopg

        return psycopg.connect(s.SUPABASE_DB_URL)
    except Exception:
        return None


def db_available(settings: Settings | None = None) -> bool:
    """Lightweight connectivity probe: SELECT 1 + PostGIS version."""
    conn = get_db_connection(settings)
    if conn is None:
        # Fall back to Supabase REST probe
        client = get_supabase_client(settings)
        if client is None:
            return False
        try:
            client.table("counties").select("id").limit(1).execute()
            return True
        except Exception:
            return False
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def postgis_available(settings: Settings | None = None) -> bool:
    conn = get_db_connection(settings)
    if conn is None:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT PostGIS_Version()")
            row = cur.fetchone()
            return row is not None
    except Exception:
        return False
    finally:
        conn.close()

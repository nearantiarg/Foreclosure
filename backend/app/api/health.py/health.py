"""Health / readiness endpoints. No data is invented here."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from ..config import Settings, get_settings
from ..db import db_available, get_supabase_client, postgis_available

router = APIRouter(tags=["health"])


@router.get("/health")
def health(settings: Settings = Depends(get_settings)):
    db_ok = db_available(settings)
    return {
        "status": "ok" if db_ok else "degraded",
        "db": "ok" if db_ok else "unavailable",
        "postgis": postgis_available(settings),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/ready")
def ready(settings: Settings = Depends(get_settings)):
    db_ok = db_available(settings)
    pg_ok = postgis_available(settings)
    # Readiness requires DB + PostGIS. If direct DB URL is absent, fall back to REST probe.
    if settings.SUPABASE_DB_URL:
        is_ready = db_ok and pg_ok
    else:
        is_ready = db_ok
    return {
        "ready": is_ready,
        "db": "ok" if db_ok else "unavailable",
        "postgis": pg_ok,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/sources")
def health_sources(settings: Settings = Depends(get_settings)):
    """Per-source health from source_health + latest ingestion_runs."""
    client = get_supabase_client(settings)
    if client is None:
        return {"sources": [], "note": "Supabase not configured — no records. Configure SUPABASE_URL + SERVICE_ROLE_KEY."}
    try:
        res = client.table("source_health").select("*").execute()
        rows = res.data or []
        return {"sources": rows}
    except Exception as exc:
        return {"sources": [], "error": str(exc)}

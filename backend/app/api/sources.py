from __future__ import annotations

from fastapi import APIRouter, Depends

from ..config import Settings, get_settings
from ..db import get_supabase_client

router = APIRouter(tags=["sources"])


@router.get("/sources")
def list_sources(settings: Settings = Depends(get_settings)):
    client = get_supabase_client(settings)
    if client is None:
        return {"sources": [], "note": "Supabase not configured — no records."}
    res = client.table("sources").select("*, source_health(*)").execute()
    return {"sources": res.data or []}

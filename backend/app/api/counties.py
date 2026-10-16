from __future__ import annotations

from fastapi import APIRouter, Depends

from ..config import Settings, get_settings
from ..db import get_supabase_client

router = APIRouter(tags=["counties"])


@router.get("/counties")
def list_counties(settings: Settings = Depends(get_settings)):
    client = get_supabase_client(settings)
    if client is None:
        return {"counties": [], "note": "Supabase not configured — no records."}
    res = client.table("counties").select("*").order("county_name").execute()
    return {"counties": res.data or []}

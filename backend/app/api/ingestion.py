"""Ingestion trigger — protected by X-Ingestion-Secret. Never open to anon."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from ..config import Settings, get_settings, require_ingestion_secret
from ..db import get_supabase_client
from ..ingestion.pipeline import CONNECTOR_REGISTRY, run_ingestion

router = APIRouter(tags=["ingestion"])


@router.post("/ingestion/run")
def trigger_ingestion(
    source_key: str = Query(...),
    mode: str = Query("incremental"),
    x_ingestion_secret: str | None = Header(None, alias="X-Ingestion-Secret"),
    settings: Settings = Depends(get_settings),
):
    if not require_ingestion_secret(x_ingestion_secret, settings):
        raise HTTPException(status_code=401, detail="Invalid or missing X-Ingestion-Secret")
    if mode not in ("incremental", "full"):
        raise HTTPException(status_code=422, detail="mode must be incremental or full")
    if source_key not in CONNECTOR_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Unknown source_key: {source_key}")
    result = run_ingestion(source_key=source_key, mode=mode, settings=settings)
    return result


@router.get("/ingestion/runs")
def list_runs(
    source_key: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    settings: Settings = Depends(get_settings),
):
    client = get_supabase_client(settings)
    if client is None:
        return {"runs": [], "note": "Supabase not configured — no records."}
    # ingestion_runs stores source_id; resolve source_key -> source_id if given
    q = client.table("ingestion_runs").select("*").order("started_at", desc=True).limit(limit)
    if source_key:
        sres = client.table("sources").select("id").eq("source_key", source_key).execute()
        if not sres.data:
            return {"runs": []}
        q = q.eq("source_id", sres.data[0]["id"])
    res = q.execute()
    return {"runs": res.data or []}

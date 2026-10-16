from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..config import Settings, get_settings
from ..db import get_supabase_client

router = APIRouter(tags=["notices"])


@router.get("/notices")
def list_notices(
    county: str | None = None,
    sale_date_from: str | None = None,
    sale_date_to: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    settings: Settings = Depends(get_settings),
):
    client = get_supabase_client(settings)
    if client is None:
        return {"notices": [], "page": page, "per_page": per_page, "note": "Supabase not configured — no records."}
    q = client.table("foreclosure_notices").select("*")
    if status:
        q = q.eq("status", status)
    if sale_date_from:
        q = q.gte("sale_date", sale_date_from)
    if sale_date_to:
        q = q.lte("sale_date", sale_date_to)
    if county:
        cres = client.table("counties").select("id").or_(f"county_name.eq.{county},county_fips.eq.{county}").execute()
        ids = [r["id"] for r in (cres.data or [])]
        if ids:
            q = q.in_("county_id", ids)
        else:
            return {"notices": [], "page": page, "per_page": per_page}
    q = q.order("sale_date", desc=True).range((page - 1) * per_page, page * per_page - 1)
    res = q.execute()
    # Attach provenance per row
    notices = []
    for r in res.data or []:
        r["provenance"] = {"source_name": r.get("source_name"), "source_url": r.get("source_url"), "first_seen_at": r.get("first_seen_at")}
        notices.append(r)
    return {"notices": notices, "page": page, "per_page": per_page}

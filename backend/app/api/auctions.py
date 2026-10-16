"""Auction calendar. Sale dates always come from published notices/lists."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query

from ..config import Settings, get_settings
from ..db import get_supabase_client

router = APIRouter(tags=["auctions"])


def _apply_filters(q, county, sale_date_from, sale_date_to, status, client):
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
            return None
    return q


@router.get("/auctions")
def list_auctions(
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
        return {"auctions": [], "page": page, "per_page": per_page, "note": "Supabase not configured — no records."}
    q = client.table("auction_events").select("*")
    q = _apply_filters(q, county, sale_date_from, sale_date_to, status, client)
    if q is None:
        return {"auctions": [], "page": page, "per_page": per_page}
    q = q.order("sale_date").range((page - 1) * per_page, page * per_page - 1)
    res = q.execute()
    auctions = []
    for r in res.data or []:
        r["provenance"] = {"source_name": "County sale list / notice", "source_url": r.get("result_source_url"), "first_seen_at": r.get("first_seen_at")}
        auctions.append(r)
    return {"auctions": auctions, "page": page, "per_page": per_page}


@router.get("/auctions/upcoming")
def upcoming_auctions(
    county: str | None = None,
    settings: Settings = Depends(get_settings),
):
    """Auctions with sale_date >= today, grouped by county + sale_date."""
    client = get_supabase_client(settings)
    if client is None:
        return {"groups": [], "note": "Supabase not configured — no records."}
    today = date.today().isoformat()
    q = client.table("auction_events").select("*, counties(county_name, county_fips)").gte("sale_date", today).order("sale_date")
    if county:
        cres = client.table("counties").select("id").or_(f"county_name.eq.{county},county_fips.eq.{county}").execute()
        ids = [r["id"] for r in (cres.data or [])]
        if ids:
            q = q.in_("county_id", ids)
        else:
            return {"groups": []}
    res = q.execute()
    groups: dict[tuple, dict] = {}
    for r in res.data or []:
        c = r.get("counties") or {}
        key = (r.get("sale_date"), c.get("county_name"))
        if key not in groups:
            groups[key] = {"sale_date": r.get("sale_date"), "county_name": c.get("county_name"), "county_fips": c.get("county_fips"), "count": 0, "auctions": []}
        groups[key]["count"] += 1
        groups[key]["auctions"].append(r)
    return {"groups": list(groups.values())}

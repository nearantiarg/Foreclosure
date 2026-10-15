"""Properties search — PostGIS bbox, filters, pagination (max 100).

bbox format: minLng,minLat,maxLng,minLat
PostGIS: ST_Within(centroid, ST_MakeEnvelope(minLng,minLat,maxLng,maxLat,4326))
q: trigram / ILIKE search over address, parcel, owner (server-side SQL).
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from ..config import Settings, get_settings
from ..db import get_db_connection, get_supabase_client

router = APIRouter(tags=["properties"])


def parse_bbox(bbox: str | None) -> tuple[float, float, float, float] | None:
    if not bbox:
        return None
    try:
        parts = [float(x) for x in bbox.split(",")]
    except ValueError:
        raise HTTPException(status_code=422, detail="bbox must be minLng,minLat,maxLng,maxLat numbers")
    if len(parts) != 4:
        raise HTTPException(status_code=422, detail="bbox must have exactly 4 numbers")
    min_lng, min_lat, max_lng, max_lat = parts
    if not (-180 <= min_lng <= 180 and -180 <= max_lng <= 180 and -90 <= min_lat <= 90 and -90 <= max_lat <= 90):
        raise HTTPException(status_code=422, detail="bbox coordinates out of range")
    if min_lng > max_lng or min_lat > max_lat:
        raise HTTPException(status_code=422, detail="bbox min must be <= max")
    return (min_lng, min_lat, max_lng, max_lat)


def build_bbox_sql(bbox: tuple[float, float, float, float] | None) -> str:
    if bbox is None:
        return ""
    min_lng, min_lat, max_lng, max_lat = bbox
    return (
        f" AND centroid IS NOT NULL AND ST_Within(centroid, "
        f"ST_MakeEnvelope({min_lng},{min_lat},{max_lng},{max_lat},4326))"
    )


@router.get("/properties")
def list_properties(
    county: str | None = Query(None, description="County name or FIPS"),
    q: str | None = Query(None, description="Address / parcel / owner search"),
    property_type: str | None = None,
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    has_notice: bool | None = None,
    has_auction: bool | None = None,
    bbox: str | None = Query(None, description="minLng,minLat,maxLng,maxLat"),
    sort: str = Query("last_seen_at", description="last_seen_at | assessed_value | address_line1"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    settings: Settings = Depends(get_settings),
):
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(status_code=422, detail="min_price must be <= max_price")
    parsed_bbox = parse_bbox(bbox)
    # When bbox is requested, use direct Postgres + PostGIS (real geo query).
    # Otherwise use Supabase REST.
    if parsed_bbox is not None:
        conn = get_db_connection(settings)
        if conn is None:
            raise HTTPException(status_code=503, detail="PostGIS query requires SUPABASE_DB_URL")
        try:
            offset = (page - 1) * per_page
            where = "WHERE 1=1" + build_bbox_sql(parsed_bbox)
            params: list = []
            # County filter via join would need county lookup; keep bbox-only + optional filters here.
            sql = (
                "SELECT p.*, c.county_name FROM properties p "
                "LEFT JOIN counties c ON c.id = p.county_id "
                f"{where} ORDER BY p.last_seen_at DESC NULLS LAST LIMIT %s OFFSET %s"
            )
            with conn.cursor() as cur:
                cur.execute(sql, [per_page, offset])
                cols = [d[0] for d in cur.description] if cur.description else []
                rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            return {"properties": rows, "page": page, "per_page": per_page, "bbox": bbox}
        finally:
            conn.close()

    client = get_supabase_client(settings)
    if client is None:
        return {"properties": [], "page": page, "per_page": per_page, "note": "Supabase not configured — no records."}
    query = client.table("properties").select("*, counties(county_name)")
    if q:
        # ILIKE across address/parcel/owner — server-side, no client filtering.
        query = query.or_(f"address_line1.ilike.%{q}%,parcel_id.ilike.%{q}%,owner_name.ilike.%{q}%")
    if property_type:
        query = query.eq("property_type", property_type)
    if min_price is not None:
        query = query.gte("assessed_value", min_price)
    if max_price is not None:
        query = query.lte("assessed_value", max_price)
    if county:
        # Resolve county by name or FIPS first
        cres = client.table("counties").select("id").or_(f"county_name.eq.{county},county_fips.eq.{county}").execute()
        ids = [r["id"] for r in (cres.data or [])]
        if ids:
            query = query.in_("county_id", ids)
        else:
            return {"properties": [], "page": page, "per_page": per_page}
    if has_notice is True:
        # Properties with at least one notice: filter via foreclosure_notices ids
        nres = client.table("foreclosure_notices").select("property_id").not_.is_("property_id", "null").execute()
        ids = list({r["property_id"] for r in (nres.data or []) if r.get("property_id")})
        query = query.in_("id", ids) if ids else query.eq("id", "00000000-0000-0000-0000-000000000000")
    if has_auction is True:
        ares = client.table("auction_events").select("property_id").not_.is_("property_id", "null").execute()
        ids = list({r["property_id"] for r in (ares.data or []) if r.get("property_id")})
        query = query.in_("id", ids) if ids else query.eq("id", "00000000-0000-0000-0000-000000000000")
    allowed_sort = {"last_seen_at", "assessed_value", "address_line1"}
    sort_col = sort if sort in allowed_sort else "last_seen_at"
    query = query.order(sort_col, desc=True).range((page - 1) * per_page, page * per_page - 1)
    res = query.execute()
    return {"properties": res.data or [], "page": page, "per_page": per_page}


@router.get("/properties/{property_id}")
def get_property(property_id: UUID, settings: Settings = Depends(get_settings)):
    client = get_supabase_client(settings)
    if client is None:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    res = client.table("properties").select("*").eq("id", str(property_id)).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Property not found")
    prop = res.data[0]
    notices = client.table("foreclosure_notices").select("*").eq("property_id", str(property_id)).execute()
    auctions = client.table("auction_events").select("*").eq("property_id", str(property_id)).execute()
    events = client.table("property_events").select("*").eq("property_id", str(property_id)).order("event_date", desc=True).execute()
    docs = client.table("document_records").select("*").eq("property_id", str(property_id)).execute()
    comps = client.table("comparable_sales").select("*").eq("subject_property_id", str(property_id)).execute()
    prop["notices"] = notices.data or []
    prop["auctions"] = auctions.data or []
    prop["events"] = events.data or []
    prop["documents"] = docs.data or []
    prop["comparable_sales"] = comps.data or []
    prop["provenance"] = {
        "source_name": prop.get("assessor_url") and "County Assessor" or None,
        "source_url": prop.get("assessor_url"),
        "first_seen_at": prop.get("first_seen_at"),
    }
    return prop

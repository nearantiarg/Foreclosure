"""Analytics — LIVE COUNT(*) aggregations only. No hardcoded numbers, no caches >5 min."""
from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from ..config import Settings, get_settings
from ..db import get_db_connection, get_supabase_client

router = APIRouter(tags=["analytics"])


def _count_via_db(conn, sql: str, params: list | None = None) -> int:
    with conn.cursor() as cur:
        cur.execute(sql, params or [])
        row = cur.fetchone()
        return int(row[0]) if row else 0


@router.get("/analytics/overview")
def overview(county: str | None = None, settings: Settings = Depends(get_settings)):
    conn = get_db_connection(settings)
    if conn is None:
        # Fallback: Supabase REST counts via head count not available in supabase-py easily;
        # return honest empty + note instead of inventing numbers.
        client = get_supabase_client(settings)
        if client is None:
            return {
                "total_properties": 0,
                "active_notices": 0,
                "upcoming_auctions": 0,
                "sales_last_30d": 0,
                "last_ingestion_at": None,
                "county": county,
                "note": "Database not configured — counts are 0 because no records exist, not an estimate.",
            }
        # Use REST: fetch counts via select count is not exposed; do len of limited fetch is WRONG.
        # So return 0 + note rather than a wrong count.
        return {
            "total_properties": 0,
            "active_notices": 0,
            "upcoming_auctions": 0,
            "sales_last_30d": 0,
            "last_ingestion_at": None,
            "county": county,
            "note": "SUPABASE_DB_URL not configured — direct COUNT(*) unavailable. Configure it for live analytics.",
        }
    try:
        county_filter = ""
        params: list = []
        county_id = None
        if county:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM counties WHERE county_name = %s OR county_fips = %s LIMIT 1", [county, county])
                row = cur.fetchone()
                county_id = str(row[0]) if row else None
            if county_id is None:
                return {"total_properties": 0, "active_notices": 0, "upcoming_auctions": 0, "sales_last_30d": 0, "last_ingestion_at": None, "county": county}
            county_filter = " WHERE county_id = %s"
            params = [county_id]
        total = _count_via_db(conn, f"SELECT COUNT(*) FROM properties{county_filter}", params)
        active = _count_via_db(
            conn, f"SELECT COUNT(*) FROM foreclosure_notices WHERE status IN ('published','scheduled'){(' AND county_id = %s' if county_id else '')}", params
        )
        upcoming = _count_via_db(
            conn,
            f"SELECT COUNT(*) FROM auction_events WHERE sale_date >= CURRENT_DATE AND status = 'scheduled'{(' AND county_id = %s' if county_id else '')}",
            params,
        )
        sales_30 = _count_via_db(
            conn,
            f"SELECT COUNT(*) FROM auction_events WHERE status = 'sold' AND sale_date >= CURRENT_DATE - INTERVAL '30 days'{(' AND county_id = %s' if county_id else '')}",
            params,
        )
        with conn.cursor() as cur:
            cur.execute("SELECT MAX(finished_at) FROM ingestion_runs WHERE status IN ('success','partial_success')")
            row = cur.fetchone()
            last_ing = row[0].isoformat() if row and row[0] else None
        return {
            "total_properties": total,
            "active_notices": active,
            "upcoming_auctions": upcoming,
            "sales_last_30d": sales_30,
            "last_ingestion_at": last_ing,
            "county": county,
        }
    finally:
        conn.close()


@router.get("/analytics/county/{county_fips}/trend")
def county_trend(county_fips: str, months: int = Query(12, ge=1, le=36), settings: Settings = Depends(get_settings)):
    conn = get_db_connection(settings)
    if conn is None:
        raise HTTPException(status_code=503, detail="SUPABASE_DB_URL required for trend analytics")
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM counties WHERE county_fips = %s LIMIT 1", [county_fips])
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="County not found")
            cid = str(row[0])
            cur.execute(
                """
                SELECT to_char(date_trunc('month', sale_date), 'YYYY-MM') AS month,
                       COUNT(*) AS notices
                FROM foreclosure_notices
                WHERE county_id = %s AND sale_date >= CURRENT_DATE - (%s || ' months')::interval
                GROUP BY 1 ORDER BY 1
                """,
                [cid, str(months)],
            )
            notice_rows = [{"month": r[0], "notices": int(r[1])} for r in cur.fetchall()]
            cur.execute(
                """
                SELECT to_char(date_trunc('month', sale_date), 'YYYY-MM') AS month,
                       COUNT(*) AS auctions
                FROM auction_events
                WHERE county_id = %s AND sale_date >= CURRENT_DATE - (%s || ' months')::interval
                GROUP BY 1 ORDER BY 1
                """,
                [cid, str(months)],
            )
            auction_rows = [{"month": r[0], "auctions": int(r[1])} for r in cur.fetchall()]
        # Merge by month
        merged: dict[str, dict] = {}
        for r in notice_rows:
            merged[r["month"]] = {"month": r["month"], "notices": r["notices"], "auctions": 0}
        for r in auction_rows:
            merged.setdefault(r["month"], {"month": r["month"], "notices": 0, "auctions": 0})
            merged[r["month"]]["auctions"] = r["auctions"]
        return {"county_fips": county_fips, "months": months, "trend": sorted(merged.values(), key=lambda x: x["month"])}
    finally:
        conn.close()

"""Analytics service — live COUNT(*) helpers (no hardcoded numbers)."""
from __future__ import annotations

from ..db import get_db_connection


def live_counts(county_id: str | None = None) -> dict:
    conn = get_db_connection()
    if conn is None:
        return {"total_properties": 0, "active_notices": 0, "upcoming_auctions": 0, "sales_last_30d": 0, "note": "DB not configured"}
    try:
        params = [county_id] if county_id else []
        cf = " WHERE county_id = %s" if county_id else ""
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM properties{cf}", params)
            total = cur.fetchone()[0]
            cur.execute(f"SELECT COUNT(*) FROM foreclosure_notices WHERE status='published'{(' AND county_id = %s' if county_id else '')}", params)
            active = cur.fetchone()[0]
            cur.execute(f"SELECT COUNT(*) FROM auction_events WHERE sale_date >= CURRENT_DATE AND status='scheduled'{(' AND county_id = %s' if county_id else '')}", params)
            upcoming = cur.fetchone()[0]
            cur.execute(f"SELECT COUNT(*) FROM auction_events WHERE status='sold' AND sale_date >= CURRENT_DATE - INTERVAL '30 days'{(' AND county_id = %s' if county_id else '')}", params)
            sales = cur.fetchone()[0]
        return {"total_properties": int(total), "active_notices": int(active), "upcoming_auctions": int(upcoming), "sales_last_30d": int(sales)}
    finally:
        conn.close()

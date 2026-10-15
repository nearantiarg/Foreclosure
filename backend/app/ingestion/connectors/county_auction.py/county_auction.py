"""County auction / First Tuesday sale lists (Forsyth + Fulton clerk / sheriff / tax commissioner).

Parses public sale-list pages/PDF-converted HTML. Sale dates/locations come
from the published list — never computed. Status defaults to 'scheduled'
unless the list explicitly says postponed/cancelled.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup

from ...schemas import AuctionEvent
from ..base import BaseConnector, content_hash

DATE_RE = re.compile(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}", re.I)


class CountyAuctionConnector(BaseConnector):
    source_key = "county_auction"
    display_name = "County First Tuesday Sale Lists (Forsyth + Fulton)"
    base_url = "https://www.forsythco.com"
    record_kind = "auction"

    def list_page_urls(self, mode: str = "incremental", since: str | None = None) -> list[str]:
        return [
            "https://www.forsythco.com/Departments-Offices/Tax-Commissioner/Tax-Sales",
            "https://www.fultoncountyga.gov/services/tax-sales",
        ]

    def parse(self, html_or_text: str, page_url: str) -> list[dict[str, Any]]:
        soup = BeautifulSoup(html_or_text, "html.parser")
        text = soup.get_text("\n")
        out = []
        for line in text.splitlines():
            line = line.strip()
            m = DATE_RE.search(line)
            if not m or len(line) < 20:
                continue
            try:
                sale_date = datetime.strptime(m.group(0), "%B %d, %Y").date()
            except ValueError:
                continue
            status = "scheduled"
            if "postpone" in line.lower():
                status = "postponed"
            elif "cancel" in line.lower():
                status = "cancelled"
            out.append({"line": line, "sale_date": sale_date.isoformat(), "status": status, "source_url": page_url, "source_record_id": content_hash(line)})
        return out

    def normalize(self, raw: dict[str, Any], page_url: str) -> AuctionEvent:
        location = "Forsyth County Courthouse steps, Cumming, GA" if "forsyth" in page_url.lower() else "Fulton County Courthouse, Atlanta, GA"
        return AuctionEvent(
            sale_date=datetime.fromisoformat(raw["sale_date"]).date(),
            sale_location=location,
            sale_type="foreclosure",
            status=raw.get("status", "scheduled"),
            result_source_url=raw.get("source_url") or page_url,
            content_hash=content_hash(raw),
        )

    def dedupe_key(self, record: Any) -> str:
        return content_hash({"sale_date": str(record.sale_date), "location": record.sale_location, "status": record.status})

    def high_water_mark(self, records: list[Any]) -> str | None:
        if not records:
            return None
        return max(str(r.sale_date) for r in records)

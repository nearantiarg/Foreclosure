"""HUD HomeStore / Fannie Mae HomePath / Freddie Mac HomeSteps — REO listings.

REO is NOT a foreclosure notice. These are stored as auction_events with
sale_type='REO_auction' and must never be mixed into foreclosure counts.
Parses public REO listing cards. Returns [] if structure unrecognized.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any

from bs4 import BeautifulSoup

from ...schemas import AuctionEvent
from ..base import BaseConnector, content_hash


class HUDREOConnector(BaseConnector):
    source_key = "hud_reo"
    display_name = "HUD HomeStore / HomePath / HomeSteps (REO)"
    base_url = "https://www.hudhomestore.gov"
    record_kind = "auction"

    def list_page_urls(self, mode: str = "incremental", since: str | None = None) -> list[str]:
        return [f"{self.base_url}/listing/HomeStore.aspx?page={n}" for n in range(1, self.max_pages + 1)]

    def parse(self, html_or_text: str, page_url: str) -> list[dict[str, Any]]:
        soup = BeautifulSoup(html_or_text, "html.parser")
        out = []
        # Generic: look for listing blocks containing an address + price
        for el in soup.find_all(["article", "div"], class_=re.compile(r"listing|property|result", re.I)):
            text = el.get_text(" ", strip=True)
            price_m = re.search(r"\$([\d,]+)", text)
            if not price_m or len(text) < 30:
                continue
            out.append({"text": text[:2000], "price": price_m.group(1).replace(",", ""), "source_url": page_url, "source_record_id": content_hash(text[:500])})
        return out

    def normalize(self, raw: dict[str, Any], page_url: str) -> AuctionEvent:
        # REO listings have no first-Tuesday sale date; use today as listing date context
        # and store as REO_auction with status scheduled. Sale_date here = listing seen date,
        # NOT a foreclosure sale date — callers must label it as REO.
        return AuctionEvent(
            sale_date=date.today(),
            sale_location="REO listing — see source",
            sale_type="REO_auction",
            status="scheduled",
            opening_bid=float(raw["price"]) if raw.get("price") else None,
            result_source_url=raw.get("source_url") or page_url,
            content_hash=content_hash(raw),
        )

    def dedupe_key(self, record: Any) -> str:
        return content_hash({"type": "REO", "location": record.sale_location, "bid": str(record.opening_bid)})

    def high_water_mark(self, records: list[Any]) -> str | None:
        return f"{len(records)} REO listings" if records else None

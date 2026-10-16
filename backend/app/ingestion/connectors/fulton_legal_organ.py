"""Fulton County legal organ — Daily Report legal notices.

Same contract as Forsyth. If paywalled/blocked, do NOT scrape around it —
fetch failure → pipeline marks source degraded/down and documents the block.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup

from ...schemas import ForeclosureNotice
from ..base import BaseConnector, content_hash

SALE_DATE_RE = re.compile(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}", re.I)
PARCEL_RE = re.compile(r"(?:Parcel|Tax Parcel|Parcel ID|APN)[:\s#]*([A-Z0-9\-\. ]+)", re.I)
DEED_RE = re.compile(r"Deed Book\s+(\d+)[,\s]+Page\s+(\d+)", re.I)


class FultonLegalOrganConnector(BaseConnector):
    source_key = "fulton_legal_organ"
    display_name = "Daily Report — Fulton Legal Notices"
    base_url = "https://www.law.com/daily-report/"
    record_kind = "notice"

    def list_page_urls(self, mode: str = "incremental", since: str | None = None) -> list[str]:
        return [f"{self.base_url}legal-notices/?page={n}" for n in range(1, self.max_pages + 1)]

    def parse(self, html_or_text: str, page_url: str) -> list[dict[str, Any]]:
        soup = BeautifulSoup(html_or_text, "html.parser")
        text = soup.get_text("\n")
        blocks = re.split(r"(?i)(?=NOTICE OF SALE UNDER POWER)", text)
        out = []
        for block in blocks:
            if "NOTICE OF SALE UNDER POWER" not in block.upper():
                continue
            m = SALE_DATE_RE.search(block)
            if not m:
                continue
            try:
                sale_date = datetime.strptime(m.group(0), "%B %d, %Y").date()
            except ValueError:
                continue
            parcel_m = PARCEL_RE.search(block)
            deed_m = DEED_RE.search(block)
            out.append(
                {
                    "notice_text": block.strip()[:10000],
                    "sale_date": sale_date.isoformat(),
                    "parcel_id": parcel_m.group(1).strip() if parcel_m else None,
                    "deed_book": deed_m.group(1) if deed_m else None,
                    "deed_page": deed_m.group(2) if deed_m else None,
                    "source_url": page_url,
                    "source_record_id": content_hash(block.strip()[:2000]),
                }
            )
        return out

    def normalize(self, raw: dict[str, Any], page_url: str) -> ForeclosureNotice:
        return ForeclosureNotice(
            source_name=self.display_name,
            source_url=raw.get("source_url") or page_url,
            source_record_id=raw["source_record_id"],
            notice_type="Notice of Sale Under Power",
            sale_date=datetime.fromisoformat(raw["sale_date"]).date(),
            sale_location="Fulton County Courthouse, Atlanta, GA",
            deed_book=raw.get("deed_book"),
            deed_page=raw.get("deed_page"),
            parcel_id=raw.get("parcel_id"),
            notice_text=raw.get("notice_text"),
            status="published",
            content_hash=content_hash(raw),
        )

    def dedupe_key(self, record: Any) -> str:
        return f"{record.source_name}:{record.source_record_id}"

    def high_water_mark(self, records: list[Any]) -> str | None:
        if not records:
            return None
        return max(str(r.sale_date) for r in records)

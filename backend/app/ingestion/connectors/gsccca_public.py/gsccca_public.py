"""GSCCCA — Georgia Superior Court Clerks' Cooperative Authority, public index.

Public search only. Bulk/API access may require subscription — that path is
PENDING_LICENSE and must NOT be faked. This connector parses the public
instrument-index result table. If the table is absent, returns [].
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup

from ...schemas import DocumentRecord
from ..base import BaseConnector, content_hash


class GSCCCAPublicConnector(BaseConnector):
    source_key = "gsccca_public"
    display_name = "GSCCCA — Public Real Estate Index"
    base_url = "https://www.gsccca.org"
    record_kind = "document"

    def list_page_urls(self, mode: str = "incremental", since: str | None = None) -> list[str]:
        return [f"{self.base_url}/search/real-estate?page={n}" for n in range(1, self.max_pages + 1)]

    def parse(self, html_or_text: str, page_url: str) -> list[dict[str, Any]]:
        soup = BeautifulSoup(html_or_text, "html.parser")
        rows = []
        for tr in soup.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
            if len(cells) < 4:
                continue
            # Heuristic: instrument rows contain a book/page pattern or instrument number
            if not re.search(r"\d+", " ".join(cells)):
                continue
            rows.append({"cells": cells, "source_url": page_url})
        return rows

    def normalize(self, raw: dict[str, Any], page_url: str) -> DocumentRecord:
        cells: list[str] = raw.get("cells", [])
        # Positional parsing is best-effort; require at least a document type + one identifier.
        doc_type = cells[0] if cells else "Unknown"
        recorded = None
        for c in cells:
            for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
                try:
                    recorded = datetime.strptime(c, fmt).date()
                    break
                except ValueError:
                    continue
            if recorded:
                break
        return DocumentRecord(
            document_type=doc_type,
            recorded_date=recorded,
            source_name=self.display_name,
            source_url=raw.get("source_url") or page_url,
            source_record_id=content_hash(cells),
            content_hash=content_hash(raw),
        )

    def dedupe_key(self, record: Any) -> str:
        return f"{record.source_name}:{record.source_record_id}"

    def high_water_mark(self, records: list[Any]) -> str | None:
        return f"{len(records)} instruments" if records else None

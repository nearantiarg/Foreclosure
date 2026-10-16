"""Fulton County Board of Assessors / qPublic — parcel records.

Fulton parcel IDs differ in format from Forsyth — normalization lives in
BaseConnector.normalize_parcel_id (strip non-alphanumerics, uppercase) and
per-county parsing lives here, not in shared code.
"""
from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from ...schemas import Property
from ..base import BaseConnector, content_hash, normalize_parcel_id
from .forsyth_qpublic import _label_value_map


class FultonAssessorConnector(BaseConnector):
    source_key = "fulton_assessor"
    display_name = "Fulton County Board of Assessors"
    base_url = "https://www.fultoncountyga.gov/services/board-of-assessors"
    record_kind = "property"

    def list_page_urls(self, mode: str = "incremental", since: str | None = None) -> list[str]:
        return [self.base_url]

    def parse(self, html_or_text: str, page_url: str) -> list[dict[str, Any]]:
        soup = BeautifulSoup(html_or_text, "html.parser")
        m = _label_value_map(soup)
        parcel = m.get("parcel id") or m.get("parcel") or m.get("parcel number") or m.get("parcel id (apn)")
        if not parcel:
            return []
        return [{"fields": m, "source_url": page_url, "parcel_id": parcel}]

    def normalize(self, raw: dict[str, Any], page_url: str) -> Property:
        f: dict[str, str] = raw.get("fields", {})
        parcel = raw["parcel_id"]
        def _num(key: str):
            v = f.get(key)
            if not v:
                return None
            v = re.sub(r"[^0-9.\-]", "", v)
            try:
                return float(v) if v else None
            except ValueError:
                return None

        def _int(key: str):
            n = _num(key)
            return int(n) if n is not None else None

        return Property(
            parcel_id=parcel,
            parcel_id_normalized=normalize_parcel_id(parcel),
            address_line1=f.get("property address") or f.get("address") or f.get("situs address"),
            owner_name=f.get("owner") or f.get("owner name"),
            property_type=f.get("property class") or f.get("property type") or f.get("land use"),
            year_built=_int("year built"),
            living_area_sqft=_num("living area") or _num("total living area"),
            lot_acres=_num("lot size (acres)") or _num("acres"),
            assessed_value=_num("assessed value"),
            appraised_value=_num("appraised value") or _num("fair market value"),
            tax_year=_int("tax year"),
            assessor_url=raw.get("source_url") or page_url,
            content_hash=content_hash(raw),
        )

    def dedupe_key(self, record: Any) -> str:
        return record.parcel_id_normalized or record.parcel_id

    def high_water_mark(self, records: list[Any]) -> str | None:
        return f"{len(records)} parcels" if records else None

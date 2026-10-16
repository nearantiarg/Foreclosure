"""Forsyth County qPublic (Schneider Geospatial) — parcel records.

Parcel-by-parcel fetch driven by parcels discovered from notices + backfill.
Parses the qPublic parcel detail table (label/value rows). Returns [] if the
page structure is unrecognized — never invent parcel fields.
"""
from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from ...schemas import Property
from ..base import BaseConnector, content_hash, normalize_parcel_id


def _label_value_map(soup: BeautifulSoup) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in soup.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]
        if len(cells) >= 2 and cells[0]:
            out[cells[0].lower()] = cells[1]
    return out


class ForsythQPublicConnector(BaseConnector):
    source_key = "forsyth_qpublic"
    display_name = "Forsyth County qPublic — Tax Assessors"
    base_url = "https://qpublic.schneidercorp.com/application.aspx"
    record_kind = "property"

    def list_page_urls(self, mode: str = "incremental", since: str | None = None) -> list[str]:
        # qPublic is parcel-driven; pipeline callers should supply parcel URLs via
        # list_page_urls_for_parcels(). Default returns the search landing page.
        return [self.base_url + "?AppID=1013&LayerID=20808&PageTypeID=2"]

    def list_page_urls_for_parcels(self, parcel_ids: list[str]) -> list[str]:
        return [f"{self.base_url}?AppID=1013&LayerID=20808&PageTypeID=2&ParcelID={p}" for p in parcel_ids]

    def parse(self, html_or_text: str, page_url: str) -> list[dict[str, Any]]:
        soup = BeautifulSoup(html_or_text, "html.parser")
        m = _label_value_map(soup)
        # Parcel ID is required — without it this is not a parcel record.
        parcel = m.get("parcel id") or m.get("parcel") or m.get("parcel number")
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
            address_line1=f.get("property address") or f.get("address"),
            owner_name=f.get("owner") or f.get("owner name"),
            property_type=f.get("property class") or f.get("property type"),
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
        if not records:
            return None
        return f"{len(records)} parcels"

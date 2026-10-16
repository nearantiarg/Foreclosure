"""Notice → property matching.

1. Exact: (county_id, parcel_id_normalized) when notice carries a parcel ID.
2. Fuzzy: normalized address + owner, threshold 0.82 (difflib). Below threshold:
   log for review, NEVER auto-link.
"""
from __future__ import annotations

import difflib
import logging
import re

logger = logging.getLogger("ingestion.matching")

FUZZY_THRESHOLD = 0.82


def normalize_address(addr: str | None) -> str:
    if not addr:
        return ""
    a = addr.upper()
    a = re.sub(r"[^A-Z0-9 ]", " ", a)
    a = re.sub(r"\s+", " ", a).strip()
    for old, new in [(" STREET", " ST"), (" AVENUE", " AVE"), (" DRIVE", " DR"), (" ROAD", " RD"), (" LANE", " LN"), (" COURT", " CT")]:
        a = a.replace(old, new)
    return a


def normalize_owner(name: str | None) -> str:
    if not name:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 ]", " ", name.upper())).strip()


def match_by_parcel(notice_parcel: str | None, properties: list[dict]) -> dict | None:
    """properties: list of dicts with parcel_id_normalized."""
    if not notice_parcel:
        return None
    from .base import normalize_parcel_id

    target = normalize_parcel_id(notice_parcel)
    for p in properties:
        if p.get("parcel_id_normalized") == target:
            return p
    return None


def match_fuzzy(notice_address: str | None, notice_owner: str | None, properties: list[dict]) -> tuple[dict | None, float]:
    """Return (best_property, score). Score < threshold → caller must NOT link."""
    if not notice_address and not notice_owner:
        return None, 0.0
    na = normalize_address(notice_address)
    no = normalize_owner(notice_owner)
    best: dict | None = None
    best_score = 0.0
    for p in properties:
        pa = normalize_address(p.get("address_line1"))
        po = normalize_owner(p.get("owner_name"))
        addr_score = difflib.SequenceMatcher(None, na, pa).ratio() if na and pa else 0.0
        owner_score = difflib.SequenceMatcher(None, no, po).ratio() if no and po else 0.0
        # Address dominates; owner is a tie-breaker
        score = 0.7 * addr_score + 0.3 * owner_score if (na and pa and no and po) else addr_score
        if score > best_score:
            best_score = score
            best = p
    if best is not None and best_score < FUZZY_THRESHOLD:
        logger.info("low-confidence match (score=%.3f) — NOT linking; needs review: notice_address=%s", best_score, notice_address)
        return None, best_score
    return best, best_score

"""Matching service — re-export of ingestion matching for API/service use."""
from ..ingestion.matching import FUZZY_THRESHOLD, match_by_parcel, match_fuzzy, normalize_address, normalize_owner

__all__ = ["FUZZY_THRESHOLD", "match_by_parcel", "match_fuzzy", "normalize_address", "normalize_owner"]

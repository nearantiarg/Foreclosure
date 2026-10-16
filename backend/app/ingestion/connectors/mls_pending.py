"""MLS / FMLS comparable sales — PENDING_LICENSE.

This connector NEVER returns records. It raises LicenseRequiredError so the
pipeline records a failed run with code license_required and the UI shows
'Comparable sales via MLS — pending license'. Do NOT fabricate comps.
"""
from __future__ import annotations

from typing import Any

from ...schemas import LicenseRequiredError
from ..base import BaseConnector


class MLSPendingConnector(BaseConnector):
    source_key = "mls_pending"
    display_name = "MLS / FMLS Comparable Sales"
    base_url = "https://www.fmls.com"
    license_status = "PENDING_LICENSE"
    record_kind = "notice"  # unused — no records ever produced

    def list_page_urls(self, mode: str = "incremental", since: str | None = None) -> list[str]:
        return []

    def parse(self, html_or_text: str, page_url: str) -> list[dict[str, Any]]:
        return []

    def normalize(self, raw: dict[str, Any], page_url: str) -> Any:
        raise LicenseRequiredError(self.source_key, "MLS comps require a license — no records fetched.")

    def check_license(self) -> None:
        raise LicenseRequiredError(self.source_key, "MLS / FMLS comparable sales require a license/approval — no records fetched.")

    def search_comps(self, parcel_id: str) -> list[dict]:
        """Public interface for future licensed implementation."""
        raise LicenseRequiredError(self.source_key, "MLS comps require a license — no records fetched.")

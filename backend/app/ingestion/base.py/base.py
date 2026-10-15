"""BaseConnector — every connector inherits this. No connector writes SQL directly.

It yields normalized Pydantic models; the pipeline upserts.
Georgia note: sale_date MUST come from the published notice. Never compute
a first-Tuesday date to fill a missing sale_date.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import time
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Iterable

import httpx

from ..config import Settings, get_settings
from ..schemas import LicenseRequiredError


def content_hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str).encode()
    return hashlib.sha256(raw).hexdigest()


def normalize_parcel_id(parcel_id: str) -> str:
    import re

    return re.sub(r"[^A-Z0-9]", "", parcel_id.upper())


class BaseConnector(ABC):
    source_key: str = ""
    display_name: str = ""
    base_url: str = ""
    license_status: str = "public"  # public | PENDING_LICENSE
    page_delay_seconds: float = 1.5
    max_pages: int = 50
    timeout_seconds: float = 30.0

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        if self.settings.INGESTION_PAGE_DELAY_SECONDS:
            self.page_delay_seconds = self.settings.INGESTION_PAGE_DELAY_SECONDS
        if self.settings.INGESTION_MAX_PAGES:
            self.max_pages = self.settings.INGESTION_MAX_PAGES
        if self.settings.INGESTION_TIMEOUT_SECONDS:
            self.timeout_seconds = self.settings.INGESTION_TIMEOUT_SECONDS

    # ---- HTTP with retries ----
    def fetch_url(self, url: str, headers: dict | None = None) -> tuple[int, str, dict]:
        """Fetch with 3 attempts, exponential backoff on 429/5xx, respect Retry-After."""
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                with httpx.Client(timeout=self.timeout_seconds, follow_redirects=True) as client:
                    resp = client.get(url, headers=headers or {"User-Agent": "GeorgiaForeclosurePlatform/0.1 (public-records ingestion)"})
                if resp.status_code in (429, 502, 503, 504):
                    retry_after = resp.headers.get("Retry-After")
                    wait = float(retry_after) if retry_after and retry_after.isdigit() else (2 ** attempt)
                    time.sleep(wait)
                    continue
                return resp.status_code, resp.text, dict(resp.headers)
            except httpx.HTTPError as exc:
                last_exc = exc
                time.sleep(2 ** attempt)
        raise RuntimeError(f"fetch failed after 3 attempts for {url}: {last_exc}")

    def delay(self) -> None:
        if self.page_delay_seconds > 0:
            time.sleep(self.page_delay_seconds)

    # ---- Abstract contract ----
    @abstractmethod
    def list_page_urls(self, mode: str = "incremental", since: str | None = None) -> list[str]:
        """Return paginated URLs to fetch, in order. Respect max_pages."""

    @abstractmethod
    def parse(self, html_or_text: str, page_url: str) -> list[dict[str, Any]]:
        """Parse one page into raw dicts (unvalidated). Return [] if no records."""

    @abstractmethod
    def normalize(self, raw: dict[str, Any], page_url: str) -> Any:
        """Convert raw dict -> validated Pydantic model. Raise ValidationError on bad rows."""

    def dedupe_key(self, record: Any) -> str:
        """Stable natural key for dedupe. Override per connector."""
        if hasattr(record, "source_record_id") and hasattr(record, "source_name"):
            return f"{getattr(record, 'source_name')}:{getattr(record, 'source_record_id')}"
        return content_hash(record.model_dump() if hasattr(record, "model_dump") else record)

    def high_water_mark(self, records: list[Any]) -> str | None:
        """High-water mark from this batch (e.g. max sale_date / last instrument)."""
        return None

    def check_license(self) -> None:
        if self.license_status == "PENDING_LICENSE":
            raise LicenseRequiredError(self.source_key, f"{self.display_name} requires a license/approval — no records fetched.")

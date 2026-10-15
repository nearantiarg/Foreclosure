"""Shared ingestion pipeline.

Flow: fetch → raw_payloads (archive FIRST) → parse → validate (Pydantic) →
dedupe by natural key + content_hash → upsert → high-water → ingestion_runs + source_health.

- Pagination loop with max_pages safety cap, stop on empty page / no new ids / 404.
- Validation failures are COUNTED (records_failed) + recorded in error_details, never silently dropped.
- One source failing must not block others (run_ingestion catches per-source errors).
- Store abstraction: SupabaseStore (prod) / InMemoryStore (tests).
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Protocol

from ..config import Settings, get_settings
from ..db import get_supabase_client
from ..schemas import LicenseRequiredError

logger = logging.getLogger("ingestion.pipeline")


class Store(Protocol):
    def get_existing_hash(self, table: str, dedupe_key: str) -> str | None: ...
    def upsert(self, table: str, dedupe_key: str, record: dict, content_hash: str) -> str: ...  # returns inserted|updated|skipped
    def insert_raw_payload(self, payload: dict) -> None: ...
    def insert_ingestion_run(self, run: dict) -> str: ...
    def update_ingestion_run(self, run_id: str, patch: dict) -> None: ...
    def upsert_source_health(self, source_key: str, status: str, error: str | None, consecutive_failures: int) -> None: ...
    def get_source_id(self, source_key: str) -> str | None: ...


class InMemoryStore:
    """Test store — never used in production code paths."""

    def __init__(self):
        self.rows: dict[str, dict[str, dict]] = {}
        self.hashes: dict[str, dict[str, str]] = {}
        self.raw: list[dict] = []
        self.runs: dict[str, dict] = {}
        self.health: dict[str, dict] = {}
        self.source_ids: dict[str, str] = {}

    def get_existing_hash(self, table: str, dedupe_key: str) -> str | None:
        return self.hashes.get(table, {}).get(dedupe_key)

    def upsert(self, table: str, dedupe_key: str, record: dict, content_hash: str) -> str:
        existing = self.get_existing_hash(table, dedupe_key)
        if existing == content_hash:
            return "skipped"
        self.rows.setdefault(table, {})[dedupe_key] = record
        self.hashes.setdefault(table, {})[dedupe_key] = content_hash
        return "updated" if existing is not None else "inserted"

    def insert_raw_payload(self, payload: dict) -> None:
        self.raw.append(payload)

    def insert_ingestion_run(self, run: dict) -> str:
        rid = str(uuid.uuid4())
        run["id"] = rid
        self.runs[rid] = run
        return rid

    def update_ingestion_run(self, run_id: str, patch: dict) -> None:
        if run_id in self.runs:
            self.runs[run_id].update(patch)

    def upsert_source_health(self, source_key: str, status: str, error: str | None, consecutive_failures: int) -> None:
        self.health[source_key] = {"status": status, "last_error": error, "consecutive_failures": consecutive_failures}

    def get_source_id(self, source_key: str) -> str | None:
        return self.source_ids.get(source_key, str(uuid.uuid4()))


class SupabaseStore:
    """Production store backed by Supabase (service-role, server-side only)."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = get_supabase_client(settings)
        if self.client is None:
            raise RuntimeError("Supabase not configured — cannot run production ingestion")

    def get_existing_hash(self, table: str, dedupe_key: str) -> str | None:
        # dedupe_key for notices/docs = source_name:source_record_id; we look up by source_record_id.
        # For properties, dedupe_key = parcel normalized — handled by caller via record fields.
        # Generic fallback: try source_record_id lookup, else parcel lookup.
        try:
            if ":" in dedupe_key:
                _, rec_id = dedupe_key.split(":", 1)
                res = self.client.table(table).select("content_hash").eq("source_record_id", rec_id).limit(1).execute()
                if res.data:
                    return res.data[0].get("content_hash")
            else:
                res = self.client.table(table).select("content_hash").eq("parcel_id_normalized", dedupe_key).limit(1).execute()
                if res.data:
                    return res.data[0].get("content_hash")
        except Exception:
            return None
        return None

    def upsert(self, table: str, dedupe_key: str, record: dict, content_hash: str) -> str:
        existing = self.get_existing_hash(table, dedupe_key)
        if existing == content_hash:
            return "skipped"
        # Strip Pydantic-only fields that are not DB columns
        db_record = {k: v for k, v in record.items() if k not in ("provenance", "county_name", "parcel_id")}
        db_record["content_hash"] = content_hash
        # Use on_conflict via upsert; supabase-py upsert requires unique constraint
        try:
            self.client.table(table).upsert(db_record).execute()
        except Exception:
            # Fallback: insert
            self.client.table(table).insert(db_record).execute()
        return "updated" if existing is not None else "inserted"

    def insert_raw_payload(self, payload: dict) -> None:
        try:
            self.client.table("raw_payloads").insert(payload).execute()
        except Exception as exc:
            logger.warning("raw_payload insert failed: %s", exc)

    def insert_ingestion_run(self, run: dict) -> str:
        res = self.client.table("ingestion_runs").insert(run).execute()
        return res.data[0]["id"] if res.data else str(uuid.uuid4())

    def update_ingestion_run(self, run_id: str, patch: dict) -> None:
        self.client.table("ingestion_runs").update(patch).eq("id", run_id).execute()

    def upsert_source_health(self, source_key: str, status: str, error: str | None, consecutive_failures: int) -> None:
        try:
            sres = self.client.table("sources").select("id").eq("source_key", source_key).execute()
            if not sres.data:
                return
            sid = sres.data[0]["id"]
            self.client.table("source_health").upsert(
                {"source_id": sid, "status": status, "last_check_at": datetime.now(timezone.utc).isoformat(), "consecutive_failures": consecutive_failures, "last_error": error}
            ).execute()
        except Exception as exc:
            logger.warning("source_health upsert failed: %s", exc)

    def get_source_id(self, source_key: str) -> str | None:
        try:
            res = self.client.table("sources").select("id").eq("source_key", source_key).execute()
            return res.data[0]["id"] if res.data else None
        except Exception:
            return None


def _table_for(connector) -> str:
    from ..schemas import AuctionEvent, DocumentRecord, ForeclosureNotice, Property

    # Infer from connector's record_kind if set, else default to notices
    kind = getattr(connector, "record_kind", "notice")
    return {"property": "properties", "notice": "foreclosure_notices", "auction": "auction_events", "document": "document_records"}.get(kind, "foreclosure_notices")


def run_pipeline(connector, store: Store, mode: str = "incremental", since: str | None = None, max_pages: int | None = None) -> dict:
    """Run one connector end-to-end. Returns run summary dict."""
    started = datetime.now(timezone.utc)
    run_id = store.insert_ingestion_run(
        {
            "source_id": store.get_source_id(connector.source_key) or str(uuid.uuid4()),
            "started_at": started.isoformat(),
            "status": "running",
            "triggered_by": "manual" if mode == "full" else "scheduled",
        }
    )
    counts = {"pages_fetched": 0, "records_seen": 0, "records_inserted": 0, "records_updated": 0, "records_skipped": 0, "records_failed": 0}
    errors: list[dict] = []
    high_water: str | None = None
    status = "success"
    try:
        connector.check_license()
        urls = connector.list_page_urls(mode=mode, since=since)
        cap = max_pages or connector.max_pages
        urls = urls[:cap]
        seen_ids: set[str] = set()
        all_records: list[Any] = []
        for url in urls:
            if counts["pages_fetched"] >= cap:
                break
            try:
                code, text, _headers = connector.fetch_url(url)
            except Exception as exc:
                errors.append({"url": url, "error": str(exc)})
                counts["records_failed"] += 1
                continue
            counts["pages_fetched"] += 1
            # Raw archive FIRST, before parsing
            payload_hash = hashlib.sha256(text.encode()).hexdigest()
            store.insert_raw_payload(
                {"source_id": store.get_source_id(connector.source_key) or str(uuid.uuid4()), "ingestion_run_id": run_id, "source_url": url, "payload_hash": payload_hash, "payload_type": "html", "payload_text": text[:100000], "fetched_at": datetime.now(timezone.utc).isoformat()}
            )
            if code == 404:
                break  # out-of-range page
            if code != 200:
                errors.append({"url": url, "error": f"HTTP {code}"})
                continue
            try:
                raw_rows = connector.parse(text, url)
            except Exception as exc:
                errors.append({"url": url, "error": f"parse: {exc}"})
                counts["records_failed"] += 1
                continue
            if not raw_rows:
                break  # empty page → stop pagination
            # Stop if no new source_record_ids (incremental fast-path)
            new_in_page = 0
            for raw in raw_rows:
                counts["records_seen"] += 1
                try:
                    record = connector.normalize(raw, url)
                except Exception as exc:
                    counts["records_failed"] += 1
                    errors.append({"url": url, "error": f"validation: {exc}", "raw": str(raw)[:500]})
                    continue
                key = connector.dedupe_key(record)
                if key in seen_ids and mode == "incremental":
                    continue
                seen_ids.add(key)
                new_in_page += 1
                all_records.append(record)
                # Dedupe + upsert
                from ..ingestion.base import content_hash as _ch

                ch = _ch(record.model_dump(mode="json") if hasattr(record, "model_dump") else record)
                table = _table_for(connector)
                outcome = store.upsert(table, key, record.model_dump(mode="json") if hasattr(record, "model_dump") else dict(record), ch)
                counts[f"records_{outcome}"] = counts.get(f"records_{outcome}", 0) + 1
            if new_in_page == 0 and mode == "incremental":
                break
            connector.delay()
        high_water = connector.high_water_mark(all_records)
        if errors and (counts["records_inserted"] + counts["records_updated"] > 0):
            status = "partial_success"
        elif errors and counts["records_inserted"] == 0 and counts["records_updated"] == 0 and counts["records_seen"] > 0:
            status = "partial_success"
        elif errors and counts["records_seen"] == 0 and counts["pages_fetched"] == 0:
            status = "failed"
    except LicenseRequiredError as exc:
        status = "failed"
        errors.append({"error": str(exc), "code": "license_required"})
    except Exception as exc:
        status = "failed"
        errors.append({"error": str(exc)})
    finished = datetime.now(timezone.utc)
    store.update_ingestion_run(
        run_id,
        {
            "finished_at": finished.isoformat(),
            "status": status,
            "pages_fetched": counts["pages_fetched"],
            "records_seen": counts["records_seen"],
            "records_inserted": counts["records_inserted"],
            "records_updated": counts["records_updated"],
            "records_skipped": counts["records_skipped"],
            "records_failed": counts["records_failed"],
            "high_water_mark": high_water,
            "error_message": errors[0]["error"] if errors else None,
            "error_details": {"errors": errors[:20]},
        },
    )
    # Source health: healthy / degraded / down (3 consecutive failures → down handled by caller count; here use status)
    health_status = {"success": "healthy", "partial_success": "degraded", "failed": "down"}.get(status, "unknown")
    try:
        store.upsert_source_health(connector.source_key, health_status, errors[0]["error"] if errors else None, 0 if status == "success" else 1)
    except Exception:
        pass
    logger.info(json.dumps({"source_key": connector.source_key, "run_id": run_id, "status": status, **counts, "duration_s": (finished - started).total_seconds()}))
    return {"run_id": run_id, "source_key": connector.source_key, "status": status, **counts, "high_water_mark": high_water, "errors": errors[:5]}


# Registry — import lazily to avoid circular imports
def _build_registry():
    from .connectors.county_auction import CountyAuctionConnector
    from .connectors.forsyth_legal_organ import ForsythLegalOrganConnector
    from .connectors.forsyth_qpublic import ForsythQPublicConnector
    from .connectors.fulton_assessor import FultonAssessorConnector
    from .connectors.fulton_legal_organ import FultonLegalOrganConnector
    from .connectors.gsccca_public import GSCCCAPublicConnector
    from .connectors.hud_reo import HUDREOConnector
    from .connectors.mls_pending import MLSPendingConnector

    return {
        "forsyth_legal_organ": ForsythLegalOrganConnector,
        "fulton_legal_organ": FultonLegalOrganConnector,
        "forsyth_qpublic": ForsythQPublicConnector,
        "fulton_assessor": FultonAssessorConnector,
        "gsccca_public": GSCCCAPublicConnector,
        "county_auction": CountyAuctionConnector,
        "hud_reo": HUDREOConnector,
        "mls_pending": MLSPendingConnector,
    }


CONNECTOR_REGISTRY = _build_registry()


def run_ingestion(source_key: str, mode: str = "incremental", settings: Settings | None = None, store: Store | None = None) -> dict:
    s = settings or get_settings()
    cls = CONNECTOR_REGISTRY[source_key]
    connector = cls(settings=s)
    st = store or SupabaseStore(s)
    return run_pipeline(connector, st, mode=mode)

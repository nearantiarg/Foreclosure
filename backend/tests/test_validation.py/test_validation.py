"""Validation: bad rows → records_failed, no row stored, never silently dropped."""
import pytest
from pydantic import ValidationError

from app.ingestion.connectors.forsyth_legal_organ import ForsythLegalOrganConnector
from app.ingestion.pipeline import run_pipeline
from app.schemas import DocumentRecord, ForeclosureNotice, Property


def test_property_requires_parcel():
    with pytest.raises(ValidationError):
        Property(parcel_id="")


def test_notice_requires_sale_date_source():
    with pytest.raises(ValidationError):
        ForeclosureNotice(source_name="x", source_url="", source_record_id="", sale_date=None)  # type: ignore


def test_document_future_recorded_date_rejected():
    from datetime import date, timedelta

    with pytest.raises(ValidationError):
        DocumentRecord(document_type="Deed", source_name="GSCCCA", recorded_date=date.today() + timedelta(days=10))


def test_negative_amount_rejected():
    with pytest.raises(ValidationError):
        ForeclosureNotice(source_name="x", source_url="https://example.test", source_record_id="1", sale_date="2025-11-04", original_loan_amount=-5)


class _BadConnector(ForsythLegalOrganConnector):
    def list_page_urls(self, mode="incremental", since=None):
        return ["https://example.test/bad"]

    def fetch_url(self, url, headers=None):
        return 200, "<html><body>NOTICE OF SALE UNDER POWER but no date</body></html>", {}

    def parse(self, html_or_text, page_url):
        # Force a raw row that will fail validation (missing sale_date)
        return [{"source_record_id": "bad-1"}]


def test_pipeline_counts_validation_failures(memory_store):
    c = _BadConnector()
    r = run_pipeline(c, memory_store, mode="full")
    assert r["records_failed"] >= 1, r
    assert r["records_inserted"] == 0

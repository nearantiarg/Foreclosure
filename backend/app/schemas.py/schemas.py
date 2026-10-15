"""Pydantic v2 schemas — canonical records + API shapes.

Georgia foreclosure law note (context only, not legal advice):
Georgia is non-judicial, power-of-sale. O.C.G.A. § 44-14-162 requires
advertisement once a week for 4 consecutive weeks before the sale.
Sales occur on the first Tuesday of the month (or next business day if a
legal holiday) at the courthouse. ALWAYS take sale_date from the published
notice — never compute/infer it.

Validation rules (enforced here, counted as failures in ingestion — never
silently dropped):
- Property: parcel_id required.
- Notice: sale_date, source_url, source_record_id required.
- Auction: sale_date, sale_location required.
- Document: recorded_date must not be > today + 1 day.
- Amounts must be >= 0 where present.
"""
from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------- Shared ----------
class Provenance(BaseModel):
    source_name: str
    source_url: str | None = None
    retrieved_at: datetime | None = None
    first_seen_at: datetime | None = None


class ErrorResponse(BaseModel):
    detail: str
    code: str
    run_id: str | None = None


class PaginatedMeta(BaseModel):
    page: int
    per_page: int
    total: int | None = None
    has_more: bool = False


def _non_negative(cls, v: Decimal | None) -> Decimal | None:
    if v is not None and v < 0:
        raise ValueError("amount must be >= 0")
    return v


# ---------- Counties ----------
class County(BaseModel):
    id: UUID | None = None
    county_name: str
    county_fips: str  # Forsyth 117, Fulton 121
    state: str = "GA"
    legal_organ_name: str | None = None
    legal_organ_url: str | None = None
    assessor_url: str | None = None
    tax_commissioner_url: str | None = None
    clerk_url: str | None = None
    gsccca_county_code: str | None = None
    is_active: bool = True
    created_at: datetime | None = None


# ---------- Properties ----------
class Property(BaseModel):
    id: UUID | None = None
    county_id: UUID | None = None
    county_name: str | None = None
    parcel_id: str = Field(..., min_length=1)
    parcel_id_normalized: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str = "GA"
    zip: str | None = None
    owner_name: str | None = None  # as published in public record
    property_type: str | None = None
    year_built: int | None = None
    living_area_sqft: Decimal | None = None
    lot_acres: Decimal | None = None
    bedrooms: int | None = None
    bathrooms: Decimal | None = None
    assessed_value: Decimal | None = None
    appraised_value: Decimal | None = None
    tax_year: int | None = None
    centroid_lng: float | None = None
    centroid_lat: float | None = None
    assessor_url: str | None = None
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    content_hash: str | None = None
    provenance: Provenance | None = None

    @model_validator(mode="after")
    def _fill_normalized(self) -> "Property":
        if not self.parcel_id_normalized:
            import re

            self.parcel_id_normalized = re.sub(r"[^A-Z0-9]", "", self.parcel_id.upper())
        return self

    _check_non_negative = field_validator("assessed_value", "appraised_value", "living_area_sqft", "lot_acres")(classmethod(_non_negative))


class PropertyDetail(Property):
    notices: list["ForeclosureNotice"] = []
    auctions: list["AuctionEvent"] = []
    events: list["PropertyEvent"] = []
    documents: list["DocumentRecord"] = []
    comparable_sales: list["ComparableSale"] = []


# ---------- Foreclosure notices ----------
class ForeclosureNotice(BaseModel):
    id: UUID | None = None
    property_id: UUID | None = None
    county_id: UUID | None = None
    county_name: str | None = None
    source_name: str
    source_url: str = Field(..., min_length=1)
    source_record_id: str = Field(..., min_length=1)
    notice_type: str = "Notice of Sale Under Power"
    grantor_name: str | None = None
    grantee_name: str | None = None
    original_loan_amount: Decimal | None = None
    deed_book: str | None = None
    deed_page: str | None = None
    instrument_number: str | None = None
    legal_description: str | None = None
    parcel_id: str | None = None  # as printed in notice, for matching
    # Sale date MUST come from the published notice. Never computed.
    sale_date: date
    sale_location: str | None = None
    publication_start_date: date | None = None
    publication_end_date: date | None = None
    publication_weeks: int | None = None
    notice_text: str | None = None
    status: str = "published"
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    content_hash: str | None = None
    provenance: Provenance | None = None

    _check_non_negative = field_validator("original_loan_amount")(classmethod(_non_negative))


# ---------- Auction events ----------
class AuctionEvent(BaseModel):
    id: UUID | None = None
    county_id: UUID | None = None
    county_name: str | None = None
    property_id: UUID | None = None
    notice_id: UUID | None = None
    sale_date: date
    sale_time: time | None = None
    sale_location: str = Field(..., min_length=1)
    sale_type: str = "foreclosure"  # foreclosure | tax_sale | sheriff_sale | REO_auction
    status: str = "scheduled"
    opening_bid: Decimal | None = None
    winning_bid: Decimal | None = None
    buyer_name: str | None = None
    result_source_url: str | None = None
    result_retrieved_at: datetime | None = None
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    content_hash: str | None = None
    provenance: Provenance | None = None

    _check_non_negative = field_validator("opening_bid", "winning_bid")(classmethod(_non_negative))


class UpcomingAuctions(BaseModel):
    sale_date: date
    county_name: str | None = None
    county_fips: str | None = None
    count: int
    auctions: list[AuctionEvent] = []


# ---------- Property events ----------
class PropertyEvent(BaseModel):
    id: UUID | None = None
    property_id: UUID
    event_type: str
    event_date: date
    title: str
    description: str | None = None
    source_name: str | None = None
    source_url: str | None = None
    payload: dict[str, Any] | None = None
    created_at: datetime | None = None


# ---------- Document records ----------
class DocumentRecord(BaseModel):
    id: UUID | None = None
    property_id: UUID | None = None
    county_id: UUID | None = None
    instrument_number: str | None = None
    deed_book: str | None = None
    deed_page: str | None = None
    document_type: str
    grantor_name: str | None = None
    grantee_name: str | None = None
    recorded_date: date | None = None
    consideration_amount: Decimal | None = None
    source_name: str
    source_url: str | None = None
    source_record_id: str | None = None
    content_hash: str | None = None
    provenance: Provenance | None = None

    @field_validator("recorded_date")
    @classmethod
    def _not_far_future(cls, v: date | None) -> date | None:
        if v is not None:
            from datetime import timedelta

            if v > date.today() + timedelta(days=1):
                raise ValueError("recorded_date must not be in the future")
        return v

    _check_non_negative = field_validator("consideration_amount")(classmethod(_non_negative))


# ---------- Comparable sales (real only) ----------
class ComparableSale(BaseModel):
    id: UUID | None = None
    subject_property_id: UUID
    comp_property_id: UUID | None = None
    comp_address: str
    sale_date: date
    sale_price: Decimal = Field(..., ge=0)
    distance_miles: Decimal | None = None
    similarity_score: Decimal | None = None
    source_name: str
    source_url: str | None = None
    source_record_id: str | None = None
    license_status: str = "public"  # public | PENDING_LICENSE
    created_at: datetime | None = None
    provenance: Provenance | None = None


# ---------- Ingestion / sources ----------
class Source(BaseModel):
    id: UUID | None = None
    source_key: str
    display_name: str
    county_id: UUID | None = None
    source_type: str
    base_url: str
    is_enabled: bool = True
    license_status: str = "public"  # public | PENDING_LICENSE | PENDING_APPROVAL
    expected_cadence: str | None = None
    last_successful_run_at: datetime | None = None
    notes: str | None = None


class SourceHealth(BaseModel):
    source_id: UUID | None = None
    source_key: str | None = None
    status: str = "unknown"  # healthy | degraded | down | pending_license | unknown
    last_check_at: datetime | None = None
    consecutive_failures: int = 0
    last_error: str | None = None
    updated_at: datetime | None = None


class IngestionRun(BaseModel):
    id: UUID | None = None
    source_id: UUID | None = None
    source_key: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    status: str  # running | success | partial_success | failed
    pages_fetched: int = 0
    records_seen: int = 0
    records_inserted: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    records_failed: int = 0
    high_water_mark: str | None = None
    error_message: str | None = None
    error_details: dict[str, Any] | None = None
    triggered_by: str = "scheduled"


class IngestionTriggerRequest(BaseModel):
    source_key: str
    mode: Literal["incremental", "full"] = "incremental"
    since: date | None = None
    max_pages: int | None = None


class LicenseRequiredError(Exception):
    """Raised by PENDING_LICENSE connectors. Carries no records."""

    def __init__(self, source_key: str, message: str = "License / approval required"):
        super().__init__(message)
        self.source_key = source_key
        self.message = message

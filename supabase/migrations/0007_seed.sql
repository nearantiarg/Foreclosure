-- Migration 0007: Seed — counties + sources registry ONLY
-- DATA-FIRST RULE: Seed ONLY 2 counties + source registry rows.
-- NO fake properties, NO fake notices, NO fake auctions, NO fake comps.
-- Production tables properties / foreclosure_notices / auction_events /
-- property_events / document_records / comparable_sales remain EMPTY after
-- seed. They fill only via real ingestion.
--
-- Idempotent-safe: ON CONFLICT DO NOTHING / DO UPDATE for counties and
-- sources, keyed on natural uniques (county_fips, source_key). Re-running
-- this migration must not duplicate rows.
--
-- Down reasoning: deleting seed rows would orphan any ingested data that
-- references them. Manual rollback with backup only.

-- ---------------------------------------------------------------------------
-- Counties: Forsyth (FIPS 117) + Fulton (FIPS 121), GA.
-- URLs are the official public entry points documented in docs/DATA_SOURCES.md.
-- If a URL moves, update it here AND in docs/DATA_SOURCES.md — never invent one.
-- ---------------------------------------------------------------------------
insert into public.counties
  (county_name, county_fips, state, legal_organ_name, legal_organ_url,
   assessor_url, tax_commissioner_url, clerk_url, gsccca_county_code, is_active)
values
  (
    'Forsyth', '117', 'GA',
    'Forsyth County News',
    'https://www.forsythnews.com/',
    'https://qpublic.schneidercorp.com/application.aspx?app=ForsythCountyGA&layer=Parcels&PageType=Search',
    'https://www.forsythco.com/Departments-Offices/Tax-Commissioner',
    'https://www.forsythco.com/Departments-Offices/Clerk-of-Superior-Court',
    'FOR',
    true
  ),
  (
    'Fulton', '121', 'GA',
    'Daily Report (Fulton legal organ)',
    'https://www.law.com/dailyreportonline/',
    'https://www.fultoncountyga.gov/inside-fulton-county/fulton-county-departments/board-of-assessors',
    'https://www.fultoncountyga.gov/inside-fulton-county/fulton-county-departments/tax-commissioner',
    'https://www.fultoncountyga.gov/inside-fulton-county/fulton-county-departments/clerk-of-superior-and-magistrate-courts',
    'FUL',
    true
  )
on conflict (county_fips) do update set
  county_name = excluded.county_name,
  legal_organ_name = excluded.legal_organ_name,
  legal_organ_url = excluded.legal_organ_url,
  assessor_url = excluded.assessor_url,
  tax_commissioner_url = excluded.tax_commissioner_url,
  clerk_url = excluded.clerk_url,
  gsccca_county_code = excluded.gsccca_county_code,
  is_active = excluded.is_active,
  updated_at = now();

-- ---------------------------------------------------------------------------
-- Sources registry.
-- county_id is resolved via subquery on county_fips (stable, no hardcoded UUIDs).
-- license_status: 'public' for sources we ingest from public pages;
--   'PENDING_LICENSE' for MLS / proprietary feeds (interface only, no rows).
-- expected_cadence follows the spec: daily for assessor/GSCCCA, daily during
-- the 4-week publication window for legal organs, first_tuesday_cycle for auctions.
-- ---------------------------------------------------------------------------

-- Forsyth legal organ
insert into public.sources
  (source_key, display_name, county_id, source_type, base_url, is_enabled, license_status, expected_cadence, notes)
values
  (
    'forsyth_legal_organ', 'Forsyth County News — Legal Notices',
    (select id from public.counties where county_fips = '117'),
    'legal_organ', 'https://www.forsythnews.com/',
    true, 'public', 'daily',
    'Notice of Sale Under Power. Public web. Dedupe (county, source_name, source_record_id).'
  )
on conflict (source_key) do nothing;

-- Fulton legal organ
insert into public.sources
  (source_key, display_name, county_id, source_type, base_url, is_enabled, license_status, expected_cadence, notes)
values
  (
    'fulton_legal_organ', 'Daily Report — Fulton Legal Notices',
    (select id from public.counties where county_fips = '121'),
    'legal_organ', 'https://www.law.com/dailyreportonline/',
    true, 'public', 'daily',
    'Fulton legal organ. May be paywalled — if blocked, mark degraded, do NOT scrape around paywall or invent notices.'
  )
on conflict (source_key) do nothing;

-- Forsyth qPublic (assessor)
insert into public.sources
  (source_key, display_name, county_id, source_type, base_url, is_enabled, license_status, expected_cadence, notes)
values
  (
    'forsyth_qpublic', 'Forsyth County qPublic — Tax Assessors',
    (select id from public.counties where county_fips = '117'),
    'assessor', 'https://qpublic.schneidercorp.com/application.aspx?app=ForsythCountyGA&layer=Parcels&PageType=Search',
    true, 'public', 'daily',
    'Parcel records: parcel_id, owner, address, type, year built, sqft, lot, values. Parcel-by-parcel fetch driven by notices + backfill.'
  )
on conflict (source_key) do nothing;

-- Fulton assessor
insert into public.sources
  (source_key, display_name, county_id, source_type, base_url, is_enabled, license_status, expected_cadence, notes)
values
  (
    'fulton_assessor', 'Fulton County Board of Assessors',
    (select id from public.counties where county_fips = '121'),
    'assessor', 'https://www.fultoncountyga.gov/inside-fulton-county/fulton-county-departments/board-of-assessors',
    true, 'public', 'daily',
    'Parcel records. Fulton parcel ID format differs from Forsyth — normalize per county in connector config.'
  )
on conflict (source_key) do nothing;

-- GSCCCA — Forsyth (public search)
insert into public.sources
  (source_key, display_name, county_id, source_type, base_url, is_enabled, license_status, expected_cadence, notes)
values
  (
    'gsccca_forsyth', 'GSCCCA — Forsyth County Real Estate Index (Public Search)',
    (select id from public.counties where county_fips = '117'),
    'clerk_gsccca', 'https://www.gsccca.org/',
    true, 'public', 'daily',
    'Instrument index: deeds, security deeds, foreclosure deeds, liens. Public search where feasible; bulk/API is PENDING_LICENSE (see gsccca_bulk).'
  )
on conflict (source_key) do nothing;

-- GSCCCA — Fulton (public search)
insert into public.sources
  (source_key, display_name, county_id, source_type, base_url, is_enabled, license_status, expected_cadence, notes)
values
  (
    'gsccca_fulton', 'GSCCCA — Fulton County Real Estate Index (Public Search)',
    (select id from public.counties where county_fips = '121'),
    'clerk_gsccca', 'https://www.gsccca.org/',
    true, 'public', 'daily',
    'Instrument index. Public search where feasible; bulk/API is PENDING_LICENSE (see gsccca_bulk).'
  )
on conflict (source_key) do nothing;

-- Forsyth auction / First Tuesday sale list
insert into public.sources
  (source_key, display_name, county_id, source_type, base_url, is_enabled, license_status, expected_cadence, notes)
values
  (
    'forsyth_auction', 'Forsyth County First Tuesday Sale List',
    (select id from public.counties where county_fips = '117'),
    'tax_sale', 'https://www.forsythco.com/Departments-Offices/Clerk-of-Superior-Court',
    true, 'public', 'first_tuesday_cycle',
    'Scheduled sale date, location, parcel list, postponements/cancellations where published. PDF lists parsed where published.'
  )
on conflict (source_key) do nothing;

-- Fulton auction / First Tuesday sale list
insert into public.sources
  (source_key, display_name, county_id, source_type, base_url, is_enabled, license_status, expected_cadence, notes)
values
  (
    'fulton_auction', 'Fulton County First Tuesday Sale List',
    (select id from public.counties where county_fips = '121'),
    'tax_sale', 'https://www.fultoncountyga.gov/inside-fulton-county/fulton-county-departments/clerk-of-superior-and-magistrate-courts',
    true, 'public', 'first_tuesday_cycle',
    'Scheduled sale date, location, parcel list, postponements/cancellations where published.'
  )
on conflict (source_key) do nothing;

-- HUD REO (statewide, filtered to Forsyth/Fulton in connectors)
insert into public.sources
  (source_key, display_name, county_id, source_type, base_url, is_enabled, license_status, expected_cadence, notes)
values
  (
    'hud_reo', 'HUD HomeStore / Fannie Mae HomePath / Freddie Mac HomeSteps (REO)',
    null,
    'reo', 'https://www.hudhomestore.gov/',
    true, 'public', 'daily',
    'REO listings genuinely for sale. Stored as auction_events sale_type=REO_auction. NEVER mixed into foreclosure counts.'
  )
on conflict (source_key) do nothing;

-- MLS comps — PENDING_LICENSE (interface only, no rows)
insert into public.sources
  (source_key, display_name, county_id, source_type, base_url, is_enabled, license_status, expected_cadence, notes)
values
  (
    'mls_pending', 'MLS / FMLS Comparable Sales (PENDING_LICENSE)',
    null,
    'mls_pending', 'https://www.fmls.com/',
    false, 'PENDING_LICENSE', 'daily',
    'Connector interface + comparable_sales table + UI shell only. No records until license granted. Never show fake comps.'
  )
on conflict (source_key) do nothing;

-- Proprietary foreclosure feeds — PENDING_LICENSE (interface only, no rows)
insert into public.sources
  (source_key, display_name, county_id, source_type, base_url, is_enabled, license_status, expected_cadence, notes)
values
  (
    'auction_proprietary', 'Auction.com / RealtyTrac Proprietary Feeds (PENDING_LICENSE)',
    null,
    'proprietary_pending', 'https://www.auction.com/',
    false, 'PENDING_LICENSE', 'daily',
    'Interface + PENDING_LICENSE badge only. No scraping around login walls. No records until licensed.'
  )
on conflict (source_key) do nothing;

-- GSCCCA bulk/API — PENDING_LICENSE (interface only)
insert into public.sources
  (source_key, display_name, county_id, source_type, base_url, is_enabled, license_status, expected_cadence, notes)
values
  (
    'gsccca_bulk', 'GSCCCA Bulk / API (PENDING_LICENSE)',
    null,
    'clerk_gsccca', 'https://www.gsccca.org/',
    false, 'PENDING_LICENSE', 'daily',
    'Bulk/API connector interface only. Public-search connectors (gsccca_forsyth/fulton) are the live path until bulk is approved.'
  )
on conflict (source_key) do nothing;

-- ---------------------------------------------------------------------------
-- Seed verification (informational; does not create data):
--   select count(*) from counties;                 -- expect 2
--   select count(*) from sources;                  -- expect 12
--   select count(*) from properties;               -- expect 0
--   select count(*) from foreclosure_notices;      -- expect 0
--   select count(*) from auction_events;           -- expect 0
--   select count(*) from comparable_sales;         -- expect 0
-- ---------------------------------------------------------------------------

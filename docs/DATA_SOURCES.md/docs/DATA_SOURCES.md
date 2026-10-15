# DATA_SOURCES.md — Georgia Foreclosure Platform

Every source the platform ingests (or is built to ingest once licensed). **No source produces invented records.** If a source is blocked, paywalled, or pending license, the connector records the failure / pending status and the UI shows an honest empty or pending state.

**Status values:** `live` = connector implemented and ingesting real records · `scaffolded` = registry row exists, connector pending (M2+) · `pending_license` = interface + UI shell only, zero records until licensed · `blocked` = access blocked; connector + degraded health, no workaround scraping.

## Launch sources (Forsyth + Fulton)

| # | Source | County | What it publishes | Access / auth | Cadence | Pagination | Dedupe key | Status |
|---|--------|--------|-------------------|---------------|---------|------------|------------|--------|
| 1 | Forsyth County News — Legal Notices (`forsyth_legal_organ`) — https://www.forsythnews.com/ | Forsyth (117) | Notice of Sale Under Power: text, publication dates, sale date, grantor/grantee, deed book/page | Public web; no auth | Daily (daily during 4-week publication window) | `?page=N` / next-link; stop on empty page / no new IDs / 404 | `(county_id, source_name, source_record_id)` where `source_record_id` = notice URL or notice hash | `scaffolded` |
| 2 | Daily Report — Fulton Legal Notices (`fulton_legal_organ`) — https://www.law.com/dailyreportonline/ | Fulton (121) | Same as #1 for Fulton | Public web; may be paywalled — if blocked, mark degraded, do NOT scrape around paywall | Daily | Search filters + pagination; same stop conditions | `(county_id, source_name, source_record_id)` | `scaffolded` |
| 3 | Forsyth County qPublic — Tax Assessors (`forsyth_qpublic`) — https://qpublic.schneidercorp.com/application.aspx?app=ForsythCountyGA&layer=Parcels&PageType=Search | Forsyth (117) | Parcel record: parcel_id, owner, address, property type, year built, sqft, lot, assessed/appraised values, tax year | Public parcel search; no auth | Daily | Parcel-by-parcel fetch driven by parcels from notices + bounded county parcel-list backfill | `(county_id, parcel_id_normalized)` | `scaffolded` |
| 4 | Fulton County Board of Assessors (`fulton_assessor`) — https://www.fultoncountyga.gov/inside-fulton-county/fulton-county-departments/board-of-assessors | Fulton (121) | Same parcel fields as #3 | Public; no auth | Daily | Same as #3. Fulton parcel ID format differs — normalize per county in connector config | `(county_id, parcel_id_normalized)` | `scaffolded` |
| 5a | GSCCCA — Forsyth Public Search (`gsccca_forsyth`) — https://www.gsccca.org/ | Forsyth (117) | Instrument index: deed / security deed / foreclosure deed / lien, book/page, parties, recorded date | Public search; no auth | Daily | Search-result pagination | `(county_id, source_name, source_record_id)` | `scaffolded` |
| 5b | GSCCCA — Fulton Public Search (`gsccca_fulton`) — https://www.gsccca.org/ | Fulton (121) | Same as 5a for Fulton | Public search; no auth | Daily | Search-result pagination | `(county_id, source_name, source_record_id)` | `scaffolded` |
| 6a | Forsyth County First Tuesday Sale List (`forsyth_auction`) — via Clerk of Superior Court — https://www.forsythco.com/Departments-Offices/Clerk-of-Superior-Court | Forsyth (117) | Scheduled sale date, location, parcel list, postponements/cancellations where published | Public pages/PDFs; no auth | `first_tuesday_cycle` | Page / PDF list; one list per sale date | Pipeline dedupe (property + notice + sale date); partial unique index for linked case | `scaffolded` |
| 6b | Fulton County First Tuesday Sale List (`fulton_auction`) — via Clerk — https://www.fultoncountyga.gov/inside-fulton-county/fulton-county-departments/clerk-of-superior-and-magistrate-courts | Fulton (121) | Same as 6a for Fulton | Public pages/PDFs; no auth | `first_tuesday_cycle` | Page / PDF list; one list per sale date | Same as 6a | `scaffolded` |
| 7 | HUD HomeStore / Fannie Mae HomePath / Freddie Mac HomeSteps — REO (`hud_reo`) — https://www.hudhomestore.gov/ | Statewide, filtered to Forsyth/Fulton | REO listings genuinely for sale (address, list price, status) | Public listings; no auth | Daily | Search-result pagination | `(county_id, source_name, source_record_id)` | `scaffolded` |

**REO rule:** REO rows are stored as `auction_events` with `sale_type='REO_auction'` and are NEVER mixed into foreclosure counts.

## Pending-license sources — interface + UI shell only, ZERO records

| Source | County | What it would publish | Access / auth | Cadence | Pagination | Dedupe key | Status |
|--------|--------|----------------------|---------------|---------|------------|------------|--------|
| MLS / FMLS Comparable Sales (`mls_pending`) — https://www.fmls.com/ | Statewide | Comparable sales (price, date, distance, similarity) | License required | Daily (once licensed) | API pagination | `(subject_property_id, source_name, source_record_id)` | `pending_license` |
| Auction.com / RealtyTrac Proprietary Feeds (`auction_proprietary`) — https://www.auction.com/ | Statewide | Proprietary foreclosure / auction feeds | License / subscription required; no scraping around login walls | Daily (once licensed) | API pagination | `(county_id, source_name, source_record_id)` | `pending_license` |
| GSCCCA Bulk / API (`gsccca_bulk`) — https://www.gsccca.org/ | Statewide | Bulk instrument index (same fields as 5a/5b, bulk) | Subscription / approval required | Daily (once approved) | Bulk cursor / API pagination | `(county_id, source_name, source_record_id)` | `pending_license` |

**Pending-license rule:** When `sources.license_status = 'PENDING_LICENSE'`, the connector returns a `license_required` signal and produces no rows. The UI shows "Comparable sales via MLS — pending license" (or equivalent) instead of fake comps. The `comparable_sales` table stays empty until licensed/public sale data exists.

## Source registry (seed)

`supabase/migrations/0007_seed.sql` inserts 12 `sources` rows: the 9 live/scaffolded sources above (Forsyth/Fulton legal organs, qPublic, Fulton assessor, 2× GSCCCA public, 2× auction, HUD REO) + 3 pending-license rows (MLS, proprietary, GSCCCA bulk). `is_enabled=false` for all pending-license rows.

## Georgia foreclosure specifics

- Non-judicial, power-of-sale. Advertisement once a week for 4 consecutive weeks before sale (O.C.G.A. § 44-14-162).
- Sales on the first Tuesday of the month (or next business day if a legal holiday) at the courthouse, typically the courthouse steps.
- `sale_date` is always taken from the published notice — never computed from `first_tuesday_of_month()`.
- If a sale result is not published, status is `unknown` / `result not yet published`.

## Keeping this doc current

When a connector ships, update that row's Status to `live` and note the first successful `ingestion_runs` id/date. When a source blocks access, set Status to `blocked`, record the block in `ingestion_runs.error_details` + `source_health.last_error`, and update this doc with the block reason and date. Never delete a source row — history matters.

# ADDING_A_COUNTY.md — Expansion to All 159 Georgia Counties

The platform is config-driven: **adding a county must be config rows + verified connectors, not a rewrite.** County is always a parameter in the pipeline, API, and frontend. If adding a county requires a code change to pipeline/API/frontend, that is a bug — fix the abstraction, then add the county.

## Current state

- Active at launch: Forsyth (FIPS 117) + Fulton (FIPS 121).
- All other Georgia counties: NOT yet in the `counties` table. M7 adds the full 159-county registry with `is_active=false` except Forsyth/Fulton until verified.

## Checklist — one county at a time

### 1. Research (no code yet)
- [ ] Confirm the county's 3-digit FIPS code (verify against Census / Georgia DCA, don't guess).
- [ ] Identify the county's **legal organ** (newspaper designated for legal advertisements) — name + URL.
- [ ] Identify the **tax assessor / qPublic** entry point — URL + parcel-ID format.
- [ ] Identify the **tax commissioner** URL (tax sale lists).
- [ ] Identify the **Clerk of Superior Court** URL (First Tuesday sale lists, deeds).
- [ ] Identify the **GSCCCA county code** for the county.
- [ ] Record all URLs in this checklist (in the PR description) and in `docs/DATA_SOURCES.md`.

### 2. Config rows (DB)
- [ ] Insert `counties` row with `is_active=false` (do NOT activate until step 5 passes).
  ```sql
  insert into public.counties
    (county_name, county_fips, state, legal_organ_name, legal_organ_url,
     assessor_url, tax_commissioner_url, clerk_url, gsccca_county_code, is_active)
  values ('<Name>', '<FFF>', 'GA', '<Legal organ>', '<URL>', '<Assessor URL>',
          '<Tax commissioner URL>', '<Clerk URL>', '<GSCCCA code>', false);
  ```
- [ ] Insert `sources` rows for the county (at minimum: `<county>_legal_organ`, `<county>_assessor`, `<county>_auction`, `gsccca_<county>`), each with:
  - `source_key` following the `<county_slug>_<kind>` convention (lowercase, underscores).
  - `county_id` = the new county's id (resolve via subquery on `county_fips`, never hardcode a UUID).
  - Correct `source_type`, `base_url`, `license_status` (`public` or `PENDING_LICENSE`), `expected_cadence`, `is_enabled` (false until verified, true after).
- [ ] Verify: `select * from counties where county_fips='<FFF>';` and `select * from sources where county_id=(select id from counties where county_fips='<FFF>');`

### 3. Connectors (backend)
- [ ] If the county uses the same source platform as an existing county (e.g. qPublic, same legal-organ CMS), reuse the existing connector class with per-county config (URLs + parcel-ID normalization + selectors). Do NOT copy-paste a connector and hardcode the new county.
- [ ] If the county uses a new platform/format, add ONE new connector class inheriting `BaseConnector` (`fetch_page`, `parse`, `normalize`, `dedupe_key`, `high_water_mark`). No connector writes SQL directly — it yields normalized Pydantic models.
- [ ] Parcel-ID normalization: implement per-county in connector config (Fulton vs. Forsyth formats differ — this is the pattern, not an exception).
- [ ] Pagination: handle the county source's pagination (page param / cursor / next-link) with `max_pages` cap + stop conditions.
- [ ] Dedupe: `(county_id, source_name, source_record_id)` for notices/documents; `(county_id, parcel_id_normalized)` for properties.
- [ ] Add parser fixtures under `backend/tests/fixtures/` from REAL sample pages for the new county (labeled as fixtures, never served as production data) + a dedupe/pagination test for the new connector.
- [ ] Document the new connector in `docs/DATA_SOURCES.md` (new rows in the launch-sources table pattern).

### 4. Bounded verification ingestion
- [ ] Run a bounded ingestion for the new county's sources, one at a time:
  `POST /ingestion/run?source_key=<county>_legal_organ&mode=incremental` (or bounded backfill with date window + `max_pages`).
- [ ] Check `ingestion_runs`: status `success` / `partial_success`, pages fetched, records seen/inserted/skipped/failed. Investigate any `failed` rows before proceeding.
- [ ] Check canonical tables: `properties`, `foreclosure_notices`, `auction_events` contain ONLY real records from the new county's sources, each with `source_url` + provenance.
- [ ] Check matching: notices link to properties where parcel/address matches; unmatched notices show "Property match pending" (never a fake property).
- [ ] Check `source_health` for the new county's sources: `healthy` (or `degraded`/`down` with a documented reason — never hidden).
- [ ] Check the frontend: `/properties?county=<Name>`, `/auctions?county=<Name>`, `/map` bbox, and `/sources` all show the new county correctly with no hardcoded Forsyth/Fulton logic.

### 5. Activate
- [ ] Only after step 4 passes: `update counties set is_active=true where county_fips='<FFF>';`
- [ ] Set the new `sources` rows to `is_enabled=true` (except any `PENDING_LICENSE` rows, which stay disabled).
- [ ] Update `docs/DATA_SOURCES.md` status for the new county's sources to `live`.
- [ ] Add the county to the milestone/PR notes. Commit per county (one county per PR).

### 6. If the county's sources are blocked / paywalled / license-gated
- [ ] Do NOT scrape around a block or invent records.
- [ ] Record the block in `ingestion_runs.error_details` + `source_health.last_error`.
- [ ] Set the affected `sources` row to the correct `license_status` (`PENDING_LICENSE` / `PENDING_APPROVAL`) and document it in `docs/DATA_SOURCES.md` (Status → `blocked` or `pending_license`, date, reason).
- [ ] Leave the county `is_active=false` until at least one real source is verified. A county with zero verified sources stays inactive.

## M7 — full 159-county registry

M7 adds all 159 Georgia counties to `counties` with `is_active=false` (except Forsyth/Fulton) + per-county connector config placeholders. That migration is registry-only (no fake data). Counties are then activated one by one via the checklist above. Demonstrate M7 by activating ONE additional county end-to-end (pick the county with the most accessible public sources, document which one + why).

## Anti-patterns (do not do)

- Hardcoding `where county_fips in ('117','121')` in pipeline/API/frontend.
- Copy-pasting a connector per county instead of config-driven reuse.
- Activating a county with zero verified sources.
- Backfilling unbounded to "fill" a new county's pages.
- Inventing a legal-organ / assessor URL — if you cannot verify the URL from an official source, leave it NULL and document the gap.

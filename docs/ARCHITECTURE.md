# ARCHITECTURE.md — Georgia Foreclosure Intelligence Platform

## Goal

One working, data-first platform for Georgia foreclosure records: real property records, verified foreclosure notices, auction events, historical changes, and comparable sales where licensed or publicly available. No mock listings, no hardcoded statistics, no simulated API responses.

## System diagram

```
Public sources (legal organs, GSCCCA public search, qPublic/assessor,
                county sale lists, HUD/Fannie/Freddie REO)
  │  HTTP fetch / CSV / HTML / PDF parsing
  │  Respect robots.txt + rate limits (1–2s between pages per source),
  │  httpx timeout 30s, 3 attempts with exponential backoff on 429/5xx,
  │  respect Retry-After. One source failing must not block others.
  ▼
FastAPI Ingestion Workers — /backend (separate agent owns)
  │  One connector class per source, all through a shared pipeline:
  │  fetch → store raw_payloads → parse → normalize (Pydantic) →
  │  validate → dedupe (natural key + content_hash) → upsert →
  │  update high-water mark → record ingestion_runs + source_health
  │  Matching: notice → property by (county, parcel_id_normalized),
  │  else normalized address + owner fuzzy match above threshold;
  │  low-confidence matches logged for review, never auto-linked.
  ▼
Supabase PostgreSQL 15 + PostGIS — source of truth
  │  Canonical: counties, properties, foreclosure_notices, auction_events,
  │  property_events (append-only), document_records, comparable_sales, watchlist
  │  Ops: sources, ingestion_runs, raw_payloads, source_health
  │  RLS on every table. service_role-only writes (via backend).
  ▼
FastAPI Analytics API + Supabase direct reads
  │  FastAPI: /health, /ready, /health/sources, /counties, /properties,
  │  /properties/{id}, /notices, /auctions, /auctions/upcoming,
  │  /analytics/overview, /analytics/county/{fips}/trend,
  │  POST /ingestion/run, GET /ingestion/runs, GET /sources
  │  Analytics = live COUNT(*) / aggregations over real tables. No cached fake stats.
  │  Next.js reads simple lists via Supabase (RLS) or via FastAPI for analytics.
  ▼
Next.js Frontend — /frontend (separate agent owns)
     / (live overview), /properties, /properties/[id], /auctions,
     /map (PostGIS GeoJSON), /sources (health dashboard),
     /watchlist (auth, RLS), /admin/ingestion (admin-gated)
```

## Why this stack

| Choice | Why |
|--------|-----|
| Supabase PostgreSQL + PostGIS | Managed Postgres, RLS, Auth, Storage in one place; PostGIS gives true geo queries (bbox, distance, intersects) without a second geo store. |
| FastAPI (Python) for ingestion + analytics | Best ecosystem for HTML/PDF parsing, Pydantic validation, async HTTP, and data pipelines. One language for ingestion + analytics keeps the pipeline coherent. |
| Next.js App Router + TypeScript + Tailwind | Server Components by default (no service-role key in browser), strict types, fast iteration, accessible + responsive UI. |
| MapLibre GL JS / Leaflet | Open-source map, OSM/Carto basemap with attribution, no paid map key required for core functionality. |
| GitHub Actions cron for scheduling | No extra scheduler infra; `POST /ingestion/run` per source with `INGESTION_SECRET`; manual dispatch for backfills. Fallback: Supabase `pg_cron` + secured Edge Function (documented in RUNBOOK). |

## Data model (summary)

See migrations in `supabase/migrations/` for the authoritative schema. Key ideas:

- **Natural keys + dedupe:** `properties` → `(county_id, parcel_id_normalized)`; `foreclosure_notices` / `document_records` → `(county_id, source_name, source_record_id)`; `auction_events` → partial unique for the fully-linked case + pipeline dedupe in code (NULLs defeat Postgres unique indexes). Every row carries `content_hash` — unchanged hash on re-ingest → `records_skipped += 1`, update `last_seen_at` only; changed hash → update + append a `property_events` row describing the change.
- **Raw archive first:** `raw_payloads` stores the raw fetched payload (or Storage path) with hash + URL + fetched_at BEFORE parsing. Parsing failures never lose evidence.
- **Incremental:** Each connector tracks `sources.last_successful_run_at` + a high-water mark (last notice date / instrument / page cursor). Full re-scrapes are manual/backfill only, behind a flag, with a bounded date window + `max_pages` cap.
- **Pagination:** Every connector loops `while next_page and pages_fetched < max_pages`, handling `?page=N`, cursor tokens, and "next" links; stops on empty page / no new IDs / 404.
- **Append-only history:** `property_events` is insert-only. Never update/delete in normal operation.
- **Provenance:** Every property/notice/auction response includes `provenance: { source_name, source_url, retrieved_at / first_seen_at }`.
- **No invented geometry:** `centroid` / `boundary` are NULL when not published. Map renders only real geometry.

## Security

- `SUPABASE_SERVICE_ROLE_KEY` + `SUPABASE_DB_URL`: server-side only (FastAPI, Next.js Server Components / Route Handlers, GitHub Actions secrets). Never in client bundles, `NEXT_PUBLIC_*`, logs, or git.
- Browser code uses only `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_ANON_KEY` and relies on RLS.
- `POST /ingestion/run` is protected by `X-Ingestion-Secret` / service-role auth; never open to anon. The ingestion secret is never exposed to the browser.
- RLS: public tables → anon + authenticated read, service-role-only write. `watchlist` → user-scoped (`user_id = auth.uid()`). `raw_payloads` → service-role only. `FORCE RLS` on all tables.
- `.env` / `.env.local` are gitignored. `.env.example` lists all vars with empty values.

## Georgia foreclosure specifics encoded in the platform

- Non-judicial, power-of-sale; advertisement once a week for 4 consecutive weeks before sale (O.C.G.A. § 44-14-162).
- Sales on the **first Tuesday** of the month (or next business day if a legal holiday) at the courthouse, typically the courthouse steps.
- `sale_date` is ALWAYS taken from the published notice — never computed. `first_tuesday_of_month()` in migration 0008 is a display/filter helper only.
- If a sale result is not published, status is `unknown` / `result not yet published` — never inferred.
- REO listings (`sale_type='REO_auction'`) are never mixed into foreclosure counts.
- Footer disclaimer on every page: "Public-record information only; not legal advice. Verify with the county clerk / legal organ before acting."

## County expansion

County is always a parameter — never hardcoded "Forsyth/Fulton only" in pipeline, API, or frontend. Adding a county = config rows (`counties` + `sources`) + verified connectors. See `docs/ADDING_A_COUNTY.md`.

## Testing

- Backend `pytest`: dedupe, pagination, incremental, validation, matching, API shapes, PostGIS bbox.
- Frontend `vitest` / Playwright: search/filters, detail provenance, empty states, map with real GeoJSON (fetch mocked only in tests).
- DB: `supabase db push` on fresh project applies cleanly; RLS tests (anon cannot write, user cannot read another user's watchlist).
- CI (`.github/workflows/ci.yml`) fails on any test failure.

# REPO_AUDIT.md — Georgia Foreclosure Platform

- **Repo:** `nearantiarg/Foreclosure` (GitHub)
- **Audit date:** 2026-10-15
- **Auditor:** Scaffolding agent (Supabase + Docs + CI + Root)

## Finding: repo was EMPTY

Verified 2026-10-15: the GitHub repository `nearantiarg/Foreclosure` contained no code, no migrations, no README, no CI — effectively empty. There was nothing to preserve, migrate, or delete. No git history to keep.

**Decision:** Scaffold from scratch per the implementation spec at `~/workspace/your_files/foreclosure-platform-meta-muse-spec.md` (read in full before building).

## What was built in this scaffolding pass (this agent)

**Supabase (M1 — database):**
- `supabase/migrations/0001_extensions.sql` — PostGIS + pg_trgm + pgcrypto
- `supabase/migrations/0002_counties_properties.sql` — counties + properties, `parcel_id_normalized`, `geometry(Point/MultiPolygon, 4326)`, GiST + trigram indexes, `last_seen_at`/`updated_at` triggers
- `supabase/migrations/0003_notices_auctions_events_documents.sql` — foreclosure_notices, auction_events (partial unique for linked case), property_events (append-only), document_records, natural-key uniques
- `supabase/migrations/0004_comps_watchlist.sql` — comparable_sales (`license_status`), watchlist (user-scoped)
- `supabase/migrations/0005_sources_ingestion.sql` — sources, ingestion_runs, raw_payloads, source_health
- `supabase/migrations/0006_rls.sql` — RLS on ALL tables; anon+authenticated read for public tables, service-role-only write, watchlist user-scoped, raw_payloads service-role-only, FORCE RLS
- `supabase/migrations/0007_seed.sql` — Forsyth (FIPS 117) + Fulton (FIPS 121) + 12 source rows ONLY. No fake properties/notices/auctions/comps.
- `supabase/migrations/0008_indexes_functions.sql` — bbox / calendar / status indexes, `properties_in_bbox()`, `nearby_properties()`, `first_tuesday_of_month()` (display helper only)
- `supabase/config.toml` (minimal), `supabase/seed.sql` (pointer to 0007), `supabase/README.md`

**Root:**
- `.gitignore` — env, node_modules, .next, __pycache__, .env.local, Supabase local dirs
- `.env.example` — all vars, empty values: SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY (server-only), SUPABASE_DB_URL (server-only), NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY, FASTAPI_BASE_URL, NEXT_PUBLIC_FASTAPI_BASE_URL, INGESTION_SECRET, SENTRY_DSN (optional), LOG_LEVEL, NODE_ENV
- `README.md` — platform description, architecture summary, run-locally, milestone table, disclaimer
- `package.json` — workspace note (frontend/backend owned by separate agents; not a build root)
- `docker-compose.yml` — local dev (Postgres+PostGIS, backend, frontend) with env placeholders; backend/frontend services expect those dirs to exist

**Docs:**
- `docs/ARCHITECTURE.md`, `docs/DATA_SOURCES.md`, `docs/RUNBOOK.md`, `docs/ADDING_A_COUNTY.md`

**CI:**
- `.github/workflows/ci.yml` — backend (ruff, black --check, mypy, pytest), frontend (tsc, eslint, npm test), migration check (files exist + SQL parse via Python, no live DB required), fails on any test failure
- `.github/workflows/ingestion.yml` — scheduled cron daily 06:00 ET calling `POST /ingestion/run` per source, manual dispatch, secrets INGESTION_SECRET + FASTAPI_BASE_URL; requires deployed FastAPI (documented)

## What is stub / mock / placeholder

- **None in production data paths.** Seed contains zero fake properties/notices/auctions/comps. Migrations contain no mock data.
- `docker-compose.yml` backend/frontend services are placeholders until those dirs land — they reference `./backend` and `./frontend` and will fail to build until those agents deliver. This is expected and documented in the file.
- `ci.yml` frontend/backend jobs use `if: hashFiles(...) != ''` guards so CI stays green until those dirs land; once they exist, the jobs run for real. This is intentional scaffolding behavior, not a test bypass — do not keep the guards once the dirs exist (see comment in ci.yml).

## What is pending (other agents / owner)

- `backend/` — FastAPI app, ingestion pipeline, connectors, tests (separate agent owns; do not duplicate here).
- `frontend/` — Next.js app, pages, map, watchlist (separate agent owns).
- **Verification against the supplied Supabase project:** `supabase db push` + seed-count checks + RLS tests have NOT been run against the real project in this pass (no credentials in this environment). Owner/backend agent must run them with the supplied project values before claiming M1 done.
- Ingestion connectors: none built yet (M2+). Sources registry rows exist; connectors are pending.
- `PENDING_LICENSE` sources (MLS/FMLS comps, proprietary feeds, GSCCCA bulk) have registry rows with `license_status='PENDING_LICENSE'` + `is_enabled=false` and must produce zero canonical rows until licensed.

## What must NOT be done

- Do NOT add fake properties/notices/auctions/comps to seed or migrations to "test the UI." Use test fixtures under `backend/tests/fixtures/` / `frontend` tests only.
- Do NOT disable RLS, add a service-role key to client code, or commit `.env` / `.env.local`.
- Do NOT compute a notice `sale_date` from `first_tuesday_of_month()` — that function is display/filter only. Sale dates come from published notices.


## Update Oct 15, 2026 — Build complete

- Backend (FastAPI + ingestion + tests): 26 pytest passed.
- Frontend (Next.js + Tailwind): tsc clean, 4 vitest passed, next build 11 routes.
- Supabase migrations 0001-0008 + docs + CI present.
- Admin route now has optional ADMIN_TOKEN gate (see frontend/app/api/admin/ingestion/route.ts). Full Supabase Auth admin-role gating still recommended before public deploy.
- Live Supabase wiring + first real ingestion run still require the supplied Supabase credentials (not invented) — see docs/RUNBOOK.md.

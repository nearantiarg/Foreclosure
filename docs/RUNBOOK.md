# RUNBOOK.md — Georgia Foreclosure Platform

Operational guide: run locally, run ingestion, backfill, check health, rotate secrets, add a county, verify RLS.

## Prerequisites

- Node 20+, Python 3.12+, Supabase CLI, Docker (optional, local Postgres+PostGIS).
- Access to the SUPPLIED Supabase project (do not create a new project).
- `.env.local` filled from `.env.example` (never commit real keys).

## Run locally

```bash
# 1. Env
cp .env.example .env.local
# Fill SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY,
# SUPABASE_DB_URL, FASTAPI_BASE_URL, INGESTION_SECRET from the supplied project.

# 2. Database — supplied cloud project (preferred for staging)
supabase db push --db-url "$SUPABASE_DB_URL"

#    ... or local dry-run
supabase start
supabase db reset

# 3. Verify seed — no fake data
psql "$SUPABASE_DB_URL" -c "select count(*) from counties;"     # expect 2
psql "$SUPABASE_DB_URL" -c "select count(*) from sources;"      # expect 12
psql "$SUPABASE_DB_URL" -c "select count(*) from properties;"   # expect 0
psql "$SUPABASE_DB_URL" -c "select count(*) from foreclosure_notices;"  # expect 0
psql "$SUPABASE_DB_URL" -c "select PostGIS_version();"

# 4. Backend (once backend/ lands)
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
curl http://localhost:8000/health
# expect: {"status":"ok","db":"ok","postgis":true,...}

# 5. Frontend (once frontend/ lands)
cd frontend
npm install
npm run dev   # http://localhost:3000
```

### Docker (optional local dev)

```bash
docker compose up -d db        # local Postgres 15 + PostGIS on :54322
docker compose up --build      # db + backend + frontend (once those dirs exist)
docker compose down
```

`docker-compose.yml` uses env placeholders — fill `.env.local` first. Backend/frontend services expect `./backend` and `./frontend` to exist; they are owned by separate agents.

## Run ingestion

Ingestion is owned by the FastAPI backend (`POST /ingestion/run`). The endpoint is protected by `X-Ingestion-Secret` / service-role auth — never open to anon.

```bash
# Incremental run for one source (default)
curl -X POST "$FASTAPI_BASE_URL/ingestion/run?source_key=forsyth_legal_organ&mode=incremental" \
  -H "X-Ingestion-Secret: $INGESTION_SECRET"

# Response: {"run_id": "<uuid>", "status": "running"|"success"|...}
# Poll:
curl "$FASTAPI_BASE_URL/ingestion/runs?source_key=forsyth_legal_organ&limit=5" \
  -H "X-Ingestion-Secret: $INGESTION_SECRET"
```

Scheduled runs: `.github/workflows/ingestion.yml` runs daily 06:00 ET and calls `POST /ingestion/run` per source. It requires a deployed FastAPI (`FASTAPI_BASE_URL` secret) + `INGESTION_SECRET` secret. Manual dispatch: Actions → "Scheduled Ingestion" → Run workflow (optionally one `source_key` + `mode`).

**Fallback scheduler:** Supabase `pg_cron` calling a secured Edge Function that proxies to `POST /ingestion/run`. Only use if GitHub Actions scheduling is unavailable; document which scheduler is active in this runbook.

## Backfill (bounded)

```bash
# Bounded backfill — NEVER unbounded. Always pass a date window + max pages.
curl -X POST "$FASTAPI_BASE_URL/ingestion/run?source_key=forsyth_legal_organ&mode=full&since=2026-01-01&until=2026-10-15&max_pages=50" \
  -H "X-Ingestion-Secret: $INGESTION_SECRET"
```

Backfill rules: date window required, `max_pages` cap required, one source at a time, watch `ingestion_runs` counts. A backfill that inserts 0 rows is fine — it means no new records in that window. Never backfill to "fill the UI."

## Check source health

```bash
# API
curl "$FASTAPI_BASE_URL/health/sources"
# Frontend
# /sources — per-source status, last run, records seen/inserted, last error, license status

# SQL
psql "$SUPABASE_DB_URL" -c "select source_id, status, consecutive_failures, last_error, updated_at from source_health order by updated_at desc;"
psql "$SUPABASE_DB_URL" -c "select s.source_key, r.status, r.records_seen, r.records_inserted, r.records_skipped, r.records_failed, r.started_at from ingestion_runs r join sources s on s.id = r.source_id order by r.started_at desc limit 20;"
```

Health rule: healthy if last run succeeded, degraded if partial, down after 3 consecutive failures. A `down` source needs investigation (see "When a source fails" below), not a retry loop.

## When a source fails

1. Read `ingestion_runs.error_message` / `error_details` for the failed run.
2. Check `source_health.last_error` + `consecutive_failures`.
3. Check the source URL in a browser — is it a site change, a paywall, a block, or a transient 5xx?
4. If transient: re-run once manually. If it fails again, leave it `down` and investigate — do not hammer the source.
5. If blocked/paywalled: document the block in `docs/DATA_SOURCES.md` (Status → `blocked`, date, reason), keep the connector, do NOT scrape around the block or invent records.
6. If the site changed format: fix the parser, add a regression fixture under `backend/tests/fixtures/` (labeled as fixture, never served as production data), and re-run.

## Verify RLS

Run against the supplied project (service-role connection for setup, then anon/authenticated checks):

```sql
-- 1. Anon can SELECT public tables:
--    (use the anon key via Supabase client / PostgREST)
--    select count(*) from properties; -- should work

-- 2. Anon CANNOT insert:
--    insert into properties (county_id, parcel_id, parcel_id_normalized)
--    values (...); -- should FAIL with RLS / permission error

-- 3. Authenticated user A sees only own watchlist:
--    select * from watchlist; -- only rows where user_id = auth.uid()

-- 4. Authenticated user B cannot see user A's watchlist rows.

-- 5. raw_payloads: anon/authenticated SELECT should FAIL; service_role succeeds.
```

## Rotate secrets

1. **Supabase keys:** Rotate in Supabase Dashboard → Settings → API. Update `.env.local` (local), deployment env vars, and GitHub secrets (`INGESTION_SECRET` / `FASTAPI_BASE_URL` are separate — see below). Never commit the new values. Verify `GET /health` still works after rotation.
2. **INGESTION_SECRET:** Generate a new secret, update the FastAPI deployment env + GitHub secret `INGESTION_SECRET` (Settings → Secrets → Actions). Verify a manual `POST /ingestion/run` with the new secret succeeds and the old secret fails.
3. **Postgres password / DB URL:** Rotate in Supabase Dashboard → Settings → Database. Update `SUPABASE_DB_URL` everywhere it is used (local `.env.local`, CI, deployment). Verify `supabase db push --dry-run` / `psql` connectivity.
4. After any rotation: grep the repo for the old value to confirm it was never committed (`grep -r "<old-value-prefix>" . --exclude-dir=node_modules --exclude-dir=.git` — do not paste full secrets into shell history; use a short unique prefix).

## Add a county

See `docs/ADDING_A_COUNTY.md` — the full checklist. Short version: insert `counties` row + `sources` rows, implement/verify the county's connectors, run a bounded ingestion, verify data + health, then set `is_active=true`.

## Deploy checklist (staging → production)

- [ ] `supabase db push` applies cleanly on a fresh/branch project.
- [ ] Seed counts verified (2 counties, 12 sources, 0 properties/notices/auctions/comps).
- [ ] RLS checks pass (above).
- [ ] `pytest` (backend) + frontend tests + `tsc --noEmit` + `eslint` pass.
- [ ] `GET /health` + `GET /ready` return ok against the deployed backend.
- [ ] GitHub secrets set: `INGESTION_SECRET`, `FASTAPI_BASE_URL`.
- [ ] No privileged key in client code (`grep -r SERVICE_ROLE frontend/` returns nothing).
- [ ] `.env` / `.env.local` not committed (`git status` clean of secrets).

## Incident notes

- Never delete `ingestion_runs` / `raw_payloads` / `property_events` to "clean up" — they are the audit trail.
- Never disable RLS to debug. Use the service-role connection for inspection, and fix the policy instead.
- Never paste full secrets into chat, logs, or shell history.

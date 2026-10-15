# Georgia Foreclosure Intelligence Platform

A working, **data-first** platform for Georgia foreclosure records: real property records, verified foreclosure notices, auction events, historical changes, and comparable sales where licensed or publicly available.

**No mock listings. No hardcoded statistics. No simulated API responses.** Every property, notice, auction, and price shown in production comes from a real ingested source record stored in Supabase, with provenance (source name, source URL, retrieved_at). Where data access requires a license or approval, the connector interface exists and is clearly marked `PENDING_LICENSE` — records are never invented.

> Public-record information only; not legal advice. Verify with the county clerk / legal organ before acting.

## Repo

- GitHub: `nearantiarg/Foreclosure`
- Layout (monorepo):

```
foreclosure/
  frontend/          # Next.js 14+ App Router, TypeScript, Tailwind CSS (separate agent owns)
  backend/           # Python 3.12+ FastAPI — ingestion + analytics (separate agent owns)
  supabase/          # Migrations, RLS, seed, PostGIS (this scaffolding)
  docs/              # ARCHITECTURE.md, DATA_SOURCES.md, RUNBOOK.md, ADDING_A_COUNTY.md
  .github/workflows/ # CI + scheduled ingestion
  .env.example       # All env vars, empty values
  README.md          # This file
  REPO_AUDIT.md      # Repo was empty — what was built, what is pending
```

## Architecture (summary)

```
Public sources (legal organs, GSCCCA public search, qPublic/assessor, county sale lists, HUD/Fannie/Freddie REO)
  ↓ HTTP fetch / CSV / HTML / PDF parsing — respect robots.txt + rate limits
FastAPI Ingestion Workers (one connector per source: fetch → raw archive → parse → normalize → dedupe → upsert → record run)
  ↓
Supabase PostgreSQL + PostGIS (canonical tables + raw_payloads + ingestion_runs + source_health)
  ↓
FastAPI Analytics API (aggregations, search, geo) + Supabase direct reads (RLS) for simple lists
  ↓
Next.js Frontend (search / list / map / property detail / auction calendar / watchlist / source status)
```

Full detail: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

## Coverage

- **Launch:** Forsyth County (FIPS 117) + Fulton County (FIPS 121), GA.
- **Expansion:** Config-driven to all 159 Georgia counties — adding a county is config rows + verified connectors, not a rewrite. See [`docs/ADDING_A_COUNTY.md`](docs/ADDING_A_COUNTY.md).

## Data sources

See [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md) for the per-source table (URL, county, what it publishes, access, cadence, pagination, dedupe key, status).

Georgia foreclosure basics encoded in the platform: non-judicial, power-of-sale, advertisement once a week for 4 consecutive weeks before sale (O.C.G.A. § 44-14-162). Sales on the **first Tuesday** of the month at the courthouse. `sale_date` is always taken from the published notice — never computed.

## How to run locally

Prerequisites: Node 20+, Python 3.12+, Supabase CLI, Docker (optional, for local Postgres+PostGIS).

```bash
# 1. Env
cp .env.example .env.local
# Fill values from the SUPPLIED Supabase project (never commit real keys).

# 2. Database — against the supplied cloud project:
supabase db push --db-url "$SUPABASE_DB_URL"
# Or local dry-run:
supabase start && supabase db reset

# 3. Verify seed (no fake data):
psql "$SUPABASE_DB_URL" -c "select count(*) from counties;"    # expect 2
psql "$SUPABASE_DB_URL" -c "select count(*) from sources;"     # expect 12
psql "$SUPABASE_DB_URL" -c "select count(*) from properties;"  # expect 0

# 4. Backend (once backend/ lands — separate agent)
# cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload

# 5. Frontend (once frontend/ lands — separate agent)
# cd frontend && npm install && npm run dev
```

Full runbook: [`docs/RUNBOOK.md`](docs/RUNBOOK.md)

## Milestones

| Milestone | Scope | Status |
|-----------|-------|--------|
| M0 | Repo audit + scaffolding + Supabase connection | ✅ Scaffolding done (this repo state); frontend/backend health endpoints pending (separate agents) |
| M1 | Database + PostGIS + RLS + county registry | ✅ Migrations 0001–0008 + seed done; needs `supabase db push` verification against supplied project |
| M2 | Ingestion core + Forsyth legal organ + Forsyth qPublic (first real data) | ⏳ Pending — backend agent |
| M3 | Fulton connectors + property matching + property detail | ⏳ Pending — backend + frontend agents |
| M4 | Auction events + calendar + GSCCCA public index + document records | ⏳ Pending |
| M5 | Map + analytics + watchlist + comps (`PENDING_LICENSE` interface) | ⏳ Pending |
| M6 | Scheduling + monitoring + hardening + docs | ⏳ Pending (ingestion workflow scaffolded; needs deployed FastAPI) |
| M7 | Expansion to all 159 GA counties (config-driven) | ⏳ Pending — see `docs/ADDING_A_COUNTY.md` |

## Definition of done (entire project)

- [ ] All M0–M7 acceptance checks pass with commands + outputs recorded.
- [ ] Production UI shows ZERO mock listings, ZERO hardcoded stats, ZERO fake comps. Every record has provenance.
- [ ] `supabase db push` on a fresh project + `pytest` + frontend tests + `tsc` all pass from a clean checkout.
- [ ] No privileged key in client code, git history, or logs (`grep -r SERVICE_ROLE frontend/` returns nothing).
- [ ] `docs/DATA_SOURCES.md` lists every source with live/pending status and source URLs.

## Disclaimer

Public-record information only; not legal advice. Verify with the county clerk / legal organ before acting. Foreclosure sale results are shown only when published by a source — otherwise status is `unknown` / `result not yet published`.

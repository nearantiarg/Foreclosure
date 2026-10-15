# Georgia Foreclosure Platform — Backend

FastAPI backend for ingestion + analytics. **Data-first: no mock listings, no hardcoded stats, no fake comps in production code.** Every record comes from a real ingested source with provenance.

Georgia note: non-judicial, power-of-sale. O.C.G.A. § 44-14-162 requires advertisement once a week for 4 consecutive weeks before the sale. Sales are on the first Tuesday (or next business day if a holiday) at the courthouse. `sale_date` is ALWAYS taken from the published notice — never computed.

## Run

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in supplied Supabase values
uvicorn app.main:app --reload --port 8000
# Docs: http://localhost:8000/docs
# Health: http://localhost:8000/health
# Ready:  http://localhost:8000/ready
```

## Env vars

See `.env.example`. `SUPABASE_SERVICE_ROLE_KEY` + `SUPABASE_DB_URL` are **server-side only** — never in frontend code or `NEXT_PUBLIC_*`.

| Var | Required | Notes |
|-----|----------|-------|
| `SUPABASE_URL` | yes | Supplied project |
| `SUPABASE_ANON_KEY` | yes | |
| `SUPABASE_SERVICE_ROLE_KEY` | yes (prod) | Server-side only |
| `SUPABASE_DB_URL` | yes (prod) | Direct Postgres for PostGIS / COUNT(*) |
| `INGESTION_SECRET` | yes (prod) | `X-Ingestion-Secret` header |
| `FRONTEND_ORIGIN` | yes | CORS allowlist — single origin, never `*` |
| `FASTAPI_BASE_URL` | no | Default `http://localhost:8000` |

## Trigger ingestion

```bash
# Incremental (default)
curl -X POST "http://localhost:8000/ingestion/run?source_key=forsyth_legal_organ&mode=incremental" \
  -H "X-Ingestion-Secret: $INGESTION_SECRET"

# Full backfill
curl -X POST "http://localhost:8000/ingestion/run?source_key=forsyth_qpublic&mode=full" \
  -H "X-Ingestion-Secret: $INGESTION_SECRET"

# Recent runs + source health
curl http://localhost:8000/ingestion/runs
curl http://localhost:8000/health/sources
curl http://localhost:8000/sources
```

Source keys: `forsyth_legal_organ`, `fulton_legal_organ`, `forsyth_qpublic`, `fulton_assessor`, `gsccca_public`, `county_auction`, `hud_reo`, `mls_pending` (PENDING_LICENSE — always fails with `license_required`, no records).

## Tests

```bash
pytest -q
# Lint / format / types
ruff check app tests
black --check app tests
mypy app
```

Fixtures live only under `tests/fixtures/` and are never served as production data.

## Layout

- `app/main.py` — FastAPI app, CORS (Next.js origin only)
- `app/config.py` — env settings
- `app/schemas.py` — Pydantic v2 models + validation
- `app/db.py` — Supabase client (service-role, server-side) + psycopg helper
- `app/api/` — health, counties, properties (PostGIS bbox), notices, auctions, analytics (live COUNT(*)), ingestion, sources
- `app/ingestion/base.py` — BaseConnector + retry / parcel normalization
- `app/ingestion/pipeline.py` — fetch → raw archive → parse → validate → dedupe → upsert → run + health
- `app/ingestion/connectors/` — one connector per source
- `app/ingestion/matching.py` — notice→property matching (exact parcel, then fuzzy ≥0.82)
- `app/services/` — analytics + matching re-exports

## Errors

All errors use `{detail, code, run_id?}`. Ingestion without a valid `X-Ingestion-Secret` → 401. Unknown source → 404. Bad filters → 422. DB unavailable → 503.

Public-record information only; not legal advice. Verify with the county clerk / legal organ before acting.

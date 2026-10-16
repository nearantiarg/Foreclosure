# Supabase — Georgia Foreclosure Platform

PostgreSQL 15 + PostGIS. Source of truth for the platform.

## Layout

```
supabase/
  config.toml          # Local dev config (minimal; no real keys)
  seed.sql             # Pointer — real seed is migrations/0007_seed.sql
  README.md            # This file
  migrations/
    0001_extensions.sql                  # postgis + pg_trgm + pgcrypto
    0002_counties_properties.sql         # counties + properties, GiST, triggers
    0003_notices_auctions_events_documents.sql
    0004_comps_watchlist.sql            # comparable_sales + watchlist
    0005_sources_ingestion.sql          # sources, ingestion_runs, raw_payloads, source_health
    0006_rls.sql                       # RLS on ALL tables
    0007_seed.sql                      # Counties (Forsyth 117, Fulton 121) + sources registry ONLY
    0008_indexes_functions.sql          # Bbox / calendar indexes + properties_in_bbox, nearby_properties, first_tuesday_of_month
```

## Rules

- **Data-first:** Seed contains NO fake properties / notices / auctions / comps. Those tables are empty after seed and fill only via real ingestion.
- **RLS:** Enabled on every table (0006). Public tables: `anon` + `authenticated` read, `service_role`-only write. `watchlist`: user-scoped. `raw_payloads`: `service_role` only.
- **Idempotency:** Every migration is re-runnable (`IF NOT EXISTS`, `ON CONFLICT`, guarded `DO` blocks). Re-running must not duplicate rows.
- **PostGIS:** All geometry is SRID 4326. `centroid` is `Point`, `boundary` is `MultiPolygon`. `NULL` geometry means "not published" — never invent coordinates.
- **Append-only:** `property_events` is never updated/deleted in normal operation.

## Local development

```bash
# 1. Copy env (never commit real keys)
cp .env.example .env.local
# Fill SUPABASE_URL / SUPABASE_ANON_KEY / SUPABASE_SERVICE_ROLE_KEY / SUPABASE_DB_URL
# from the SUPPLIED Supabase project.

# 2a. Against the supplied cloud project (preferred for staging)
# Use the Supabase Dashboard SQL editor or:
#   supabase db push --db-url "$SUPABASE_DB_URL"

# 2b. Local Supabase (for migration dry-runs)
supabase start
supabase db reset   # applies migrations incl. seed

# 3. Verify
psql "$SUPABASE_DB_URL" -c "select PostGIS_version();"
psql "$SUPABASE_DB_URL" -c "select count(*) from counties;"
psql "$SUPABASE_DB_URL" -c "select count(*) from sources;"
psql "$SUPABASE_DB_URL" -c "select count(*) from properties;"  -- expect 0
```

## Adding a migration

1. Create `supabase/migrations/NNNN_description.sql` with the next number.
2. Make it idempotent-safe (`IF NOT EXISTS`, `ON CONFLICT`, guarded triggers).
3. Comment the down reasoning (why a rollback needs a backup / manual step).
4. If it adds a table, add RLS in the same migration or in a follow-up RLS migration — never leave a table without RLS.
5. Test: `supabase db reset` on a fresh local project must apply cleanly.

## RLS testing (manual)

```sql
-- As anon: should SELECT public tables, should FAIL on INSERT.
-- As authenticated user A: should SELECT own watchlist only.
-- As authenticated user B: should NOT see user A's watchlist.
-- See docs/RUNBOOK.md "Verify RLS" for the full checklist.
```

## Functions

- `properties_in_bbox(min_lng, min_lat, max_lng, max_lat, county_fips?)` — map bbox query.
- `nearby_properties(property_id, radius_miles, limit)` — true PostGIS distance.
- `first_tuesday_of_month(year, month)` — display/filter helper ONLY. Never use to create a notice `sale_date`.

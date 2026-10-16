-- Migration 0001: Extensions
-- Georgia Foreclosure Platform — Supabase PostgreSQL + PostGIS
-- Idempotent-safe: uses IF NOT EXISTS / CREATE ... IF NOT EXISTS where supported.
-- Down reasoning: extensions are shared infra; do NOT drop them in a down migration
-- without confirming no other object depends on them. Manual rollback only.

-- PostGIS: spatial types, GiST indexes, ST_* functions. Required for parcel
-- centroids / boundaries, bbox search, nearby-properties queries.
create extension if not exists postgis;

-- pg_trgm: trigram similarity for address / parcel / owner fuzzy search.
create extension if not exists pg_trgm;

-- pgcrypto: gen_random_uuid() for UUID primary keys.
-- On Supabase, pgcrypto is typically available; guard with IF NOT EXISTS.
create extension if not exists pgcrypto;

-- Verify (no-op if extensions already present; informational only).
-- select PostGIS_version(), * from pg_extension where extname in ('postgis','pg_trgm','pgcrypto');

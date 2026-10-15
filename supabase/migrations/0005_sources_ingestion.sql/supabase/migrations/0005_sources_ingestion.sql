-- Migration 0005: Sources, ingestion runs, raw payloads, source health
-- Idempotent-safe: IF NOT EXISTS / guarded DO blocks.
-- Down reasoning: ingestion_runs / raw_payloads are the audit trail for
-- provenance. Never truncate them via migration. Manual rollback only.

-- ---------------------------------------------------------------------------
-- sources — registry of every ingestion source.
-- source_key: stable machine key, e.g. 'forsyth_legal_organ'.
-- county_id NULL for statewide / national sources (e.g. hud_reo).
-- license_status: 'public' | 'PENDING_LICENSE' | 'PENDING_APPROVAL'.
--   PENDING_* sources must have NO rows in canonical tables from that source.
-- ---------------------------------------------------------------------------
create table if not exists public.sources (
  id uuid primary key default gen_random_uuid(),
  source_key text not null unique,
  display_name text not null,
  county_id uuid references public.counties(id) on delete set null,
  source_type text not null,
  base_url text not null,
  is_enabled boolean not null default true,
  license_status text not null default 'public',
  expected_cadence text,
  last_successful_run_at timestamptz,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint sources_license_check check (license_status in ('public','PENDING_LICENSE','PENDING_APPROVAL')),
  constraint sources_type_check check (source_type in ('legal_organ','assessor','clerk_gsccca','tax_sale','reo','mls_pending','proprietary_pending'))
);

do $$
begin
  if not exists (select 1 from pg_trigger where tgname = 'trg_sources_updated_at') then
    create trigger trg_sources_updated_at
      before update on public.sources
      for each row execute function public.touch_updated_at();
  end if;
end $$;

-- ---------------------------------------------------------------------------
-- ingestion_runs — one row per ingestion attempt (success or failure).
-- status: running | success | partial_success | failed
-- triggered_by: scheduled | manual | backfill
-- Every run records pages / counts so dedupe + incremental behavior is auditable.
-- ---------------------------------------------------------------------------
create table if not exists public.ingestion_runs (
  id uuid primary key default gen_random_uuid(),
  source_id uuid not null references public.sources(id) on delete restrict,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  status text not null,
  pages_fetched int not null default 0,
  records_seen int not null default 0,
  records_inserted int not null default 0,
  records_updated int not null default 0,
  records_skipped int not null default 0,
  records_failed int not null default 0,
  high_water_mark text,
  error_message text,
  error_details jsonb,
  triggered_by text not null default 'scheduled',
  constraint ingestion_runs_status_check check (status in ('running','success','partial_success','failed')),
  constraint ingestion_runs_triggered_by_check check (triggered_by in ('scheduled','manual','backfill')),
  constraint ingestion_runs_counts_nonnegative check (
    pages_fetched >= 0 and records_seen >= 0 and records_inserted >= 0 and
    records_updated >= 0 and records_skipped >= 0 and records_failed >= 0
  ),
  constraint ingestion_runs_finished_after_start check (finished_at is null or finished_at >= started_at)
);

-- ---------------------------------------------------------------------------
-- raw_payloads — raw fetched payload BEFORE parsing.
-- Parsing failures must not lose raw evidence.
-- payload_text inline for small payloads; storage_path (Supabase Storage)
-- for large payloads (PDFs, large HTML). Exactly one should be set in
-- practice; the pipeline enforces this in code, not with a DB constraint,
-- so a failed upload does not block the audit row.
-- payload_hash: SHA-256 (or similar) of the raw bytes, for dedupe / integrity.
-- ---------------------------------------------------------------------------
create table if not exists public.raw_payloads (
  id uuid primary key default gen_random_uuid(),
  source_id uuid not null references public.sources(id) on delete restrict,
  ingestion_run_id uuid references public.ingestion_runs(id) on delete set null,
  source_url text not null,
  payload_hash text not null,
  payload_type text not null,
  storage_path text,
  payload_text text,
  fetched_at timestamptz not null default now(),
  constraint raw_payloads_type_check check (payload_type in ('html','csv','json','pdf'))
);

-- ---------------------------------------------------------------------------
-- source_health — current health per source (one row per source).
-- status: unknown | healthy | degraded | down | pending_license
-- updated_at bumped on every health write.
-- Rule (enforced by pipeline, documented here): healthy if last run succeeded,
-- degraded if partial, down after 3 consecutive failures.
-- ---------------------------------------------------------------------------
create table if not exists public.source_health (
  source_id uuid primary key references public.sources(id) on delete cascade,
  status text not null default 'unknown',
  last_check_at timestamptz,
  consecutive_failures int not null default 0,
  last_error text,
  updated_at timestamptz not null default now(),
  constraint source_health_status_check check (status in ('unknown','healthy','degraded','down','pending_license')),
  constraint source_health_failures_nonnegative check (consecutive_failures >= 0)
);

do $$
begin
  if not exists (select 1 from pg_trigger where tgname = 'trg_source_health_updated_at') then
    create trigger trg_source_health_updated_at
      before update on public.source_health
      for each row execute function public.touch_updated_at();
  end if;
end $$;

comment on table public.sources is 'Ingestion source registry. PENDING_* sources produce no canonical rows.';
comment on table public.ingestion_runs is 'Audit trail for every ingestion attempt. Never delete.';
comment on table public.raw_payloads is 'Raw evidence before parsing. payload_text inline OR storage_path for large payloads.';
comment on table public.source_health is 'Current per-source health. Pipeline-maintained; UI reads this.';

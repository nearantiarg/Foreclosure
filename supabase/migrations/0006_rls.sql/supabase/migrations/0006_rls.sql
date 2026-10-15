-- Migration 0006: Row Level Security (RLS)
-- Enable RLS on ALL user tables. No table is left without RLS.
-- Model (per spec §3.2):
--   Public tables (counties, properties, foreclosure_notices, auction_events,
--   property_events, document_records, comparable_sales, sources,
--   source_health, ingestion_runs):
--     - READ: anon + authenticated (public-record data)
--     - WRITE: service_role ONLY (via backend; anon/authenticated cannot insert/update/delete)
--   watchlist: user-scoped — user can only see/manage own rows (user_id = auth.uid()).
--     Service role bypasses RLS by design (Supabase: service_role skips RLS),
--     so no explicit service_role policies are needed for writes.
--   raw_payloads: service_role ONLY (no anon/authenticated read or write).
--
-- Idempotent-safe: ALTER TABLE ... ENABLE ROW LEVEL SECURITY is idempotent;
-- policies are dropped if they exist, then created.
-- Down reasoning: disabling RLS would expose write access. Never do it in
-- production. Manual rollback only, with a full policy review.

-- ---------------------------------------------------------------------------
-- Enable RLS on every table
-- ---------------------------------------------------------------------------
alter table public.counties enable row level security;
alter table public.properties enable row level security;
alter table public.foreclosure_notices enable row level security;
alter table public.auction_events enable row level security;
alter table public.property_events enable row level security;
alter table public.document_records enable row level security;
alter table public.comparable_sales enable row level security;
alter table public.watchlist enable row level security;
alter table public.sources enable row level security;
alter table public.ingestion_runs enable row level security;
alter table public.raw_payloads enable row level security;
alter table public.source_health enable row level security;

-- ---------------------------------------------------------------------------
-- Helper: drop a policy if it exists (Postgres has no DROP POLICY IF EXISTS
-- on older versions in all contexts, but Supabase PG15 supports it).
-- We use DROP POLICY IF EXISTS throughout for idempotency.
-- ---------------------------------------------------------------------------

-- ===================== counties =====================
drop policy if exists counties_read_public on public.counties;
create policy counties_read_public on public.counties
  for select to anon, authenticated using (true);

-- No write policy for anon/authenticated => writes denied for them.
-- service_role bypasses RLS.

-- ===================== properties =====================
drop policy if exists properties_read_public on public.properties;
create policy properties_read_public on public.properties
  for select to anon, authenticated using (true);

-- ===================== foreclosure_notices =====================
drop policy if exists foreclosure_notices_read_public on public.foreclosure_notices;
create policy foreclosure_notices_read_public on public.foreclosure_notices
  for select to anon, authenticated using (true);

-- ===================== auction_events =====================
drop policy if exists auction_events_read_public on public.auction_events;
create policy auction_events_read_public on public.auction_events
  for select to anon, authenticated using (true);

-- ===================== property_events =====================
drop policy if exists property_events_read_public on public.property_events;
create policy property_events_read_public on public.property_events
  for select to anon, authenticated using (true);

-- ===================== document_records =====================
drop policy if exists document_records_read_public on public.document_records;
create policy document_records_read_public on public.document_records
  for select to anon, authenticated using (true);

-- ===================== comparable_sales =====================
drop policy if exists comparable_sales_read_public on public.comparable_sales;
create policy comparable_sales_read_public on public.comparable_sales
  for select to anon, authenticated using (true);

-- ===================== sources =====================
drop policy if exists sources_read_public on public.sources;
create policy sources_read_public on public.sources
  for select to anon, authenticated using (true);

-- ===================== source_health =====================
drop policy if exists source_health_read_public on public.source_health;
create policy source_health_read_public on public.source_health
  for select to anon, authenticated using (true);

-- ===================== ingestion_runs =====================
drop policy if exists ingestion_runs_read_public on public.ingestion_runs;
create policy ingestion_runs_read_public on public.ingestion_runs
  for select to anon, authenticated using (true);

-- ===================== watchlist (user-scoped) =====================
drop policy if exists watchlist_select_own on public.watchlist;
create policy watchlist_select_own on public.watchlist
  for select to authenticated using (user_id = auth.uid());

drop policy if exists watchlist_insert_own on public.watchlist;
create policy watchlist_insert_own on public.watchlist
  for insert to authenticated with check (user_id = auth.uid());

drop policy if exists watchlist_delete_own on public.watchlist;
create policy watchlist_delete_own on public.watchlist
  for delete to authenticated using (user_id = auth.uid());

-- No update policy: watchlist rows are immutable except delete + re-insert.
-- anon has NO access to watchlist at all.

-- ===================== raw_payloads (service_role only) =====================
-- No policies for anon/authenticated => all access denied for them.
-- service_role bypasses RLS, so the backend can read/write.

-- ---------------------------------------------------------------------------
-- Force RLS for table owners too (defense in depth).
-- Supabase: tables owned by postgres would otherwise bypass RLS for the
-- owner. FORCE RLS closes that hole; service_role still bypasses RLS by
-- design in Supabase, so backend writes keep working.
-- NOTE: If your Supabase project uses a different table owner, this is still
-- safe — FORCE applies to the owner role, not to service_role.
-- ---------------------------------------------------------------------------
alter table public.counties force row level security;
alter table public.properties force row level security;
alter table public.foreclosure_notices force row level security;
alter table public.auction_events force row level security;
alter table public.property_events force row level security;
alter table public.document_records force row level security;
alter table public.comparable_sales force row level security;
alter table public.watchlist force row level security;
alter table public.sources force row level security;
alter table public.ingestion_runs force row level security;
alter table public.raw_payloads force row level security;
alter table public.source_health force row level security;

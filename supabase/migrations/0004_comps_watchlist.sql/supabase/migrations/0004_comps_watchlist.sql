-- Migration 0004: Comparable sales + watchlist
-- Idempotent-safe: IF NOT EXISTS / guarded DO blocks.
-- Down reasoning: comparable_sales must never contain synthetic rows.
-- Deleting this table would lose provenance for real comps; manual rollback only.

-- ---------------------------------------------------------------------------
-- comparable_sales — ONLY real recorded sales or licensed MLS data.
-- NO synthetic comps. If license_status = 'PENDING_LICENSE', the row must
-- not exist — the pending state is represented by the absence of rows +
-- the sources.license_status flag + UI message, not by placeholder rows.
-- source_name examples: 'GSCCCA recorded sale', 'County assessor sales',
-- 'MLS (PENDING_LICENSE)'.
-- ---------------------------------------------------------------------------
create table if not exists public.comparable_sales (
  id uuid primary key default gen_random_uuid(),
  subject_property_id uuid not null references public.properties(id) on delete cascade,
  comp_property_id uuid references public.properties(id) on delete set null,
  comp_address text not null,
  sale_date date not null,
  sale_price numeric not null,
  distance_miles numeric,
  similarity_score numeric,
  source_name text not null,
  source_url text,
  source_record_id text,
  license_status text not null default 'public',
  created_at timestamptz not null default now(),
  constraint comparable_sales_natural_unique unique (subject_property_id, source_name, source_record_id),
  constraint comparable_sales_price_positive check (sale_price > 0),
  constraint comparable_sales_distance_nonnegative check (distance_miles is null or distance_miles >= 0),
  constraint comparable_sales_license_check check (license_status in ('public','PENDING_LICENSE')),
  constraint comparable_sales_similarity_range check (similarity_score is null or (similarity_score between 0 and 1))
);

-- ---------------------------------------------------------------------------
-- watchlist — authenticated users only. RLS: user sees only own rows.
-- user_id = Supabase Auth user id (auth.uid()).
-- ---------------------------------------------------------------------------
create table if not exists public.watchlist (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  property_id uuid not null references public.properties(id) on delete cascade,
  created_at timestamptz not null default now(),
  constraint watchlist_user_property_unique unique (user_id, property_id)
);

comment on table public.comparable_sales is 'Real recorded sales / licensed MLS only. Never synthetic. Empty until licensed/public data exists.';
comment on table public.watchlist is 'User-scoped. RLS enforces user_id = auth.uid().';

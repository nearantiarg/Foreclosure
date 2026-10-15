-- Migration 0003: Foreclosure notices, auction events, property events, documents
-- Idempotent-safe: IF NOT EXISTS / guarded DO blocks.
-- Down reasoning: append-only history (property_events) must never be
-- truncated by a migration. Manual rollback with backup only.

-- ---------------------------------------------------------------------------
-- foreclosure_notices — one row per published notice / instrument.
-- Natural key: (county_id, source_name, source_record_id).
-- source_record_id: stable ID from source (instrument #, notice ID, URL hash).
-- sale_date is ALWAYS taken from the published notice — never computed.
-- property_id is NULL until matching links it; matching never invents a property.
-- ---------------------------------------------------------------------------
create table if not exists public.foreclosure_notices (
  id uuid primary key default gen_random_uuid(),
  property_id uuid references public.properties(id) on delete set null,
  county_id uuid not null references public.counties(id) on delete restrict,
  source_name text not null,
  source_url text not null,
  source_record_id text not null,
  notice_type text not null,
  grantor_name text,
  grantee_name text,
  original_loan_amount numeric,
  deed_book text,
  deed_page text,
  instrument_number text,
  legal_description text,
  sale_date date not null,
  sale_location text,
  publication_start_date date,
  publication_end_date date,
  publication_weeks int,
  notice_text text,
  status text not null default 'published',
  first_seen_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  content_hash text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint foreclosure_notices_natural_unique unique (county_id, source_name, source_record_id),
  constraint foreclosure_notices_status_check check (status in ('published','postponed','cancelled','sold','withdrawn','unknown')),
  constraint foreclosure_notices_loan_nonnegative check (original_loan_amount is null or original_loan_amount >= 0),
  constraint foreclosure_notices_pub_order check (
    publication_start_date is null or publication_end_date is null or publication_start_date <= publication_end_date
  )
);

do $$
begin
  if not exists (select 1 from pg_trigger where tgname = 'trg_notices_touch') then
    create trigger trg_notices_touch
      before update on public.foreclosure_notices
      for each row execute function public.touch_last_seen_at();
  end if;
end $$;

do $$
begin
  if not exists (select 1 from pg_trigger where tgname = 'trg_notices_updated_at') then
    create trigger trg_notices_updated_at
      before update on public.foreclosure_notices
      for each row execute function public.touch_updated_at();
  end if;
end $$;

-- ---------------------------------------------------------------------------
-- auction_events — one row per scheduled sale; links to notices.
-- Dedupe: (county_id, sale_type, sale_date, property_id, notice_id) is NOT
-- a safe unique constraint when property_id / notice_id are NULL (NULL != NULL
-- in Postgres unique indexes), so the pipeline enforces dedupe in code
-- AND we add a partial unique index for the fully-linked case below.
-- REO listings use sale_type='REO_auction' and are NEVER mixed into
-- foreclosure counts.
-- ---------------------------------------------------------------------------
create table if not exists public.auction_events (
  id uuid primary key default gen_random_uuid(),
  county_id uuid not null references public.counties(id) on delete restrict,
  property_id uuid references public.properties(id) on delete set null,
  notice_id uuid references public.foreclosure_notices(id) on delete set null,
  sale_date date not null,
  sale_time time,
  sale_location text not null,
  sale_type text not null default 'foreclosure',
  status text not null default 'scheduled',
  opening_bid numeric,
  winning_bid numeric,
  buyer_name text,
  result_source_url text,
  result_retrieved_at timestamptz,
  first_seen_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  content_hash text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint auction_events_sale_type_check check (sale_type in ('foreclosure','tax_sale','sheriff_sale','REO_auction')),
  constraint auction_events_status_check check (status in ('scheduled','postponed','cancelled','held','sold','no_sale','unknown')),
  constraint auction_events_bids_nonnegative check (
    (opening_bid is null or opening_bid >= 0) and
    (winning_bid is null or winning_bid >= 0)
  )
);

do $$
begin
  if not exists (select 1 from pg_trigger where tgname = 'trg_auctions_touch') then
    create trigger trg_auctions_touch
      before update on public.auction_events
      for each row execute function public.touch_last_seen_at();
  end if;
end $$;

do $$
begin
  if not exists (select 1 from pg_trigger where tgname = 'trg_auctions_updated_at') then
    create trigger trg_auctions_updated_at
      before update on public.auction_events
      for each row execute function public.touch_updated_at();
  end if;
end $$;

-- Partial unique: only when both property_id and notice_id are present.
create unique index if not exists idx_auction_events_linked_unique
  on public.auction_events (county_id, sale_type, sale_date, property_id, notice_id)
  where property_id is not null and notice_id is not null;

-- ---------------------------------------------------------------------------
-- property_events — append-only audit of what changed.
-- NEVER update or delete rows here in normal operation. Inserts only.
-- event_type: notice_published | sale_scheduled | sale_postponed |
--   sale_cancelled | sale_result | owner_change | value_change |
--   deed_recorded | ingestion_update
-- payload: structured diff { old: {...}, new: {...} } where applicable.
-- ---------------------------------------------------------------------------
create table if not exists public.property_events (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references public.properties(id) on delete cascade,
  event_type text not null,
  event_date date not null,
  title text not null,
  description text,
  source_name text,
  source_url text,
  payload jsonb,
  created_at timestamptz not null default now(),
  constraint property_events_type_check check (event_type in (
    'notice_published','sale_scheduled','sale_postponed','sale_cancelled',
    'sale_result','owner_change','value_change','deed_recorded','ingestion_update'
  ))
);

-- ---------------------------------------------------------------------------
-- document_records — deeds, liens, foreclosure deeds (clerk / GSCCCA index).
-- Natural key: (county_id, source_name, source_record_id).
-- ---------------------------------------------------------------------------
create table if not exists public.document_records (
  id uuid primary key default gen_random_uuid(),
  property_id uuid references public.properties(id) on delete set null,
  county_id uuid not null references public.counties(id) on delete restrict,
  instrument_number text,
  deed_book text,
  deed_page text,
  document_type text not null,
  grantor_name text,
  grantee_name text,
  recorded_date date,
  consideration_amount numeric,
  source_name text not null,
  source_url text,
  source_record_id text,
  content_hash text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint document_records_natural_unique unique (county_id, source_name, source_record_id),
  constraint document_records_consideration_nonnegative check (consideration_amount is null or consideration_amount >= 0)
);

do $$
begin
  if not exists (select 1 from pg_trigger where tgname = 'trg_documents_updated_at') then
    create trigger trg_documents_updated_at
      before update on public.document_records
      for each row execute function public.touch_updated_at();
  end if;
end $$;

comment on table public.foreclosure_notices is 'Verified published notices only. sale_date from notice text, never computed.';
comment on table public.auction_events is 'Scheduled sales. REO_auction rows are REO listings, not foreclosure notices.';
comment on table public.property_events is 'Append-only history. Never UPDATE/DELETE in normal operation.';
comment on table public.document_records is 'Instrument index from clerk / GSCCCA public search. No fabricated rows.';

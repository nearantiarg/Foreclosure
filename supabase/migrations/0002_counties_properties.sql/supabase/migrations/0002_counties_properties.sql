-- Migration 0002: Counties + Properties (canonical parcels)
-- Idempotent-safe: CREATE TABLE IF NOT EXISTS, CREATE INDEX IF NOT EXISTS,
-- DO blocks for triggers / constraints that lack IF NOT EXISTS support.
-- Down reasoning: dropping these tables would destroy canonical parcel data.
-- Do not auto-drop; manual rollback with backup only.

-- ---------------------------------------------------------------------------
-- Helper: touch last_seen_at / updated_at
-- Used by properties / notices / auctions. Created here so later migrations
-- can reuse it. Idempotent via CREATE OR REPLACE.
-- ---------------------------------------------------------------------------
create or replace function public.touch_last_seen_at()
returns trigger
language plpgsql
as $$
begin
  new.last_seen_at = now();
  return new;
end;
$$;

create or replace function public.touch_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- ---------------------------------------------------------------------------
-- counties — config-driven registry. Start: Forsyth + Fulton active.
-- Expansion to all 159 GA counties = rows + per-county connector config,
-- NOT code changes (see docs/ADDING_A_COUNTY.md).
-- ---------------------------------------------------------------------------
create table if not exists public.counties (
  id uuid primary key default gen_random_uuid(),
  county_name text not null,
  county_fips text not null unique,
  state text not null default 'GA',
  legal_organ_name text,
  legal_organ_url text,
  assessor_url text,
  tax_commissioner_url text,
  clerk_url text,
  gsccca_county_code text,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint counties_fips_format check (county_fips ~ '^[0-9]{3}$'),
  constraint counties_state_check check (state = 'GA')
);

-- Unique on (county_name, state) in addition to FIPS, to catch typos.
do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'counties_name_state_unique'
  ) then
    alter table public.counties
      add constraint counties_name_state_unique unique (county_name, state);
  end if;
end $$;

-- ---------------------------------------------------------------------------
-- properties — one row per parcel (canonical property)
-- parcel_id: as published by the county assessor (APN).
-- parcel_id_normalized: stripped, uppercased, no dashes/spaces/dots, for dedupe.
--   Normalization is the connector's job; the DB enforces uniqueness on the
--   normalized form. Example: "123-45-678" -> "12345678".
-- geometry: centroid Point(4326), boundary MultiPolygon(4326) when published.
--   NULL geometry is allowed — never invent coordinates.
-- ---------------------------------------------------------------------------
create table if not exists public.properties (
  id uuid primary key default gen_random_uuid(),
  county_id uuid not null references public.counties(id) on delete restrict,
  parcel_id text not null,
  parcel_id_normalized text not null,
  address_line1 text,
  address_line2 text,
  city text,
  state text not null default 'GA',
  zip text,
  owner_name text,
  property_type text,
  year_built int,
  living_area_sqft numeric,
  lot_acres numeric,
  bedrooms int,
  bathrooms numeric,
  assessed_value numeric,
  appraised_value numeric,
  tax_year int,
  centroid geometry(Point, 4326),
  boundary geometry(MultiPolygon, 4326),
  assessor_url text,
  first_seen_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  content_hash text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint properties_parcel_normalized_unique unique (county_id, parcel_id_normalized),
  constraint properties_year_built_check check (year_built is null or (year_built between 1700 and 2100)),
  constraint properties_values_nonnegative check (
    (assessed_value is null or assessed_value >= 0) and
    (appraised_value is null or appraised_value >= 0) and
    (living_area_sqft is null or living_area_sqft >= 0) and
    (lot_acres is null or lot_acres >= 0)
  )
);

-- Trigger: bump last_seen_at / updated_at on any update.
do $$
begin
  if not exists (select 1 from pg_trigger where tgname = 'trg_properties_touch') then
    create trigger trg_properties_touch
      before update on public.properties
      for each row execute function public.touch_last_seen_at();
  end if;
end $$;

do $$
begin
  if not exists (select 1 from pg_trigger where tgname = 'trg_properties_updated_at') then
    create trigger trg_properties_updated_at
      before update on public.properties
      for each row execute function public.touch_updated_at();
  end if;
end $$;

do $$
begin
  if not exists (select 1 from pg_trigger where tgname = 'trg_counties_updated_at') then
    create trigger trg_counties_updated_at
      before update on public.counties
      for each row execute function public.touch_updated_at();
  end if;
end $$;

-- Indexes for properties (GiST + B-tree + trigram).
create index if not exists idx_properties_county_parcel
  on public.properties (county_id, parcel_id_normalized);

create index if not exists idx_properties_county_type
  on public.properties (county_id, property_type);

create index if not exists idx_properties_centroid_gist
  on public.properties using gist (centroid);

create index if not exists idx_properties_boundary_gist
  on public.properties using gist (boundary);

-- Trigram search on address / owner / parcel. Requires pg_trgm (0001).
create index if not exists idx_properties_address_trgm
  on public.properties using gin (address_line1 gin_trgm_ops);

create index if not exists idx_properties_owner_trgm
  on public.properties using gin (owner_name gin_trgm_ops);

create index if not exists idx_properties_parcel_trgm
  on public.properties using gin (parcel_id gin_trgm_ops);

-- Helpful comment for future maintainers.
comment on table public.properties is 'Canonical parcel: one row per (county, normalized parcel_id). Real assessor records only; no mock data.';
comment on column public.properties.parcel_id_normalized is 'Uppercase, alphanumeric-only form of parcel_id. Dedupe key.';
comment on column public.properties.centroid is 'PostGIS Point 4326. NULL if not published — never invented.';

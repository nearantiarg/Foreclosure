-- Migration 0008: Indexes + helper functions
-- Idempotent-safe: CREATE INDEX IF NOT EXISTS, CREATE OR REPLACE FUNCTION.
-- Down reasoning: dropping indexes degrades query performance but loses no
-- data. Functions are replaceable. Manual rollback only if needed.

-- ---------------------------------------------------------------------------
-- Indexes not already created in 0002/0003
-- ---------------------------------------------------------------------------

-- Auction calendar: (county_id, sale_date) — the primary calendar query.
create index if not exists idx_auction_events_county_sale_date
  on public.auction_events (county_id, sale_date);

-- Auction status filter.
create index if not exists idx_auction_events_county_status
  on public.auction_events (county_id, status);

-- Notices: (county_id, sale_date) for sale-date range queries.
create index if not exists idx_notices_county_sale_date
  on public.foreclosure_notices (county_id, sale_date);

-- Notices: (county_id, status) for status filters.
create index if not exists idx_notices_county_status
  on public.foreclosure_notices (county_id, status);

-- Notices: property link.
create index if not exists idx_notices_property_id
  on public.foreclosure_notices (property_id);

-- Property events: property timeline (property_id, event_date DESC).
create index if not exists idx_property_events_property_date
  on public.property_events (property_id, event_date desc);

-- Document records: property link + recorded date.
create index if not exists idx_document_records_property_date
  on public.document_records (property_id, recorded_date desc);

create index if not exists idx_document_records_county_source
  on public.document_records (county_id, source_name);

-- Comparable sales: subject property.
create index if not exists idx_comparable_sales_subject
  on public.comparable_sales (subject_property_id);

-- Ingestion runs: source + started_at (monitoring UI).
create index if not exists idx_ingestion_runs_source_started
  on public.ingestion_runs (source_id, started_at desc);

-- Raw payloads: source + fetched_at.
create index if not exists idx_raw_payloads_source_fetched
  on public.raw_payloads (source_id, fetched_at desc);

-- Source health: updated_at (monitoring).
create index if not exists idx_source_health_updated
  on public.source_health (updated_at desc);

-- Properties: county + city/zip for list filters.
create index if not exists idx_properties_county_city_zip
  on public.properties (county_id, city, zip);

-- Bbox support: centroid GiST already exists (0002). This index supports
-- boundary-intersects queries for the map view.
-- (Boundary GiST already created in 0002 as idx_properties_boundary_gist.)

-- ---------------------------------------------------------------------------
-- Function: properties within a bounding box
--   properties_in_bbox(min_lng, min_lat, max_lng, max_lat, county_fips?)
-- Returns id, parcel_id, address, centroid as GeoJSON, county.
-- Used by the map view: GET /properties?bbox=...
-- Never returns invented geometry — only rows with a real centroid.
-- ---------------------------------------------------------------------------
create or replace function public.properties_in_bbox(
  p_min_lng double precision,
  p_min_lat double precision,
  p_max_lng double precision,
  p_max_lat double precision,
  p_county_fips text default null
)
returns table (
  id uuid,
  county_fips text,
  parcel_id text,
  address_line1 text,
  city text,
  zip text,
  property_type text,
  centroid_geojson jsonb
)
language sql
stable
as $$
  select
    p.id,
    c.county_fips,
    p.parcel_id,
    p.address_line1,
    p.city,
    p.zip,
    p.property_type,
    st_asgeojson(p.centroid)::jsonb as centroid_geojson
  from public.properties p
  join public.counties c on c.id = p.county_id
  where p.centroid is not null
    and p.centroid && st_makeenvelope(p_min_lng, p_min_lat, p_max_lng, p_max_lat, 4326)
    and st_within(p.centroid, st_makeenvelope(p_min_lng, p_min_lat, p_max_lng, p_max_lat, 4326))
    and (p_county_fips is null or c.county_fips = p_county_fips)
  order by p.id;
$$;

-- ---------------------------------------------------------------------------
-- Function: nearby properties (for comps / map click)
--   nearby_properties(property_id, radius_miles, limit_count)
-- Uses PostGIS geography for true distance. Returns distance in miles.
-- ---------------------------------------------------------------------------
create or replace function public.nearby_properties(
  p_property_id uuid,
  p_radius_miles double precision default 1.0,
  p_limit int default 20
)
returns table (
  id uuid,
  parcel_id text,
  address_line1 text,
  distance_miles double precision
)
language sql
stable
as $$
  select
    p2.id,
    p2.parcel_id,
    p2.address_line1,
    (st_distance(
      p1.centroid::geography,
      p2.centroid::geography
    ) / 1609.344) as distance_miles
  from public.properties p1
  join public.properties p2
    on p2.id <> p1.id
    and p2.centroid is not null
  where p1.id = p_property_id
    and p1.centroid is not null
    and st_dwithin(
      p1.centroid::geography,
      p2.centroid::geography,
      p_radius_miles * 1609.344
    )
  order by distance_miles asc
  limit least(greatest(p_limit, 1), 100);
$$;

-- ---------------------------------------------------------------------------
-- Function: next First Tuesday sale date helper (for UI convenience ONLY).
-- Georgia foreclosure sales occur on the first Tuesday of the month.
-- This function is for filtering / display convenience. It NEVER creates
-- a sale_date for a notice — sale_date always comes from the published notice.
-- ---------------------------------------------------------------------------
create or replace function public.first_tuesday_of_month(p_year int, p_month int)
returns date
language sql
immutable
as $$
  select (
    date_trunc('month', make_date(p_year, p_month, 1))
    + ((2 - extract(dow from date_trunc('month', make_date(p_year, p_month, 1))) + 7) % 7) * interval '1 day'
  )::date;
$$;

comment on function public.properties_in_bbox(double precision, double precision, double precision, double precision, text)
  is 'Map bbox query. Returns only rows with real centroids; never invents geometry.';
comment on function public.nearby_properties(uuid, double precision, int)
  is 'Nearby parcels by true PostGIS geography distance. For comps / map click.';
comment on function public.first_tuesday_of_month(int, int)
  is 'Display/filter helper only. NEVER use to create a notice sale_date.';

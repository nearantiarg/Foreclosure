export interface Provenance {
  source_name: string;
  source_url: string;
  retrieved_at?: string | null;
  first_seen_at?: string | null;
}

export interface County {
  id: string;
  county_name: string;
  county_fips: string;
  state: string;
  legal_organ_name?: string | null;
  legal_organ_url?: string | null;
  is_active: boolean;
}

export interface Property {
  id: string;
  county_id: string;
  county_name?: string | null;
  parcel_id: string;
  parcel_id_normalized?: string | null;
  address_line1?: string | null;
  address_line2?: string | null;
  city?: string | null;
  state?: string | null;
  zip?: string | null;
  owner_name?: string | null;
  property_type?: string | null;
  year_built?: number | null;
  living_area_sqft?: number | null;
  lot_acres?: number | null;
  bedrooms?: number | null;
  bathrooms?: number | null;
  assessed_value?: number | null;
  appraised_value?: number | null;
  tax_year?: number | null;
  latitude?: number | null;
  longitude?: number | null;
  centroid?: { type: string; coordinates: [number, number] } | null;
  assessor_url?: string | null;
  first_seen_at?: string | null;
  last_seen_at?: string | null;
  provenance?: Provenance | null;
  // Convenience: backend may flatten provenance fields
  source_name?: string | null;
  source_url?: string | null;
}

export interface ForeclosureNotice {
  id: string;
  property_id?: string | null;
  county_id: string;
  county_name?: string | null;
  source_name: string;
  source_url: string;
  source_record_id: string;
  notice_type: string;
  grantor_name?: string | null;
  grantee_name?: string | null;
  original_loan_amount?: number | null;
  deed_book?: string | null;
  deed_page?: string | null;
  instrument_number?: string | null;
  legal_description?: string | null;
  sale_date: string;
  sale_location?: string | null;
  publication_start_date?: string | null;
  publication_end_date?: string | null;
  publication_weeks?: number | null;
  notice_text?: string | null;
  status: string;
  first_seen_at?: string | null;
  last_seen_at?: string | null;
  provenance?: Provenance | null;
}

export interface AuctionEvent {
  id: string;
  county_id: string;
  county_name?: string | null;
  property_id?: string | null;
  notice_id?: string | null;
  sale_date: string;
  sale_time?: string | null;
  sale_location: string;
  sale_type: string;
  status: string;
  opening_bid?: number | null;
  winning_bid?: number | null;
  buyer_name?: string | null;
  result_source_url?: string | null;
  result_retrieved_at?: string | null;
  first_seen_at?: string | null;
  property?: Property | null;
  provenance?: Provenance | null;
  source_name?: string | null;
  source_url?: string | null;
}

export interface PropertyEvent {
  id: string;
  property_id: string;
  event_type: string;
  event_date: string;
  title: string;
  description?: string | null;
  source_name?: string | null;
  source_url?: string | null;
  payload?: Record<string, unknown> | null;
  created_at?: string | null;
}

export interface DocumentRecord {
  id: string;
  property_id?: string | null;
  county_id: string;
  instrument_number?: string | null;
  deed_book?: string | null;
  deed_page?: string | null;
  document_type: string;
  grantor_name?: string | null;
  grantee_name?: string | null;
  recorded_date?: string | null;
  consideration_amount?: number | null;
  source_name: string;
  source_url?: string | null;
}

export interface ComparableSale {
  id: string;
  subject_property_id: string;
  comp_address: string;
  sale_date: string;
  sale_price: number;
  distance_miles?: number | null;
  similarity_score?: number | null;
  source_name: string;
  source_url?: string | null;
  license_status: string;
}

export interface PropertyDetail extends Property {
  notices: ForeclosureNotice[];
  auctions: AuctionEvent[];
  events: PropertyEvent[];
  documents: DocumentRecord[];
  comparable_sales: ComparableSale[];
}

export interface AnalyticsOverview {
  total_properties: number;
  active_notices: number;
  upcoming_auctions: number;
  sales_last_30d: number;
  last_ingestion_at?: string | null;
}

export interface SourceHealth {
  id: string;
  source_key: string;
  display_name: string;
  county_id?: string | null;
  source_type: string;
  base_url: string;
  is_enabled: boolean;
  license_status: string;
  expected_cadence?: string | null;
  last_successful_run_at?: string | null;
  health?: {
    status: string;
    last_check_at?: string | null;
    consecutive_failures: number;
    last_error?: string | null;
  } | null;
  status?: string;
  last_check_at?: string | null;
  consecutive_failures?: number;
  last_error?: string | null;
}

export interface IngestionRun {
  id: string;
  source_id: string;
  source_key?: string | null;
  started_at: string;
  finished_at?: string | null;
  status: string;
  pages_fetched: number;
  records_seen: number;
  records_inserted: number;
  records_updated: number;
  records_skipped: number;
  records_failed: number;
  high_water_mark?: string | null;
  error_message?: string | null;
  triggered_by?: string | null;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface PropertyFilters {
  county?: string;
  q?: string;
  city?: string;
  zip?: string;
  property_type?: string;
  min_price?: string;
  max_price?: string;
  has_notice?: string;
  has_auction?: string;
  sale_date_from?: string;
  sale_date_to?: string;
  page?: string;
  per_page?: string;
  bbox?: string;
  sort?: string;
}

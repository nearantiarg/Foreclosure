import type {
  AnalyticsOverview,
  AuctionEvent,
  County,
  ForeclosureNotice,
  IngestionRun,
  Paginated,
  Property,
  PropertyDetail,
  PropertyFilters,
  SourceHealth,
} from "./types";

const FASTAPI_BASE =
  process.env.NEXT_PUBLIC_FASTAPI_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

function buildQuery(params: Record<string, string | undefined>): string {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "" && v !== "all") qs.set(k, v);
  }
  const s = qs.toString();
  return s ? `?${s}` : "";
}

async function fetchJson<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${FASTAPI_BASE}${path}`, {
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

function emptyPage<T>(): Paginated<T> {
  return { items: [], total: 0, page: 1, per_page: 20, total_pages: 0 };
}

function normalizePage<T>(data: unknown): Paginated<T> {
  if (!data) return emptyPage<T>();
  if (Array.isArray(data)) {
    return {
      items: data as T[],
      total: data.length,
      page: 1,
      per_page: data.length || 20,
      total_pages: 1,
    };
  }
  const d = data as Partial<Paginated<T>> & {
    results?: T[];
    // Backend envelope variants: { sources: [] }, { counties: [] }, { groups: [] }, { runs: [] }
    sources?: T[];
    counties?: T[];
    groups?: T[];
    runs?: T[];
  };
  const items = d.items ?? d.results ?? d.sources ?? d.counties ?? d.groups ?? d.runs ?? [];
  return {
    items,
    total: d.total ?? items.length,
    page: d.page ?? 1,
    per_page: d.per_page ?? 20,
    total_pages: d.total_pages ?? (Math.ceil((d.total ?? 0) / (d.per_page ?? 20)) || 0),
  };
}

// Backend sometimes returns { <key>: [] } envelopes instead of bare arrays.
// Always return an array — never undefined — so pages can safely .find/.map.
function extractArray<T>(data: unknown, keys: string[]): T[] {
  if (!data) return [];
  if (Array.isArray(data)) return data as T[];
  const d = data as Record<string, unknown>;
  for (const k of keys) {
    if (Array.isArray(d[k])) return d[k] as T[];
  }
  if (Array.isArray(d.items)) return d.items as T[];
  if (Array.isArray(d.results)) return d.results as T[];
  return [];
}

export async function getCounties(): Promise<County[]> {
  const data = await fetchJson<unknown>("/counties");
  return extractArray<County>(data, ["counties"]);
}

export async function getProperties(
  filters: PropertyFilters = {},
): Promise<Paginated<Property>> {
  const data = await fetchJson<unknown>(
    `/properties${buildQuery(filters as Record<string, string | undefined>)}`,
  );
  return normalizePage<Property>(data);
}

export async function getProperty(id: string): Promise<PropertyDetail | null> {
  return fetchJson<PropertyDetail>(
    `/properties/${encodeURIComponent(id)}`,
  );
}

export async function getNotices(params: {
  county?: string;
  sale_date_from?: string;
  sale_date_to?: string;
  status?: string;
  page?: string;
  per_page?: string;
} = {}): Promise<Paginated<ForeclosureNotice>> {
  const data = await fetchJson<unknown>(
    `/notices${buildQuery(params as Record<string, string | undefined>)}`,
  );
  return normalizePage<ForeclosureNotice>(data);
}

export async function getAuctions(params: {
  county?: string;
  sale_date_from?: string;
  sale_date_to?: string;
  status?: string;
  page?: string;
  per_page?: string;
} = {}): Promise<Paginated<AuctionEvent>> {
  const data = await fetchJson<unknown>(
    `/auctions${buildQuery(params as Record<string, string | undefined>)}`,
  );
  return normalizePage<AuctionEvent>(data);
}

export async function getUpcomingAuctions(): Promise<AuctionEvent[]> {
  const data = await fetchJson<unknown>("/auctions/upcoming");
  // /auctions/upcoming returns { groups: [...] } where each group has auctions.
  // Flatten groups to a plain list; fall back to bare array / items.
  if (data && typeof data === "object" && !Array.isArray(data)) {
    const d = data as { groups?: Array<{ auctions?: AuctionEvent[] }> };
    if (Array.isArray(d.groups)) {
      return d.groups.flatMap((g) => (Array.isArray(g.auctions) ? g.auctions : []));
    }
  }
  return extractArray<AuctionEvent>(data, ["auctions", "upcoming"]);
}

export async function getAnalyticsOverview(
  county?: string,
): Promise<AnalyticsOverview | null> {
  return fetchJson<AnalyticsOverview>(
    `/analytics/overview${buildQuery({ county })}`,
  );
}

export async function getSources(): Promise<SourceHealth[]> {
  const data = await fetchJson<unknown>("/sources");
  return extractArray<SourceHealth>(data, ["sources"]);
}

export async function getSourceHealth(): Promise<SourceHealth[]> {
  const data = await fetchJson<unknown>("/health/sources");
  return extractArray<SourceHealth>(data, ["sources"]);
}

export async function getIngestionRuns(
  sourceKey?: string,
  limit = 20,
): Promise<IngestionRun[]> {
  const data = await fetchJson<unknown>(
    `/ingestion/runs${buildQuery({
      source_key: sourceKey,
      limit: String(limit),
    })}`,
  );
  return extractArray<IngestionRun>(data, ["runs"]);
}

export function formatMoney(n?: number | null): string {
  if (n === null || n === undefined) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);
}

export function formatDate(d?: string | null): string {
  if (!d) return "—";
  const parsed = new Date(d.length <= 10 ? `${d}T12:00:00` : d);
  if (Number.isNaN(parsed.getTime())) return d;
  return parsed.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function formatDateTime(d?: string | null): string {
  if (!d) return "Unknown";
  const parsed = new Date(d);
  if (Number.isNaN(parsed.getTime())) return d;
  return parsed.toLocaleString("en-US");
}

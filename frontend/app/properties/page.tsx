import Link from "next/link";
import { Suspense } from "react";
import { getProperties } from "@/lib/api";
import type { PropertyFilters } from "@/lib/types";
import PropertyCard from "@/components/PropertyCard";
import SearchFilters from "@/components/SearchFilters";
import EmptyState from "@/components/EmptyState";
import LoadingSkeleton from "@/components/LoadingSkeleton";

export default async function PropertiesPage({
  searchParams,
}: {
  searchParams: Record<string, string | undefined>;
}) {
  const filters: PropertyFilters = {
    county: searchParams.county,
    q: searchParams.q,
    city: searchParams.city,
    zip: searchParams.zip,
    property_type: searchParams.property_type,
    min_price: searchParams.min_price,
    max_price: searchParams.max_price,
    has_notice: searchParams.has_notice,
    has_auction: searchParams.has_auction,
    sale_date_from: searchParams.sale_date_from,
    sale_date_to: searchParams.sale_date_to,
    page: searchParams.page ?? "1",
    per_page: searchParams.per_page ?? "20",
  };
  const view = searchParams.view === "map" ? "map" : "list";
  const page = Number(filters.page ?? "1") || 1;
  const result = await getProperties(filters);

  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(searchParams)) {
    if (v && k !== "page") qs.set(k, v);
  }
  const baseQs = qs.toString();
  const prevHref = page > 1 ? `/properties?${baseQs}${baseQs ? "&" : ""}page=${page - 1}` : null;
  const nextHref =
    page < result.total_pages ? `/properties?${baseQs}${baseQs ? "&" : ""}page=${page + 1}` : null;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="text-2xl font-bold">Properties</h1>
        <div className="flex gap-2 text-sm">
          <Link href={`/properties?${baseQs}`} className={view === "list" ? "font-semibold underline" : "text-brand-600 underline"}>List</Link>
          <Link href={`/map?${baseQs}`} className="text-brand-600 underline">Map view</Link>
        </div>
      </div>

      <Suspense fallback={<LoadingSkeleton />}>
        <SearchFilters />
      </Suspense>

      <p role="status" className="text-sm text-gray-600">
        {result.total.toLocaleString("en-US")} verified propert{result.total === 1 ? "y" : "ies"} found
        {result.total > 0 ? ` — page ${result.page} of ${Math.max(result.total_pages, 1)}` : ""}
      </p>

      {result.items.length === 0 ? (
        <EmptyState
          lastIngestion={null}
          source="assessor / legal organ"
          action={<Link href="/sources" className="text-brand-600 underline">Check source status</Link>}
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {result.items.map((p) => (
            <PropertyCard key={p.id} property={p} />
          ))}
        </div>
      )}

      {(prevHref || nextHref) && (
        <nav aria-label="Pagination" className="flex items-center gap-3">
          {prevHref ? (
            <Link href={prevHref} className="rounded-md border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50">Previous</Link>
          ) : (
            <span className="rounded-md border border-gray-200 px-3 py-1.5 text-sm text-gray-400">Previous</span>
          )}
          <span className="text-sm text-gray-600">Page {page} of {Math.max(result.total_pages, 1)}</span>
          {nextHref ? (
            <Link href={nextHref} className="rounded-md border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50">Next</Link>
          ) : (
            <span className="rounded-md border border-gray-200 px-3 py-1.5 text-sm text-gray-400">Next</span>
          )}
        </nav>
      )}
    </div>
  );
}

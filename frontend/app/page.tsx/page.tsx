import Link from "next/link";
import { getAnalyticsOverview, getSources, getUpcomingAuctions, formatDate } from "@/lib/api";
import EmptyState from "@/components/EmptyState";
import StatusBadge from "@/components/StatusBadge";
import Provenance from "@/components/Provenance";

export default async function HomePage() {
  const [overview, sourcesRaw, upcomingRaw] = await Promise.all([
    getAnalyticsOverview(),
    getSources(),
    getUpcomingAuctions(),
  ]);
  const sources = sourcesRaw ?? [];
  const upcoming = upcomingRaw ?? [];

  const hasData = overview !== null;
  const lastIngestion =
    overview?.last_ingestion_at ??
    sources.find((s) => s.last_successful_run_at)?.last_successful_run_at ??
    null;

  return (
    <div className="space-y-8">
      <section>
        <h1 className="text-3xl font-bold">Georgia foreclosure records, verified at the source</h1>
        <p className="mt-2 max-w-2xl text-gray-600">
          Actual property records, verified foreclosure notices, auction events, and historical
          changes from public sources in Forsyth and Fulton Counties.
        </p>
        <form action="/properties" method="get" className="mt-4 flex max-w-xl gap-2" role="search">
          <label htmlFor="home-q" className="sr-only">Search address, parcel, or owner</label>
          <input
            id="home-q"
            name="q"
            placeholder="Search address, parcel, or owner"
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-600 focus:outline-none"
          />
          <button type="submit" className="shrink-0 rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700">
            Search
          </button>
        </form>
      </section>

      <section aria-label="Overview">
        <h2 className="text-xl font-semibold">Overview</h2>
        {!hasData ? (
          <div className="mt-3">
            <EmptyState
              lastIngestion={lastIngestion}
              source={sources[0]?.display_name ?? "none yet"}
              action={<Link href="/sources" className="text-brand-600 underline">View source status</Link>}
            />
          </div>
        ) : (
          <dl className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {[
              { label: "Properties in database", value: overview!.total_properties },
              { label: "Active foreclosure notices", value: overview!.active_notices },
              { label: "Upcoming auctions", value: overview!.upcoming_auctions },
              { label: "Sales (last 30 days)", value: overview!.sales_last_30d },
            ].map((stat) => (
              <div key={stat.label} className="rounded-lg border border-gray-200 bg-white p-4">
                <dt className="text-sm text-gray-500">{stat.label}</dt>
                <dd className="mt-1 text-3xl font-bold">{stat.value.toLocaleString("en-US")}</dd>
              </div>
            ))}
          </dl>
        )}
        {overview?.last_ingestion_at ? (
          <p className="mt-2 text-xs text-gray-500">
            Last ingestion: {new Date(overview.last_ingestion_at).toLocaleString("en-US")}
          </p>
        ) : null}
      </section>

      <section aria-label="Upcoming auctions">
        <div className="flex items-baseline justify-between">
          <h2 className="text-xl font-semibold">Upcoming auctions</h2>
          <Link href="/auctions" className="text-sm text-brand-600 underline">View all auctions</Link>
        </div>
        {upcoming.length === 0 ? (
          <div className="mt-3">
            <EmptyState title="No upcoming auctions found" lastIngestion={lastIngestion} source="county auction lists" />
          </div>
        ) : (
          <ul className="mt-3 divide-y divide-gray-200 rounded-lg border border-gray-200 bg-white">
            {upcoming.slice(0, 10).map((a) => (
              <li key={a.id} className="flex flex-wrap items-center justify-between gap-2 px-4 py-3">
                <div>
                  <p className="font-medium">
                    {a.property?.address_line1 ?? `Parcel ${a.property?.parcel_id ?? "unknown"}`} — {a.county_name ?? ""}
                  </p>
                  <p className="text-sm text-gray-500">{a.sale_location}</p>
                  <Provenance sourceName={a.source_name} sourceUrl={a.source_url ?? a.result_source_url} retrievedAt={a.first_seen_at} />
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{formatDate(a.sale_date)}</span>
                  <StatusBadge status={a.status} />
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-label="Source status">
        <div className="flex items-baseline justify-between">
          <h2 className="text-xl font-semibold">Source status</h2>
          <Link href="/sources" className="text-sm text-brand-600 underline">View all sources</Link>
        </div>
        {sources.length === 0 ? (
          <div className="mt-3">
            <EmptyState title="No sources configured yet" lastIngestion={null} source="none yet" />
          </div>
        ) : (
          <ul className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {sources.map((s) => (
              <li key={s.id} className="rounded-lg border border-gray-200 bg-white p-4">
                <div className="flex items-center justify-between gap-2">
                  <p className="font-medium">{s.display_name}</p>
                  <StatusBadge status={s.health?.status ?? s.status ?? "unknown"} />
                </div>
                <p className="mt-1 text-sm text-gray-500">
                  License: {s.license_status}
                  {s.last_successful_run_at ? ` • Last success: ${new Date(s.last_successful_run_at).toLocaleString("en-US")}` : ""}
                </p>
                <a href={s.base_url} target="_blank" rel="noreferrer" className="text-xs text-brand-600 underline">
                  View source ↗
                </a>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

import Link from "next/link";
import { getAuctions, formatDate } from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";
import Provenance from "@/components/Provenance";
import EmptyState from "@/components/EmptyState";

export default async function AuctionsPage({
  searchParams,
}: {
  searchParams: Record<string, string | undefined>;
}) {
  const result = await getAuctions({
    county: searchParams.county,
    sale_date_from: searchParams.sale_date_from,
    sale_date_to: searchParams.sale_date_to,
    status: searchParams.status,
    page: searchParams.page ?? "1",
    per_page: "100",
  });

  const grouped = new Map<string, typeof result.items>();
  for (const a of result.items) {
    const key = a.sale_date;
    grouped.set(key, [...(grouped.get(key) ?? []), a]);
  }
  const sortedDates = [...grouped.keys()].sort();

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Auction calendar</h1>
      <form method="get" className="flex flex-wrap gap-2 rounded-lg border border-gray-200 bg-white p-4">
        <label className="sr-only" htmlFor="county">County</label>
        <select id="county" name="county" defaultValue={searchParams.county ?? "all"} className="rounded-md border border-gray-300 px-3 py-2 text-sm">
          <option value="all">All counties</option>
          <option value="Forsyth">Forsyth</option>
          <option value="Fulton">Fulton</option>
        </select>
        <label className="sr-only" htmlFor="sale_date_from">Sale date from</label>
        <input id="sale_date_from" name="sale_date_from" type="date" defaultValue={searchParams.sale_date_from ?? ""} className="rounded-md border border-gray-300 px-3 py-2 text-sm" />
        <label className="sr-only" htmlFor="sale_date_to">Sale date to</label>
        <input id="sale_date_to" name="sale_date_to" type="date" defaultValue={searchParams.sale_date_to ?? ""} className="rounded-md border border-gray-300 px-3 py-2 text-sm" />
        <label className="sr-only" htmlFor="status">Status</label>
        <select id="status" name="status" defaultValue={searchParams.status ?? "all"} className="rounded-md border border-gray-300 px-3 py-2 text-sm">
          <option value="all">All statuses</option>
          <option value="scheduled">Scheduled</option>
          <option value="postponed">Postponed</option>
          <option value="cancelled">Cancelled</option>
          <option value="sold">Sold</option>
          <option value="unknown">Unknown</option>
        </select>
        <button type="submit" className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700">Filter</button>
      </form>

      <p role="status" className="text-sm text-gray-600">{result.total.toLocaleString("en-US")} auction event{result.total === 1 ? "" : "s"} found</p>

      {result.items.length === 0 ? (
        <EmptyState lastIngestion={null} source="county auction lists" />
      ) : (
        sortedDates.map((date) => (
          <section key={date} aria-label={`Auctions on ${date}`}>
            <h2 className="text-lg font-semibold">{formatDate(date)}</h2>
            <ul className="mt-2 divide-y divide-gray-200 rounded-lg border border-gray-200 bg-white">
              {grouped.get(date)!.map((a) => (
                <li key={a.id} className="flex flex-wrap items-center justify-between gap-2 px-4 py-3">
                  <div>
                    {a.property_id ? (
                      <Link href={`/properties/${a.property_id}`} className="font-medium text-brand-700 hover:underline">
                        {a.property?.address_line1 ?? `Property ${a.property_id}`}
                      </Link>
                    ) : (
                      <span className="font-medium">Property match pending</span>
                    )}
                    <p className="text-sm text-gray-500">{a.county_name ?? ""} • {a.sale_location} • {a.sale_type}</p>
                    <Provenance sourceName={a.source_name} sourceUrl={a.source_url ?? a.result_source_url} retrievedAt={a.first_seen_at} />
                  </div>
                  <StatusBadge status={a.status} />
                </li>
              ))}
            </ul>
          </section>
        ))
      )}
    </div>
  );
}

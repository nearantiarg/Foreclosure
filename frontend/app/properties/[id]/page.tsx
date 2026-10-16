import { notFound } from "next/navigation";
import dynamic from "next/dynamic";
import Link from "next/link";
import { getProperty, formatDate, formatMoney } from "@/lib/api";
import Provenance from "@/components/Provenance";
import StatusBadge from "@/components/StatusBadge";
import EmptyState from "@/components/EmptyState";

const MapView = dynamic(() => import("@/components/MapView"), { ssr: false });

export default async function PropertyDetailPage({ params }: { params: { id: string } }) {
  const property = await getProperty(params.id);
  if (!property) notFound();
  // Backend may omit empty arrays — never crash on .length/.map.
  property.events = property.events ?? [];
  property.notices = property.notices ?? [];
  property.auctions = property.auctions ?? [];
  property.documents = property.documents ?? [];
  property.comparable_sales = property.comparable_sales ?? [];

  const address = [property.address_line1, property.address_line2, property.city, property.state, property.zip]
    .filter(Boolean)
    .join(", ");
  const hasCoords =
    (property.latitude != null && property.longitude != null) || Boolean(property.centroid);

  const facts: [string, string][] = [
    ["Parcel ID", property.parcel_id],
    ["County", property.county_name ?? "—"],
    ["Owner (as published)", property.owner_name ?? "—"],
    ["Property type", property.property_type ?? "—"],
    ["Year built", property.year_built != null ? String(property.year_built) : "—"],
    ["Living area", property.living_area_sqft ? `${property.living_area_sqft} sq ft` : "—"],
    ["Lot", property.lot_acres != null ? `${property.lot_acres} acres` : "—"],
    ["Bedrooms / Bathrooms", `${property.bedrooms ?? "—"} / ${property.bathrooms ?? "—"}`],
    ["Assessed value", formatMoney(property.assessed_value)],
    ["Appraised value", formatMoney(property.appraised_value)],
    ["Tax year", property.tax_year != null ? String(property.tax_year) : "—"],
  ];

  const pendingComps =
    property.comparable_sales.length === 0 ||
    property.comparable_sales.every((c) => c.license_status === "PENDING_LICENSE");

  return (
    <article className="space-y-6">
      <div>
        <Link href="/properties" className="text-sm text-brand-600 underline">← Back to properties</Link>
        <h1 className="mt-2 text-2xl font-bold">{address || `Parcel ${property.parcel_id}`}</h1>
        <p className="mt-1 text-sm text-gray-600">
          {property.county_name ?? ""} • Parcel {property.parcel_id}
        </p>
        <div className="mt-2">
          <Provenance
            provenance={property.provenance}
            sourceName={property.source_name}
            sourceUrl={property.source_url ?? property.assessor_url}
            retrievedAt={property.first_seen_at}
          />
        </div>
      </div>

      <section aria-label="Property facts" className="rounded-lg border border-gray-200 bg-white p-4">
        <h2 className="text-lg font-semibold">Property facts</h2>
        <dl className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {facts.map(([k, v]) => (
            <div key={k}>
              <dt className="text-xs text-gray-500">{k}</dt>
              <dd className="text-sm font-medium">{v}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section aria-label="Map">
        <h2 className="text-lg font-semibold">Map</h2>
        <div className="mt-2">
          {hasCoords ? (
            <MapView properties={[property]} zoom={15} />
          ) : (
            <EmptyState title="No coordinates published for this parcel" message="The source record for this property does not include coordinates yet." lastIngestion={property.last_seen_at} source="assessor" />
          )}
        </div>
      </section>

      <section aria-label="Timeline">
        <h2 className="text-lg font-semibold">Timeline</h2>
        {property.events.length === 0 ? (
          <div className="mt-2"><EmptyState title="No historical events yet" lastIngestion={property.last_seen_at} source="ingestion" /></div>
        ) : (
          <ol className="mt-2 space-y-2">
            {property.events.map((e) => (
              <li key={e.id} className="rounded-lg border border-gray-200 bg-white p-3">
                <p className="text-sm font-medium">{e.title} — {formatDate(e.event_date)}</p>
                {e.description ? <p className="text-sm text-gray-600">{e.description}</p> : null}
                <Provenance sourceName={e.source_name} sourceUrl={e.source_url} />
              </li>
            ))}
          </ol>
        )}
      </section>

      <section aria-label="Foreclosure notices">
        <h2 className="text-lg font-semibold">Foreclosure notices</h2>
        {property.notices.length === 0 ? (
          <div className="mt-2"><EmptyState title="No verified foreclosure notices for this property" lastIngestion={property.last_seen_at} source="legal organ" /></div>
        ) : (
          <div className="mt-2 space-y-3">
            {property.notices.map((n) => (
              <article key={n.id} className="rounded-lg border border-gray-200 bg-white p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="font-semibold">{n.notice_type}</h3>
                  <StatusBadge status={n.status} />
                </div>
                <p className="mt-1 text-sm text-gray-600">
                  Sale date: {formatDate(n.sale_date)} • Sale location: {n.sale_location ?? "—"}
                </p>
                <p className="text-sm text-gray-600">
                  Grantor: {n.grantor_name ?? "—"} • Grantee: {n.grantee_name ?? "—"}
                  {n.deed_book ? ` • Deed ${n.deed_book}/${n.deed_page ?? ""}` : ""}
                </p>
                <p className="text-sm text-gray-600">
                  Publication: {formatDate(n.publication_start_date)} – {formatDate(n.publication_end_date)}
                  {n.publication_weeks ? ` (${n.publication_weeks} weeks)` : ""}
                </p>
                {n.notice_text ? (
                  <blockquote className="mt-2 whitespace-pre-wrap border-l-2 border-gray-200 pl-3 text-sm text-gray-700">
                    {n.notice_text}
                  </blockquote>
                ) : null}
                <div className="mt-2"><Provenance provenance={n.provenance} sourceName={n.source_name} sourceUrl={n.source_url} retrievedAt={n.first_seen_at} /></div>
              </article>
            ))}
          </div>
        )}
      </section>

      <section aria-label="Auctions">
        <h2 className="text-lg font-semibold">Auctions</h2>
        {property.auctions.length === 0 ? (
          <div className="mt-2"><EmptyState title="No auction events for this property" lastIngestion={property.last_seen_at} source="county auction lists" /></div>
        ) : (
          <ul className="mt-2 space-y-2">
            {property.auctions.map((a) => (
              <li key={a.id} className="rounded-lg border border-gray-200 bg-white p-3">
                <div className="flex flex-wrap justify-between gap-2">
                  <span className="font-medium">{formatDate(a.sale_date)} — {a.sale_location}</span>
                  <StatusBadge status={a.status} />
                </div>
                <p className="text-sm text-gray-600">
                  Type: {a.sale_type} • Opening bid: {formatMoney(a.opening_bid)} • Winning bid: {formatMoney(a.winning_bid)}
                </p>
                <Provenance sourceName={a.source_name} sourceUrl={a.source_url ?? a.result_source_url} retrievedAt={a.first_seen_at} />
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-label="Documents">
        <h2 className="text-lg font-semibold">Document records</h2>
        {property.documents.length === 0 ? (
          <div className="mt-2"><EmptyState title="No document records for this property" lastIngestion={property.last_seen_at} source="GSCCCA / clerk" /></div>
        ) : (
          <ul className="mt-2 divide-y divide-gray-200 rounded-lg border border-gray-200 bg-white">
            {property.documents.map((d) => (
              <li key={d.id} className="px-4 py-3 text-sm">
                <span className="font-medium">{d.document_type}</span> — recorded {formatDate(d.recorded_date)}
                {d.instrument_number ? ` • Instrument ${d.instrument_number}` : ""}
                {d.deed_book ? ` • Book ${d.deed_book} Page ${d.deed_page ?? ""}` : ""}
                <Provenance sourceName={d.source_name} sourceUrl={d.source_url} />
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-label="Comparable sales">
        <h2 className="text-lg font-semibold">Comparable sales</h2>
        {pendingComps ? (
          <div className="mt-2 rounded-lg border border-purple-200 bg-purple-50 p-4">
            <p className="text-sm font-medium text-purple-900">Comparable sales via MLS — pending license</p>
            <p className="mt-1 text-sm text-purple-800">
              No licensed comparable-sales data is available yet. No synthetic comps are shown.
              {property.comparable_sales.length > 0
                ? ` ${property.comparable_sales.length} public-record sale(s) are listed below.`
                : ""}
            </p>
          </div>
        ) : null}
        {property.comparable_sales.filter((c) => c.license_status !== "PENDING_LICENSE").length > 0 ? (
          <ul className="mt-2 space-y-2">
            {property.comparable_sales
              .filter((c) => c.license_status !== "PENDING_LICENSE")
              .map((c) => (
                <li key={c.id} className="rounded-lg border border-gray-200 bg-white p-3 text-sm">
                  <span className="font-medium">{c.comp_address}</span> — {formatMoney(c.sale_price)} on {formatDate(c.sale_date)}
                  {c.distance_miles != null ? ` • ${c.distance_miles} mi` : ""}
                  <Provenance sourceName={c.source_name} sourceUrl={c.source_url} />
                </li>
              ))}
          </ul>
        ) : null}
      </section>

      <section aria-label="Provenance" className="rounded-lg border border-gray-200 bg-white p-4">
        <h2 className="text-lg font-semibold">Provenance</h2>
        <div className="mt-2">
          <Provenance provenance={property.provenance} sourceName={property.source_name} sourceUrl={property.source_url ?? property.assessor_url} retrievedAt={property.first_seen_at} />
        </div>
        <p className="mt-1 text-xs text-gray-500">
          First seen: {property.first_seen_at ? new Date(property.first_seen_at).toLocaleString("en-US") : "—"} •
          Last seen: {property.last_seen_at ? new Date(property.last_seen_at).toLocaleString("en-US") : "—"}
        </p>
      </section>
    </article>
  );
}

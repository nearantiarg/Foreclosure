import Link from "next/link";
import type { Property } from "@/lib/types";
import { formatMoney } from "@/lib/api";
import Provenance from "./Provenance";
import StatusBadge from "./StatusBadge";

export default function PropertyCard({ property }: { property: Property }) {
  const address = [property.address_line1, property.city, property.state, property.zip]
    .filter(Boolean)
    .join(", ");
  return (
    <article className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-base font-semibold">
          <Link
            href={`/properties/${property.id}`}
            className="text-brand-700 hover:underline"
          >
            {address || `Parcel ${property.parcel_id}`}
          </Link>
        </h3>
        {property.property_type ? <StatusBadge status={property.property_type.toLowerCase()} /> : null}
      </div>
      <dl className="mt-2 grid grid-cols-2 gap-2 text-sm text-gray-700">
        <div>
          <dt className="text-xs text-gray-500">County</dt>
          <dd>{property.county_name ?? "—"}</dd>
        </div>
        <div>
          <dt className="text-xs text-gray-500">Parcel ID</dt>
          <dd>{property.parcel_id}</dd>
        </div>
        <div>
          <dt className="text-xs text-gray-500">Owner (as published)</dt>
          <dd>{property.owner_name ?? "—"}</dd>
        </div>
        <div>
          <dt className="text-xs text-gray-500">Assessed value</dt>
          <dd>{formatMoney(property.assessed_value)}</dd>
        </div>
        <div>
          <dt className="text-xs text-gray-500">Year built</dt>
          <dd>{property.year_built ?? "—"}</dd>
        </div>
        <div>
          <dt className="text-xs text-gray-500">Living area</dt>
          <dd>{property.living_area_sqft ? `${property.living_area_sqft} sq ft` : "—"}</dd>
        </div>
      </dl>
      <div className="mt-3">
        <Provenance
          provenance={property.provenance}
          sourceName={property.source_name}
          sourceUrl={property.source_url ?? property.assessor_url}
          retrievedAt={property.first_seen_at}
        />
      </div>
    </article>
  );
}

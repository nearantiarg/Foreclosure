import dynamic from "next/dynamic";
import { getProperties } from "@/lib/api";
import EmptyState from "@/components/EmptyState";

const MapView = dynamic(() => import("@/components/MapView"), { ssr: false });

export default async function MapPage({
  searchParams,
}: {
  searchParams: Record<string, string | undefined>;
}) {
  // Georgia-wide default bbox; honours ?bbox= when supplied.
  const bbox = searchParams.bbox ?? "-85.6,30.3,-80.8,35.0";
  const result = await getProperties({
    bbox,
    county: searchParams.county,
    q: searchParams.q,
    page: "1",
    per_page: "100",
  });

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Map</h1>
      <p className="text-sm text-gray-600">
        Parcels from the live API ({result.total.toLocaleString("en-US")} total for current filters;
        showing up to 100). Markers appear only for records with coordinates from the source.
      </p>
      {result.items.length === 0 ? (
        <EmptyState lastIngestion={null} source="assessor / PostGIS" />
      ) : (
        <MapView properties={result.items} />
      )}
      <p className="text-xs text-gray-500">
        Basemap: OpenStreetMap contributors / CARTO. No paid map key required.
      </p>
    </div>
  );
}

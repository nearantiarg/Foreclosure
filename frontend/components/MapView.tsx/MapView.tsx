"use client";

import { useEffect } from "react";
import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import Link from "next/link";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { Property } from "@/lib/types";

interface MapViewProps {
  properties: Property[];
  center?: [number, number];
  zoom?: number;
}

function getLatLng(p: Property): [number, number] | null {
  if (p.latitude != null && p.longitude != null) return [p.latitude, p.longitude];
  if (p.centroid?.coordinates) {
    const [lng, lat] = p.centroid.coordinates;
    return [lat, lng];
  }
  return null;
}

export default function MapView({
  properties,
  center = [34.05, -84.2],
  zoom = 9,
}: MapViewProps) {
  useEffect(() => {
    // Fix default Leaflet marker icons (missing in Next.js bundling).
    // Use CDN icons so no local image assets are required.
    const DefaultIcon = L.Icon.Default;
    DefaultIcon.mergeOptions({
      iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
      iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
      shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
    });
  }, []);

  const withCoords = properties
    .map((p) => ({ property: p, latlng: getLatLng(p) }))
    .filter((x): x is { property: Property; latlng: [number, number] } => x.latlng !== null);

  return (
    <div className="h-[560px] w-full overflow-hidden rounded-lg border border-gray-200">
      <MapContainer center={center} zoom={zoom} style={{ height: "100%", width: "100%" }} scrollWheelZoom>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        />
        {withCoords.map(({ property, latlng }) => (
          <Marker key={property.id} position={latlng}>
            <Popup>
              <div>
                <p className="font-semibold">
                  {property.address_line1 ?? `Parcel ${property.parcel_id}`}
                </p>
                <p className="text-sm text-gray-600">
                  {property.county_name ?? ""} • Parcel {property.parcel_id}
                </p>
                <Link href={`/properties/${property.id}`} className="text-sm text-blue-700 underline">
                  View detail
                </Link>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
      {withCoords.length === 0 ? (
        <p className="p-3 text-sm text-gray-500">
          No mapped parcels in this result set — markers appear only for records with coordinates from the source.
        </p>
      ) : null}
    </div>
  );
}

"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

export default function SearchFilters() {
  const router = useRouter();
  const params = useSearchParams();
  const [q, setQ] = useState(params.get("q") ?? "");
  const [county, setCounty] = useState(params.get("county") ?? "all");
  const [city, setCity] = useState(params.get("city") ?? "");
  const [zip, setZip] = useState(params.get("zip") ?? "");
  const [propertyType, setPropertyType] = useState(params.get("property_type") ?? "all");
  const [minPrice, setMinPrice] = useState(params.get("min_price") ?? "");
  const [maxPrice, setMaxPrice] = useState(params.get("max_price") ?? "");
  const [hasNotice, setHasNotice] = useState(params.get("has_notice") ?? "");
  const [hasAuction, setHasAuction] = useState(params.get("has_auction") ?? "");
  const [saleFrom, setSaleFrom] = useState(params.get("sale_date_from") ?? "");
  const [saleTo, setSaleTo] = useState(params.get("sale_date_to") ?? "");

  function apply(e: React.FormEvent) {
    e.preventDefault();
    const qs = new URLSearchParams();
    if (q) qs.set("q", q);
    if (county && county !== "all") qs.set("county", county);
    if (city) qs.set("city", city);
    if (zip) qs.set("zip", zip);
    if (propertyType && propertyType !== "all") qs.set("property_type", propertyType);
    if (minPrice) qs.set("min_price", minPrice);
    if (maxPrice) qs.set("max_price", maxPrice);
    if (hasNotice) qs.set("has_notice", hasNotice);
    if (hasAuction) qs.set("has_auction", hasAuction);
    if (saleFrom) qs.set("sale_date_from", saleFrom);
    if (saleTo) qs.set("sale_date_to", saleTo);
    router.push(`/properties?${qs.toString()}`);
  }

  const input =
    "w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600";
  const label = "block text-xs font-medium text-gray-700";

  return (
    <form onSubmit={apply} className="rounded-lg border border-gray-200 bg-white p-4">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <label htmlFor="q" className={label}>Search address / parcel / owner</label>
          <input id="q" className={input} value={q} onChange={(e) => setQ(e.target.value)} placeholder="Address, parcel, owner" />
        </div>
        <div>
          <label htmlFor="county" className={label}>County</label>
          <select id="county" className={input} value={county} onChange={(e) => setCounty(e.target.value)}>
            <option value="all">All counties</option>
            <option value="Forsyth">Forsyth</option>
            <option value="Fulton">Fulton</option>
          </select>
        </div>
        <div>
          <label htmlFor="city" className={label}>City</label>
          <input id="city" className={input} value={city} onChange={(e) => setCity(e.target.value)} />
        </div>
        <div>
          <label htmlFor="zip" className={label}>ZIP</label>
          <input id="zip" className={input} value={zip} onChange={(e) => setZip(e.target.value)} inputMode="numeric" />
        </div>
        <div>
          <label htmlFor="property_type" className={label}>Property type</label>
          <select id="property_type" className={input} value={propertyType} onChange={(e) => setPropertyType(e.target.value)}>
            <option value="all">All types</option>
            <option value="Single Family">Single Family</option>
            <option value="Condo">Condo</option>
            <option value="Land">Land</option>
            <option value="Commercial">Commercial</option>
          </select>
        </div>
        <div>
          <label htmlFor="min_price" className={label}>Min assessed value</label>
          <input id="min_price" className={input} type="number" min="0" value={minPrice} onChange={(e) => setMinPrice(e.target.value)} />
        </div>
        <div>
          <label htmlFor="max_price" className={label}>Max assessed value</label>
          <input id="max_price" className={input} type="number" min="0" value={maxPrice} onChange={(e) => setMaxPrice(e.target.value)} />
        </div>
        <div>
          <label htmlFor="has_notice" className={label}>Has foreclosure notice</label>
          <select id="has_notice" className={input} value={hasNotice} onChange={(e) => setHasNotice(e.target.value)}>
            <option value="">Any</option>
            <option value="true">Yes</option>
            <option value="false">No</option>
          </select>
        </div>
        <div>
          <label htmlFor="has_auction" className={label}>Has auction</label>
          <select id="has_auction" className={input} value={hasAuction} onChange={(e) => setHasAuction(e.target.value)}>
            <option value="">Any</option>
            <option value="true">Yes</option>
            <option value="false">No</option>
          </select>
        </div>
        <div>
          <label htmlFor="sale_date_from" className={label}>Sale date from</label>
          <input id="sale_date_from" className={input} type="date" value={saleFrom} onChange={(e) => setSaleFrom(e.target.value)} />
        </div>
        <div>
          <label htmlFor="sale_date_to" className={label}>Sale date to</label>
          <input id="sale_date_to" className={input} type="date" value={saleTo} onChange={(e) => setSaleTo(e.target.value)} />
        </div>
      </div>
      <div className="mt-4 flex gap-2">
        <button type="submit" className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700">
          Apply filters
        </button>
        <button
          type="button"
          onClick={() => router.push("/properties")}
          className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium hover:bg-gray-50"
        >
          Clear
        </button>
      </div>
    </form>
  );
}

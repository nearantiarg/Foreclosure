import type { Provenance as ProvenanceType } from "@/lib/types";
import { formatDateTime } from "@/lib/api";

interface ProvenanceProps {
  provenance?: ProvenanceType | null;
  sourceName?: string | null;
  sourceUrl?: string | null;
  retrievedAt?: string | null;
}

export default function Provenance({
  provenance,
  sourceName,
  sourceUrl,
  retrievedAt,
}: ProvenanceProps) {
  const name = provenance?.source_name ?? sourceName;
  const url = provenance?.source_url ?? sourceUrl;
  const retrieved = provenance?.retrieved_at ?? provenance?.first_seen_at ?? retrievedAt;
  if (!name && !url) return null;
  return (
    <p className="text-xs text-gray-500">
      Source: {name ?? "Unknown"}
      {url ? (
        <>
          {" • "}
          <a
            href={url}
            target="_blank"
            rel="noreferrer"
            className="text-brand-600 underline hover:text-brand-700"
          >
            View source ↗
          </a>
        </>
      ) : null}
      {retrieved ? <> • Retrieved {formatDateTime(retrieved)}</> : null}
    </p>
  );
}

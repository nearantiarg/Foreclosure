import { getSources, getIngestionRuns } from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";
import EmptyState from "@/components/EmptyState";

export default async function SourcesPage() {
  const [sourcesRaw, runsRaw] = await Promise.all([getSources(), getIngestionRuns(undefined, 20)]);
  const sources = sourcesRaw ?? [];
  const runs = runsRaw ?? [];
  const runBySource = new Map(runs.map((r) => [r.source_id, r]));

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Source health</h1>
      {sources.length === 0 ? (
        <EmptyState title="No sources configured yet" lastIngestion={null} source="none yet" />
      ) : (
        <ul className="grid gap-4 md:grid-cols-2">
          {sources.map((s) => {
            const healthStatus = s.health?.status ?? s.status ?? "unknown";
            const lastRun = runBySource.get(s.id);
            return (
              <li key={s.id} className="rounded-lg border border-gray-200 bg-white p-4">
                <div className="flex items-center justify-between gap-2">
                  <h2 className="font-semibold">{s.display_name}</h2>
                  <StatusBadge status={healthStatus} />
                </div>
                <dl className="mt-2 space-y-1 text-sm text-gray-600">
                  <div><dt className="inline text-gray-500">Key: </dt><dd className="inline">{s.source_key}</dd></div>
                  <div><dt className="inline text-gray-500">Type: </dt><dd className="inline">{s.source_type}</dd></div>
                  <div><dt className="inline text-gray-500">License: </dt><dd className="inline">{s.license_status}</dd></div>
                  <div><dt className="inline text-gray-500">Cadence: </dt><dd className="inline">{s.expected_cadence ?? "—"}</dd></div>
                  <div><dt className="inline text-gray-500">Last success: </dt><dd className="inline">{s.last_successful_run_at ? new Date(s.last_successful_run_at).toLocaleString("en-US") : "Never"}</dd></div>
                  {s.health?.consecutive_failures ? (
                    <div><dt className="inline text-gray-500">Consecutive failures: </dt><dd className="inline">{s.health.consecutive_failures}</dd></div>
                  ) : null}
                </dl>
                {lastRun ? (
                  <p className="mt-2 text-sm text-gray-600">
                    Last run: {lastRun.status} • seen {lastRun.records_seen} • inserted {lastRun.records_inserted} • updated {lastRun.records_updated} • skipped {lastRun.records_skipped} • failed {lastRun.records_failed}
                  </p>
                ) : null}
                {(s.health?.last_error ?? s.last_error) ? (
                  <p className="mt-2 rounded bg-red-50 p-2 text-sm text-red-700">
                    Last error: {s.health?.last_error ?? s.last_error}
                  </p>
                ) : null}
                <a href={s.base_url} target="_blank" rel="noreferrer" className="mt-2 inline-block text-sm text-brand-600 underline">
                  View source ↗
                </a>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

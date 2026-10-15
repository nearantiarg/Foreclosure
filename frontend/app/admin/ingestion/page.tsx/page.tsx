"use client";

import { useCallback, useEffect, useState } from "react";
import StatusBadge from "@/components/StatusBadge";

interface SourceRow {
  id: string;
  source_key: string;
  display_name: string;
  license_status: string;
}
interface RunRow {
  id: string;
  source_id: string;
  started_at: string;
  status: string;
  records_seen: number;
  records_inserted: number;
  records_failed: number;
  error_message?: string | null;
}

export default function AdminIngestionPage() {
  const [sources, setSources] = useState<SourceRow[]>([]);
  const [runs, setRuns] = useState<RunRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [adminToken, setAdminToken] = useState<string>("");

  const load = useCallback(async () => {
    try {
      const base = process.env.NEXT_PUBLIC_FASTAPI_BASE_URL?.replace(/\/$/, "") || "http://localhost:8000";
      const [sRes, rRes] = await Promise.all([
        fetch(`${base}/sources`, { cache: "no-store" }),
        fetch(`${base}/ingestion/runs?limit=20`, { cache: "no-store" }),
      ]);
      if (sRes.ok) {
        const data = await sRes.json();
        setSources(Array.isArray(data) ? data : data.items ?? []);
      }
      if (rRes.ok) {
        const data = await rRes.json();
        setRuns(Array.isArray(data) ? data : data.items ?? []);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load admin data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function trigger(sourceKey: string) {
    setTriggering(sourceKey);
    setNotice(null);
    setError(null);
    try {
      // Calls the Next.js server route, which holds the ingestion secret server-side.
      // The browser never sees INGESTION_SECRET.
      const res = await fetch("/api/admin/ingestion", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(adminToken ? { "X-Admin-Token": adminToken } : {}),
        },
        body: JSON.stringify({ source_key: sourceKey, mode: "incremental" }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(data.detail ?? `Trigger failed (${res.status})`);
      } else {
        setNotice(`Ingestion triggered for ${sourceKey}: ${data.status ?? "accepted"} (run ${data.run_id ?? "unknown"})`);
        await load();
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Trigger failed");
    } finally {
      setTriggering(null);
    }
  }

  if (loading) return <p role="status">Loading…</p>;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Admin — Ingestion</h1>
      <p className="text-sm text-gray-600">
        Triggers go through a server-side route that holds the ingestion secret. The browser never
        receives it. If ADMIN_TOKEN is set on the server, enter it below — it is sent only as a
        header to the server route and is not stored.
      </p>
      <label className="block text-sm">
        <span className="text-gray-700">Admin token (if configured on server)</span>
        <input
          type="password"
          value={adminToken}
          onChange={(e) => setAdminToken(e.target.value)}
          placeholder="Leave blank if ADMIN_TOKEN is not set"
          className="mt-1 block w-full max-w-sm rounded-md border border-gray-300 px-3 py-2"
          autoComplete="off"
        />
      </label>
      {notice ? <p role="status" className="rounded bg-green-50 p-3 text-sm text-green-800">{notice}</p> : null}
      {error ? <p role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}

      <section aria-label="Sources">
        <h2 className="text-lg font-semibold">Sources</h2>
        {sources.length === 0 ? (
          <p className="mt-2 text-sm text-gray-500">No sources returned by the API.</p>
        ) : (
          <ul className="mt-2 space-y-2">
            {sources.map((s) => (
              <li key={s.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-gray-200 bg-white p-3">
                <div>
                  <p className="font-medium">{s.display_name}</p>
                  <p className="text-sm text-gray-500">{s.source_key} • License: {s.license_status}</p>
                </div>
                <button
                  type="button"
                  disabled={triggering === s.source_key || s.license_status === "PENDING_LICENSE"}
                  onClick={() => trigger(s.source_key)}
                  className="rounded-md bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
                >
                  {triggering === s.source_key ? "Triggering…" : "Run ingestion"}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-label="Recent runs">
        <h2 className="text-lg font-semibold">Recent runs</h2>
        {runs.length === 0 ? (
          <p className="mt-2 text-sm text-gray-500">No ingestion runs yet.</p>
        ) : (
          <ul className="mt-2 divide-y divide-gray-200 rounded-lg border border-gray-200 bg-white">
            {runs.map((r) => (
              <li key={r.id} className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 text-sm">
                <span>{new Date(r.started_at).toLocaleString("en-US")} • seen {r.records_seen} • inserted {r.records_inserted} • failed {r.records_failed}</span>
                <StatusBadge status={r.status} />
                {r.error_message ? <p className="w-full text-red-700">{r.error_message}</p> : null}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

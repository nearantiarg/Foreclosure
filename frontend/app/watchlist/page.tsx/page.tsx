"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { supabase, isSupabaseConfigured } from "@/lib/supabase";
import EmptyState from "@/components/EmptyState";

interface WatchItem {
  id: string;
  property_id: string;
  created_at: string;
}

export default function WatchlistPage() {
  const [userId, setUserId] = useState<string | null>(null);
  const [items, setItems] = useState<WatchItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      if (!isSupabaseConfigured) {
        setLoading(false);
        return;
      }
      const { data } = await supabase.auth.getSession();
      const uid = data.session?.user.id ?? null;
      setUserId(uid);
      if (!uid) {
        setLoading(false);
        return;
      }
      const { data: rows, error: err } = await supabase
        .from("watchlist")
        .select("id, property_id, created_at")
        .order("created_at", { ascending: false });
      if (err) setError(err.message);
      else setItems((rows ?? []) as WatchItem[]);
      setLoading(false);
    }
    load();
  }, []);

  if (loading) return <p role="status">Loading…</p>;

  if (!isSupabaseConfigured || !userId) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">Watchlist</h1>
        <EmptyState
          title="Sign in to use watchlist"
          message="Your watchlist is tied to your account and enforced by Row Level Security. Sign in to view saved properties."
          lastIngestion={null}
          source="Supabase Auth"
          action={<Link href="/properties" className="text-brand-600 underline">Browse properties</Link>}
        />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">Watchlist</h1>
        <p role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Watchlist</h1>
      {items.length === 0 ? (
        <EmptyState
          title="No saved properties yet"
          message="Save properties from their detail pages (once signed in) and they will appear here. No demo entries are shown."
          lastIngestion={null}
          source="watchlist"
          action={<Link href="/properties" className="text-brand-600 underline">Browse properties</Link>}
        />
      ) : (
        <ul className="space-y-2">
          {items.map((item) => (
            <li key={item.id} className="rounded-lg border border-gray-200 bg-white p-3">
              <Link href={`/properties/${item.property_id}`} className="text-brand-700 hover:underline">
                View property
              </Link>
              <p className="text-sm text-gray-500">Saved {new Date(item.created_at).toLocaleString("en-US")}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

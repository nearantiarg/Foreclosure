import { NextRequest, NextResponse } from "next/server";

// Server-only route: holds INGESTION_SECRET (no NEXT_PUBLIC_ prefix).
// The browser never sees the secret; this route forwards it to FastAPI.
// Minimal admin gate: if ADMIN_TOKEN is set, the caller must send
// X-Admin-Token matching it. This is a stopgap until full Supabase
// Auth + admin-role gating lands — do NOT expose /admin publicly
// without either ADMIN_TOKEN or Supabase admin-role checks.
export async function POST(req: NextRequest) {
  const adminToken = process.env.ADMIN_TOKEN;
  if (adminToken && req.headers.get("x-admin-token") !== adminToken) {
    return NextResponse.json({ detail: "Admin token required." }, { status: 401 });
  }
  const secret = process.env.INGESTION_SECRET;
  if (!secret) {
    return NextResponse.json(
      { detail: "Ingestion is not configured on the server (INGESTION_SECRET missing)." },
      { status: 503 },
    );
  }
  let body: { source_key?: string; mode?: string } = {};
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ detail: "Invalid JSON body." }, { status: 400 });
  }
  if (!body.source_key) {
    return NextResponse.json({ detail: "source_key is required." }, { status: 422 });
  }
  const base =
    process.env.NEXT_PUBLIC_FASTAPI_BASE_URL?.replace(/\/$/, "") || "http://localhost:8000";
  const qs = new URLSearchParams({
    source_key: body.source_key,
    mode: body.mode ?? "incremental",
  });
  try {
    const res = await fetch(`${base}/ingestion/run?${qs.toString()}`, {
      method: "POST",
      headers: { "X-Ingestion-Secret": secret },
    });
    const data = await res.json().catch(() => ({}));
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ detail: "FastAPI backend unreachable." }, { status: 502 });
  }
}

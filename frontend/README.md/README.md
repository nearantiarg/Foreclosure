# Georgia Foreclosure Platform — Frontend

Data-first Next.js 14 App Router + TypeScript strict + Tailwind CSS.

No mock listings, no hardcoded stats, no fake comps. Every number/card comes
from the FastAPI backend (`NEXT_PUBLIC_FASTAPI_BASE_URL`) or Supabase
(anon key only, RLS enforced). When the backend returns no rows, pages show an
honest empty state.

## Run

```bash
npm install
cp .env.example .env.local  # fill in real values
npm run dev    # http://localhost:3000
npm run build
npm run test
npm run typecheck
```

## Env

See `.env.example`. Never put a service-role key in this app — there is no
`NEXT_PUBLIC_*SERVICE*` variable. The ingestion trigger goes through
`app/api/admin/ingestion/route.ts`, which reads the server-only
`INGESTION_SECRET` and forwards it to FastAPI. The browser never sees it.

## Routes

/ — live overview, upcoming auctions, search, source-status strip
/properties — search + filters + list/map toggle + pagination
/properties/[id] — detail, timeline, notices, auctions, documents, comps
/auctions — calendar grouped by sale_date
/map — Leaflet map from /properties?bbox=
/sources — source health dashboard
/watchlist — Supabase Auth, RLS; sign-in required
/admin/ingestion — admin-gated trigger + recent runs (server-side secret)

Disclaimer: Public-record information only; not legal advice. Verify with the
county clerk / legal organ before acting.

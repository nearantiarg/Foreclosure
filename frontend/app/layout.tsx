import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Georgia Foreclosure Platform",
  description:
    "Verified Georgia foreclosure notices, auction events, and property records from public sources.",
};

const NAV = [
  { href: "/", label: "Home" },
  { href: "/properties", label: "Properties" },
  { href: "/auctions", label: "Auctions" },
  { href: "/map", label: "Map" },
  { href: "/sources", label: "Sources" },
  { href: "/watchlist", label: "Watchlist" },
  { href: "/admin/ingestion", label: "Admin" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="border-b border-gray-200 bg-white">
          <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3">
            <Link href="/" className="text-lg font-bold text-brand-700">
              Georgia Foreclosure Platform
            </Link>
            <nav aria-label="Main">
              <ul className="flex flex-wrap gap-1">
                {NAV.map((item) => (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className="rounded-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 hover:text-gray-900"
                    >
                      {item.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
        <footer className="border-t border-gray-200 bg-white">
          <div className="mx-auto max-w-7xl px-4 py-4 text-sm text-gray-500">
            <p>
              Public-record information only; not legal advice. Verify with the county clerk /
              legal organ before acting.
            </p>
            <p className="mt-1">
              Coverage: Forsyth &amp; Fulton Counties, GA at launch — expanding to all 159 Georgia
              counties.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}

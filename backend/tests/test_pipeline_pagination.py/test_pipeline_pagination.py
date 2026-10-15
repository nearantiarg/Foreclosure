"""Pagination: multi-page fixture → all pages fetched, stop on empty page."""
from app.ingestion.connectors.forsyth_legal_organ import ForsythLegalOrganConnector
from app.ingestion.pipeline import run_pipeline


class _MultiPageConnector(ForsythLegalOrganConnector):
    def __init__(self, pages):
        super().__init__()
        self._pages = pages

    def list_page_urls(self, mode="incremental", since=None):
        return list(self._pages.keys())

    def fetch_url(self, url, headers=None):
        return 200, self._pages[url], {}


def test_pagination_fetches_all_pages_then_stops(fixture_html, memory_store):
    html = fixture_html("forsyth_legal_notice_sample.html")
    pages = {"https://example.test/p1": html, "https://example.test/p2": html, "https://example.test/p3": "<html><body>No notices here</body></html>"}
    c = _MultiPageConnector(pages)
    r = run_pipeline(c, memory_store, mode="full")
    # p1: 2 inserted, p2: same 2 → skipped (dedupe by hash), p3: empty → stop
    assert r["pages_fetched"] == 3, r
    assert r["records_seen"] == 4, r
    assert r["records_inserted"] == 2, r

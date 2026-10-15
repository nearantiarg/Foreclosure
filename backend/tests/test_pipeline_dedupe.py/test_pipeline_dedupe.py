"""Dedupe: same record twice → 1 stored row + skipped count on re-run."""
from app.ingestion.connectors.forsyth_legal_organ import ForsythLegalOrganConnector
from app.ingestion.pipeline import run_pipeline


class _OnePageConnector(ForsythLegalOrganConnector):
    def __init__(self, html):
        super().__init__()
        self._html = html

    def list_page_urls(self, mode="incremental", since=None):
        return ["https://example.test/legal?page=1"]

    def fetch_url(self, url, headers=None):
        return 200, self._html, {}


def test_dedupe_same_record_twice(fixture_html, memory_store):
    html = fixture_html("forsyth_legal_notice_sample.html")
    c1 = _OnePageConnector(html)
    r1 = run_pipeline(c1, memory_store, mode="full")
    assert r1["records_inserted"] == 2, r1
    c2 = _OnePageConnector(html)
    r2 = run_pipeline(c2, memory_store, mode="incremental")
    assert r2["records_inserted"] == 0
    assert r2["records_skipped"] == 2, r2

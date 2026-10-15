"""Incremental: second run with no new records → 0 inserts."""
from app.ingestion.connectors.forsyth_legal_organ import ForsythLegalOrganConnector
from app.ingestion.pipeline import run_pipeline


class _StaticConnector(ForsythLegalOrganConnector):
    def __init__(self, html):
        super().__init__()
        self._html = html

    def list_page_urls(self, mode="incremental", since=None):
        return ["https://example.test/legal"]

    def fetch_url(self, url, headers=None):
        return 200, self._html, {}


def test_incremental_no_new_records(fixture_html, memory_store):
    html = fixture_html("forsyth_legal_notice_sample.html")
    r1 = run_pipeline(_StaticConnector(html), memory_store, mode="full")
    assert r1["records_inserted"] == 2
    r2 = run_pipeline(_StaticConnector(html), memory_store, mode="incremental")
    assert r2["records_inserted"] == 0
    assert r2["records_updated"] == 0

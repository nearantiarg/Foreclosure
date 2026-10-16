"""API: all endpoints return 200 (or honest empty) + 404/422 cases."""
from unittest.mock import MagicMock, patch


def test_all_list_endpoints_200(client):
    for path in ["/counties", "/properties", "/notices", "/auctions", "/auctions/upcoming", "/sources", "/ingestion/runs", "/health/sources"]:
        r = client.get(path)
        assert r.status_code == 200, (path, r.status_code, r.text)


def test_analytics_overview_200(client):
    r = client.get("/analytics/overview")
    assert r.status_code == 200
    body = r.json()
    for key in ("total_properties", "active_notices", "upcoming_auctions", "sales_last_30d"):
        assert key in body


def test_property_404(client):
    r = client.get("/properties/00000000-0000-0000-0000-000000000000")
    assert r.status_code in (404, 503)


def test_bbox_422(client):
    r = client.get("/properties?bbox=not-a-bbox")
    assert r.status_code == 422
    r2 = client.get("/properties?bbox=1,2,3")
    assert r2.status_code == 422


def test_price_range_422(client):
    r = client.get("/properties?min_price=500&max_price=100")
    assert r.status_code == 422


def test_ingestion_requires_secret(client):
    r = client.post("/ingestion/run?source_key=forsyth_legal_organ&mode=incremental")
    assert r.status_code == 401


def test_ingestion_unknown_source_with_secret(client):
    r = client.post("/ingestion/run?source_key=nope&mode=incremental", headers={"X-Ingestion-Secret": "test-secret"})
    assert r.status_code == 404


def test_ingestion_bad_mode(client):
    r = client.post("/ingestion/run?source_key=forsyth_legal_organ&mode=bogus", headers={"X-Ingestion-Secret": "test-secret"})
    assert r.status_code == 422


def test_mls_pending_raises_license():
    from app.ingestion.connectors.mls_pending import MLSPendingConnector
    from app.schemas import LicenseRequiredError

    c = MLSPendingConnector()
    try:
        c.check_license()
        raise AssertionError("should have raised")
    except LicenseRequiredError:
        pass

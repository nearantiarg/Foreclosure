def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert "status" in body and "db" in body and "postgis" in body


def test_ready_endpoint(client):
    r = client.get("/ready")
    assert r.status_code == 200
    assert "ready" in r.json()

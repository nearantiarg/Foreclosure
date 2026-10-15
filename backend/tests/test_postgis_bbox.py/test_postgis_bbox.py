"""PostGIS bbox: logic test with mocked DB — verifies the SQL uses ST_Within + envelope.

Real PostGIS integration requires SUPABASE_DB_URL; this test proves the query
construction is correct without needing a live DB.
"""
from unittest.mock import MagicMock, patch

from app.api.properties import build_bbox_sql, parse_bbox


def test_parse_bbox_valid():
    assert parse_bbox("-84.5,34.0,-84.0,34.5") == (-84.5, 34.0, -84.0, 34.5)


def test_build_bbox_sql_uses_st_within():
    sql = build_bbox_sql((-84.5, 34.0, -84.0, 34.5))
    assert "ST_Within" in sql
    assert "ST_MakeEnvelope(-84.5,34.0,-84.0,34.5,4326)" in sql


def test_build_bbox_sql_empty_when_none():
    assert build_bbox_sql(None) == ""


def test_bbox_query_filters_via_db_mock(client):
    # Mock get_db_connection to return a fake conn whose cursor yields one row inside bbox
    fake_cur = MagicMock()
    fake_cur.description = [("id",), ("centroid",)]
    fake_cur.fetchall.return_value = [("prop-1", None)]
    fake_cur.__enter__ = lambda s: s
    fake_cur.__exit__ = lambda *a: None
    fake_conn = MagicMock()
    fake_conn.cursor.return_value = fake_cur
    fake_conn.close.return_value = None
    with patch("app.api.properties.get_db_connection", return_value=fake_conn):
        r = client.get("/properties?bbox=-84.5,34.0,-84.0,34.5")
        assert r.status_code == 200
        assert r.json()["properties"]
        # Verify the executed SQL contained ST_Within
        executed = " ".join(str(c) for c in fake_cur.execute.call_args_list)
        assert "ST_Within" in executed

"""Pytest fixtures. Fixtures live ONLY under tests/fixtures/ and are NEVER served as prod data."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure backend/ is on sys.path so `app.*` imports work from any cwd.
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("SUPABASE_URL", "")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "")
os.environ.setdefault("SUPABASE_DB_URL", "")
os.environ.setdefault("INGESTION_SECRET", "test-secret")


@pytest.fixture()
def client():
    from app.main import app

    return TestClient(app)


@pytest.fixture()
def fixture_html():
    def _load(name: str) -> str:
        return (Path(__file__).parent / "fixtures" / name).read_text(encoding="utf-8")

    return _load


@pytest.fixture()
def memory_store():
    from app.ingestion.pipeline import InMemoryStore

    return InMemoryStore()

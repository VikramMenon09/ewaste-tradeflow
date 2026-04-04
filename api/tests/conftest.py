"""
Shared pytest fixtures for the EWasteTradeFlow API test suite.

Uses FastAPI's TestClient with dependency overrides to avoid requiring a real
database or Redis instance.  All database interactions are replaced with simple
async mocks that return realistic fixture data.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.database import get_db
from app.services.cache import cache_service


# ── Fixture data ──────────────────────────────────────────────────────────────

COUNTRY_ROWS = [
    {
        "iso3": "DEU",
        "name": "Germany",
        "region": "Europe",
        "subregion": "Western Europe",
        "income_classification": "high",
        "basel_signatory": True,
        "basel_ban_ratified": True,
        "is_oecd_member": True,
    },
    {
        "iso3": "NGA",
        "name": "Nigeria",
        "region": "Africa",
        "subregion": "Western Africa",
        "income_classification": "lower_middle",
        "basel_signatory": True,
        "basel_ban_ratified": False,
        "is_oecd_member": False,
    },
]


def _make_country_obj(data: dict):
    """Build a mock SQLAlchemy ORM object from a plain dict."""
    obj = MagicMock()
    for k, v in data.items():
        setattr(obj, k, v)
    return obj


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def mock_db():
    """Async mock for the SQLAlchemy session dependency."""
    db = AsyncMock()

    # Default: scalars().all() returns country rows
    result = MagicMock()
    result.scalars.return_value.all.return_value = [
        _make_country_obj(row) for row in COUNTRY_ROWS
    ]
    result.scalar_one_or_none.return_value = _make_country_obj(COUNTRY_ROWS[0])
    db.execute.return_value = result
    return db


@pytest.fixture(autouse=True)
def mock_cache(monkeypatch):
    """Replace cache_service with a no-op to avoid Redis dependency."""
    monkeypatch.setattr(cache_service, "get", AsyncMock(return_value=None))
    monkeypatch.setattr(cache_service, "set", AsyncMock(return_value=None))
    monkeypatch.setattr(cache_service, "connect", AsyncMock(return_value=None))
    monkeypatch.setattr(cache_service, "close", AsyncMock(return_value=None))


@pytest.fixture()
def client(mock_db):
    """TestClient with database dependency overridden."""
    app = create_app()

    async def _override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

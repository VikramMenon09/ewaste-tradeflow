"""
Integration-style tests for the EWasteTradeFlow API routers.

These tests exercise the HTTP layer (routing, request parsing, response shape,
status codes) using a mock database session — no real PostgreSQL or Redis
required.  They catch: wrong route registration, broken schemas, missing
required fields in responses, and basic authentication guard behavior.
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.conftest import COUNTRY_ROWS, _make_country_obj


# ── /health ───────────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_returns_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert "env" in body


# ── /api/v1/countries ─────────────────────────────────────────────────────────

class TestCountries:
    def test_list_returns_200_with_schema(self, client):
        r = client.get("/api/v1/countries")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        # Check required fields on first item
        item = data[0]
        for field in ("iso3", "name", "region", "basel_signatory", "is_oecd_member"):
            assert field in item, f"Missing field: {field}"

    def test_list_accepts_region_filter(self, client):
        r = client.get("/api/v1/countries", params={"region": "Europe"})
        # Endpoint should accept the param without error (mocked DB returns all rows)
        assert r.status_code == 200

    def test_single_country_returns_200(self, client):
        r = client.get("/api/v1/countries/DEU")
        assert r.status_code == 200
        body = r.json()
        assert body["iso3"] == "DEU"

    def test_single_country_404_on_not_found(self, client, mock_db):
        # Make the DB return nothing for the scalar query
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result

        r = client.get("/api/v1/countries/ZZZ")
        assert r.status_code == 404


# ── /api/v1/export/csv ────────────────────────────────────────────────────────

class TestExport:
    def test_csv_export_requires_type_param(self, client):
        # Missing 'type' query param should return 422 Unprocessable Entity
        r = client.get("/api/v1/export/csv")
        assert r.status_code == 422

    def test_csv_export_with_generation_type(self, client, mock_db):
        # Set up mock to return generation records
        row = MagicMock()
        row.country_iso3 = "DEU"
        row.year = 2022
        row.category_code = None
        row.total_mt = 1234.5
        row.per_capita_kg = 14.8
        row.formal_collection_rate = 0.43
        row.confidence_tier = "reported"
        row.is_interpolated = False

        result = MagicMock()
        result.scalars.return_value.all.return_value = [row]
        mock_db.execute.return_value = result

        r = client.get("/api/v1/export/csv", params={"type": "generation"})
        assert r.status_code == 200
        assert "text/csv" in r.headers.get("content-type", "")


# ── /api/v1/reports ───────────────────────────────────────────────────────────

class TestReports:
    def test_generate_returns_202_with_job_id(self, client, mock_db):
        # Mock the DB insert + commit
        mock_db.execute.return_value = MagicMock()
        mock_db.commit = AsyncMock()

        r = client.post(
            "/api/v1/reports/generate",
            json={"report_type": "global", "params": {"year": 2022}},
        )
        assert r.status_code == 202
        body = r.json()
        assert "job_id" in body
        assert "poll_url" in body
        assert "estimated_wait_seconds" in body

    def test_generate_rejects_invalid_report_type(self, client):
        r = client.post(
            "/api/v1/reports/generate",
            json={"report_type": "invalid_type", "params": {}},
        )
        assert r.status_code == 422

    def test_poll_returns_404_for_unknown_job(self, client, mock_db):
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result

        fake_id = str(uuid.uuid4())
        r = client.get(f"/api/v1/reports/{fake_id}")
        assert r.status_code == 404

    def test_poll_returns_job_status(self, client, mock_db):
        job = MagicMock()
        job.id = uuid.uuid4()
        job.status = "queued"
        job.output_url = None
        job.output_expires_at = None
        job.error_message = None
        job.created_at = None
        job.completed_at = None

        result = MagicMock()
        result.scalar_one_or_none.return_value = job
        mock_db.execute.return_value = result

        r = client.get(f"/api/v1/reports/{job.id}")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "queued"
        assert "job_id" in body


# ── /api/v1/embed ─────────────────────────────────────────────────────────────

class TestEmbed:
    def test_create_token_requires_auth(self, client):
        # No Authorization header — should return 401
        r = client.post(
            "/api/v1/embed/tokens",
            json={"label": "test"},
        )
        assert r.status_code == 401

    def test_list_tokens_requires_auth(self, client):
        r = client.get("/api/v1/embed/tokens")
        assert r.status_code == 401


# ── /api/v1/saved-states ──────────────────────────────────────────────────────

class TestSavedStates:
    def test_list_saved_states_requires_auth(self, client):
        r = client.get("/api/v1/saved-states")
        assert r.status_code == 401

    def test_create_saved_state_requires_auth(self, client):
        r = client.post(
            "/api/v1/saved-states",
            json={
                "name": "My saved view",
                "filter_state": {
                    "year": 2022,
                    "metric": "generation",
                    "region": [],
                    "category": [],
                    "compliantOnly": False,
                    "flaggedOnly": False,
                    "topN": 20,
                    "activeView": "map",
                },
            },
        )
        assert r.status_code == 401

"""Pydantic v2 request / response schemas for the EWasteTradeFlow API.

Each schema class maps to a specific API contract.  Schemas intentionally
do not inherit from the ORM models to keep the API surface stable even as
the database schema evolves.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Shared config ─────────────────────────────────────────────────────────────

class _Base(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ── Country ───────────────────────────────────────────────────────────────────

class CountryBasic(_Base):
    """Lightweight country reference returned by /countries list endpoint."""

    iso3: str
    name: str
    region: Optional[str] = None
    subregion: Optional[str] = None
    income_classification: Optional[str] = None
    basel_signatory: bool = False
    basel_ban_ratified: bool = False
    is_oecd_member: bool = False


# ── Generation ────────────────────────────────────────────────────────────────

class GenerationPoint(_Base):
    """Single year data point in a country's generation time-series."""

    year: int
    total_mt: Optional[float] = None
    per_capita_kg: Optional[float] = None
    formal_collection_rate: Optional[float] = None
    confidence_tier: Optional[str] = None
    data_vintage_year: Optional[int] = None
    is_interpolated: bool = False


# ── Trade partners ────────────────────────────────────────────────────────────

class TradePartner(_Base):
    """Summary of a single bilateral trade relationship."""

    partner_iso3: str
    partner_name: Optional[str] = None
    volume_mt: Optional[float] = None
    value_usd: Optional[float] = None
    basel_compliant: Optional[bool] = None
    prs_risk_flag: bool = False
    compliance_color: Optional[str] = None  # 'green' | 'amber' | 'red'


# ── Country profile ───────────────────────────────────────────────────────────

class CountryProfile(_Base):
    """Full country detail response including generation series and trade summary."""

    iso3: str
    name: str
    region: Optional[str] = None
    subregion: Optional[str] = None
    income_classification: Optional[str] = None
    basel_signatory: bool = False
    basel_ban_ratified: bool = False
    is_oecd_member: bool = False

    prs_score: Optional[float] = None
    prs_methodology_version: Optional[int] = None

    generation_series: list[GenerationPoint] = Field(default_factory=list)
    top_exports: list[TradePartner] = Field(default_factory=list)
    top_imports: list[TradePartner] = Field(default_factory=list)

    processing_capacity_mt: Optional[float] = None
    literature_flag_level: Optional[str] = None


# ── Choropleth ────────────────────────────────────────────────────────────────

class ChoroplethCountry(_Base):
    """Per-country value for a choropleth layer."""

    iso3: str
    name: str
    value: Optional[float] = None
    confidence_tier: Optional[str] = None
    data_vintage_year: Optional[int] = None
    is_missing: bool = False


class ChoroplethResponse(_Base):
    """Full choropleth dataset for a given metric and year."""

    year: int
    metric: str
    countries: list[ChoroplethCountry]


# ── Sankey ────────────────────────────────────────────────────────────────────

class SankeyNode(_Base):
    """A country node in the Sankey trade-flow diagram."""

    id: str  # iso3
    name: str
    region: Optional[str] = None


class SankeyLink(_Base):
    """A directional trade-flow link between two country nodes."""

    source: str  # exporter iso3
    target: str  # importer iso3
    volume_mt: Optional[float] = None
    value_usd: Optional[float] = None
    compliance_color: Literal["green", "amber", "red"] = "amber"
    has_violation: bool = False
    prs_risk_flag: bool = False
    importer_prs_score: Optional[float] = None
    data_conflict: bool = False
    confidence_tier: Optional[str] = None
    mapping_confidence: Optional[str] = None


class SankeyResponse(_Base):
    """Full Sankey diagram dataset for a given year and filter set."""

    year: int
    nodes: list[SankeyNode]
    links: list[SankeyLink]


# ── Report generation ─────────────────────────────────────────────────────────

class ReportGenerateRequest(_Base):
    """Request body for POST /reports/generate."""

    report_type: Literal["country_profile", "trade_route", "regional", "global"]
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary filter / display state forwarded to the renderer",
    )


class ReportGenerateResponse(_Base):
    """Immediate 202 response confirming job submission."""

    job_id: uuid.UUID
    poll_url: str
    estimated_wait_seconds: int = 30


class ReportStatusResponse(_Base):
    """Job status response returned by GET /reports/{job_id}."""

    job_id: uuid.UUID
    status: str
    download_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


# ── User saved states ─────────────────────────────────────────────────────────

class UserSavedStateCreate(_Base):
    """Request body for POST /user/saved-states."""

    name: str
    description: Optional[str] = None
    filter_state: dict[str, Any]
    is_default: bool = False


class UserSavedState(_Base):
    """Persisted map / filter state belonging to an authenticated user."""

    id: uuid.UUID
    name: str
    description: Optional[str] = None
    filter_state: dict[str, Any]
    is_default: bool = False
    created_at: datetime


# ── Flat record schemas (used by /export and /trade-flows endpoints) ───────────

class TradeFlowRecord(_Base):
    """Individual trade flow record as returned by the trade-flows list endpoint."""

    exporter_iso3: str
    importer_iso3: str
    year: int
    hs_code: Optional[str] = None
    ewaste_category_code: Optional[int] = None
    volume_mt: Optional[float] = None
    estimated_ewaste_volume_mt: Optional[float] = None
    value_usd: Optional[float] = None
    confidence_tier: Optional[str] = None
    mapping_confidence: Optional[str] = None
    basel_compliant: Optional[bool] = None
    prs_risk_flag: bool = False
    compliance_color: Optional[str] = None


class GenerationRecord(_Base):
    """Individual generation record as returned by the generation list endpoint."""

    country_iso3: str
    year: int
    category_code: Optional[int] = None
    total_mt: Optional[float] = None
    per_capita_kg: Optional[float] = None
    formal_collection_rate: Optional[float] = None
    confidence_tier: Optional[str] = None
    is_interpolated: bool = False

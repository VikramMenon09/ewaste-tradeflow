"""SQLAlchemy ORM models for all EWasteTradeFlow database tables.

Tables fall into three logical groups:
  1. Core reference/fact tables populated by the dbt pipeline
     (countries, ewaste_generation, trade_flows, processing_risk_scores,
      data_sources, pipeline_runs)
  2. Application tables managed by the API
     (async_jobs, user_saved_states, embed_tokens)
  3. dbt mart (pre-aggregated cache) tables — read-only from the API
     (mart_choropleth_cache, mart_sankey_cache)

PostGIS geometry columns are stored as Text with a type comment; to use full
GeoAlchemy2 features, swap the column type for geoalchemy2.types.Geometry.
"""

from __future__ import annotations

import uuid
from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    Boolean,
    BigInteger,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


# ── Helper ────────────────────────────────────────────────────────────────────

def _uuid_pk():
    """Return a UUID primary-key column defaulting to gen_random_uuid()."""
    return Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )


# ── 1. Reference / fact tables ────────────────────────────────────────────────

class Country(Base):
    """ISO 3166-1 alpha-3 country reference with Basel Convention membership
    flags and PostGIS geometry columns."""

    __tablename__ = "countries"

    iso3 = Column(String(3), primary_key=True)
    name = Column(String(255), nullable=False)
    region = Column(String(100))
    subregion = Column(String(100))
    un_member = Column(Boolean, default=False)
    basel_signatory = Column(Boolean, default=False)
    basel_ban_ratified = Column(Boolean, default=False)
    is_oecd_member = Column(Boolean, default=False)
    income_classification = Column(String(50))

    # PostGIS geometry columns — stored as TEXT to avoid a hard dependency on
    # GeoAlchemy2.  In production, these hold WKB/WKT geometry values.
    geometry = Column(Text, comment="PostGIS polygon (MultiPolygon)")
    geometry_simplified = Column(Text, comment="PostGIS polygon (simplified)")
    centroid = Column(Text, comment="PostGIS point")

    last_updated_at = Column(DateTime(timezone=True), server_default=text("now()"))

    # Relationships
    generation_records = relationship("EwasteGeneration", back_populates="country", lazy="noload")
    export_flows = relationship(
        "TradeFlow", foreign_keys="TradeFlow.exporter_iso3", back_populates="exporter", lazy="noload"
    )
    import_flows = relationship(
        "TradeFlow", foreign_keys="TradeFlow.importer_iso3", back_populates="importer", lazy="noload"
    )
    prs_scores = relationship("ProcessingRiskScore", back_populates="country", lazy="noload")


class EwasteGeneration(Base):
    """Annual e-waste generation estimates per country and category."""

    __tablename__ = "ewaste_generation"

    id = Column(Integer, primary_key=True, autoincrement=True)
    country_iso3 = Column(String(3), ForeignKey("countries.iso3"), nullable=False)
    year = Column(Integer, nullable=False)
    category_code = Column(Integer)
    total_mt = Column(Numeric(12, 2))
    per_capita_kg = Column(Numeric(8, 3))
    formal_collection_mt = Column(Numeric(12, 2))
    formal_collection_rate = Column(Numeric(5, 4))
    is_interpolated = Column(Boolean, default=False)
    data_vintage_year = Column(Integer)
    source_id = Column(Integer, ForeignKey("data_sources.id"))
    confidence_tier = Column(String(20))
    ingested_at = Column(DateTime(timezone=True), server_default=text("now()"))

    country = relationship("Country", back_populates="generation_records")
    data_source = relationship("DataSource", lazy="noload")


class TradeFlow(Base):
    """Bilateral trade flow records mapped to e-waste HS codes."""

    __tablename__ = "trade_flows"

    id = Column(Integer, primary_key=True, autoincrement=True)
    exporter_iso3 = Column(String(3), ForeignKey("countries.iso3"), nullable=False)
    importer_iso3 = Column(String(3), ForeignKey("countries.iso3"), nullable=False)
    year = Column(Integer, nullable=False)
    hs_code = Column(String(20))
    ewaste_category_code = Column(Integer)
    volume_mt = Column(Numeric(14, 2))
    estimated_ewaste_volume_mt = Column(Numeric(14, 2))
    value_usd = Column(Numeric(18, 2))
    source_id = Column(Integer, ForeignKey("data_sources.id"))
    confidence_tier = Column(String(20))
    mapping_confidence = Column(String(20))
    data_conflict = Column(Boolean, default=False)
    basel_compliant = Column(Boolean, nullable=True)
    prs_risk_flag = Column(Boolean, default=False)
    importer_prs_score = Column(Numeric(4, 2), nullable=True)
    informal_estimate = Column(Boolean, default=False)
    data_source = Column(String(100))
    ingested_at = Column(DateTime(timezone=True), server_default=text("now()"))

    exporter = relationship(
        "Country", foreign_keys=[exporter_iso3], back_populates="export_flows"
    )
    importer = relationship(
        "Country", foreign_keys=[importer_iso3], back_populates="import_flows"
    )
    source = relationship("DataSource", lazy="noload")


class ProcessingRiskScore(Base):
    """Processing Risk Score (PRS) per country and year with component breakdown."""

    __tablename__ = "processing_risk_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    country_iso3 = Column(String(3), ForeignKey("countries.iso3"), nullable=False)
    year = Column(Integer, nullable=False)
    prs_score = Column(Numeric(4, 2), nullable=False)
    capacity_score = Column(Numeric(5, 4))
    enforcement_score = Column(Numeric(5, 4))
    income_score = Column(Numeric(5, 4))
    literature_score = Column(Numeric(5, 4))
    formal_capacity_mt = Column(Numeric(14, 2), nullable=True)
    import_volume_mt = Column(Numeric(14, 2), nullable=True)
    capacity_ratio = Column(Numeric(8, 4), nullable=True)
    enforcement_index = Column(Numeric(8, 4), nullable=True)
    income_classification = Column(String(50))
    literature_flag_level = Column(String(20))
    data_completeness = Column(Numeric(4, 3))
    methodology_version = Column(Integer, default=1)
    computed_at = Column(DateTime(timezone=True), server_default=text("now()"))

    country = relationship("Country", back_populates="prs_scores")


class DataSource(Base):
    """Registry of external data sources used to populate the pipeline."""

    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    url = Column(String(2048))
    vintage_year = Column(Integer)
    accessed_date = Column(Date)
    methodology_notes = Column(Text)

    __table_args__ = (UniqueConstraint("name", "vintage_year", name="uq_data_sources_name_vintage"),)


class PipelineRun(Base):
    """Audit log of dbt / ingestion pipeline executions."""

    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_name = Column(String(255))
    run_type = Column(String(50))
    status = Column(String(30))
    records_fetched = Column(Integer)
    records_written = Column(Integer)
    s3_prefix = Column(Text)
    error_log = Column(Text)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    triggered_by = Column(String(100))


# ── 2. Application tables ─────────────────────────────────────────────────────

class AsyncJob(Base):
    """Background job record for report generation and other async work."""

    __tablename__ = "async_jobs"

    id = _uuid_pk()
    auth0_user_id = Column(String(128), nullable=True)
    job_type = Column(String(50), nullable=False)
    status = Column(String(30), nullable=False, server_default="queued")
    params = Column(JSONB)
    output_url = Column(Text, nullable=True)
    output_expires_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    worker_id = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class UserSavedState(Base):
    """Persisted map / filter states for authenticated users."""

    __tablename__ = "user_saved_states"

    id = _uuid_pk()
    auth0_user_id = Column(String(128), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    filter_state = Column(JSONB, nullable=False)
    is_default = Column(Boolean, server_default="false", default=False)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), server_default=text("now()"), onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("auth0_user_id", "name", name="uq_user_saved_states_user_name"),
    )


class EmbedToken(Base):
    """API embed tokens allowing third-party sites to query the API with
    pre-scoped filters and domain restrictions."""

    __tablename__ = "embed_tokens"

    id = _uuid_pk()
    token = Column(String(128), unique=True, nullable=False)
    label = Column(String(255), nullable=True)
    allowed_origins = Column(ARRAY(Text), nullable=True)
    default_filters = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    request_count = Column(BigInteger, server_default="0", default=0)
    is_active = Column(Boolean, server_default="true", default=True)


# ── 3. dbt mart (read-only) cache tables ─────────────────────────────────────

class MartChoroplethCache(Base):
    """Pre-aggregated per-country metrics for choropleth map rendering.

    Populated exclusively by the dbt pipeline; the API only reads this table.
    Composite primary key on (country_iso3, year).
    """

    __tablename__ = "mart_choropleth_cache"

    country_iso3 = Column(String(3), primary_key=True)
    year = Column(Integer, primary_key=True)
    country_name = Column(String(255))
    region = Column(String(100))
    subregion = Column(String(100))
    total_generation_mt = Column(Numeric(14, 2))
    per_capita_kg = Column(Numeric(8, 3))
    formal_collection_rate = Column(Numeric(5, 4))
    net_trade_mt = Column(Numeric(14, 2))
    export_volume_mt = Column(Numeric(14, 2))
    import_volume_mt = Column(Numeric(14, 2))
    prs_score = Column(Numeric(4, 2))
    export_intensity = Column(Numeric(8, 4))
    compliance_rate = Column(Numeric(5, 4))
    generation_confidence_tier = Column(String(20))
    data_vintage_year = Column(Integer)
    generation_missing = Column(Boolean, default=False)
    exports_missing = Column(Boolean, default=False)
    imports_missing = Column(Boolean, default=False)
    prs_missing = Column(Boolean, default=False)


class MartSankeyCache(Base):
    """Pre-joined bilateral trade flow records for Sankey diagram rendering.

    Populated exclusively by the dbt pipeline; the API only reads this table.
    No single-column primary key — Alembic migration defines a surrogate.
    """

    __tablename__ = "mart_sankey_cache"

    # Surrogate PK to satisfy SQLAlchemy ORM requirement
    id = Column(Integer, primary_key=True, autoincrement=True)

    year = Column(Integer, nullable=False)
    exporter_iso3 = Column(String(3))
    importer_iso3 = Column(String(3))
    un_category_code = Column(Integer)
    volume_mt = Column(Numeric(14, 2))
    value_usd = Column(Numeric(18, 2))
    data_source = Column(String(100))
    confidence_tier = Column(String(20))
    mapping_confidence = Column(String(20))
    has_violation = Column(Boolean)
    prs_risk_flag = Column(Boolean)
    importer_prs_score = Column(Numeric(4, 2))
    data_conflict = Column(Boolean)
    exporter_name = Column(String(255))
    exporter_region = Column(String(100))
    exporter_subregion = Column(String(100))
    importer_name = Column(String(255))
    importer_region = Column(String(100))
    importer_subregion = Column(String(100))
    compliance_color = Column(String(10))
    rank_by_volume = Column(Integer)
    violation_rank_by_volume = Column(Integer)

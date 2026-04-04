"""Initial schema — all EWasteTradeFlow tables.

Revision ID: 001
Revises: (none)
Create Date: 2025-01-01 00:00:00.000000

Creates the 10 tables defined in app/models/db.py:
  Reference/fact:     countries, data_sources, ewaste_generation,
                      trade_flows, processing_risk_scores, pipeline_runs
  Application:        async_jobs, user_saved_states, embed_tokens
  dbt mart (r/o):     mart_choropleth_cache, mart_sankey_cache
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgcrypto for gen_random_uuid()
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # ── data_sources ──────────────────────────────────────────────────────────
    op.create_table(
        "data_sources",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("url", sa.String(2048), nullable=True),
        sa.Column("vintage_year", sa.Integer(), nullable=True),
        sa.Column("accessed_date", sa.Date(), nullable=True),
        sa.Column("methodology_notes", sa.Text(), nullable=True),
        sa.UniqueConstraint("name", "vintage_year", name="uq_data_sources_name_vintage"),
    )

    # ── countries ─────────────────────────────────────────────────────────────
    op.create_table(
        "countries",
        sa.Column("iso3", sa.String(3), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("subregion", sa.String(100), nullable=True),
        sa.Column("un_member", sa.Boolean(), server_default="false"),
        sa.Column("basel_signatory", sa.Boolean(), server_default="false"),
        sa.Column("basel_ban_ratified", sa.Boolean(), server_default="false"),
        sa.Column("is_oecd_member", sa.Boolean(), server_default="false"),
        sa.Column("income_classification", sa.String(50), nullable=True),
        sa.Column("geometry", sa.Text(), nullable=True, comment="PostGIS polygon (MultiPolygon)"),
        sa.Column("geometry_simplified", sa.Text(), nullable=True, comment="PostGIS polygon (simplified)"),
        sa.Column("centroid", sa.Text(), nullable=True, comment="PostGIS point"),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── ewaste_generation ─────────────────────────────────────────────────────
    op.create_table(
        "ewaste_generation",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("country_iso3", sa.String(3), sa.ForeignKey("countries.iso3"), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("category_code", sa.Integer(), nullable=True),
        sa.Column("total_mt", sa.Numeric(12, 2), nullable=True),
        sa.Column("per_capita_kg", sa.Numeric(8, 3), nullable=True),
        sa.Column("formal_collection_mt", sa.Numeric(12, 2), nullable=True),
        sa.Column("formal_collection_rate", sa.Numeric(5, 4), nullable=True),
        sa.Column("is_interpolated", sa.Boolean(), server_default="false"),
        sa.Column("data_vintage_year", sa.Integer(), nullable=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("data_sources.id"), nullable=True),
        sa.Column("confidence_tier", sa.String(20), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_ewaste_generation_country_year", "ewaste_generation", ["country_iso3", "year"])

    # ── trade_flows ───────────────────────────────────────────────────────────
    op.create_table(
        "trade_flows",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("exporter_iso3", sa.String(3), sa.ForeignKey("countries.iso3"), nullable=False),
        sa.Column("importer_iso3", sa.String(3), sa.ForeignKey("countries.iso3"), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("hs_code", sa.String(20), nullable=True),
        sa.Column("ewaste_category_code", sa.Integer(), nullable=True),
        sa.Column("volume_mt", sa.Numeric(14, 2), nullable=True),
        sa.Column("estimated_ewaste_volume_mt", sa.Numeric(14, 2), nullable=True),
        sa.Column("value_usd", sa.Numeric(18, 2), nullable=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("data_sources.id"), nullable=True),
        sa.Column("confidence_tier", sa.String(20), nullable=True),
        sa.Column("mapping_confidence", sa.String(20), nullable=True),
        sa.Column("data_conflict", sa.Boolean(), server_default="false"),
        sa.Column("basel_compliant", sa.Boolean(), nullable=True),
        sa.Column("prs_risk_flag", sa.Boolean(), server_default="false"),
        sa.Column("importer_prs_score", sa.Numeric(4, 2), nullable=True),
        sa.Column("informal_estimate", sa.Boolean(), server_default="false"),
        sa.Column("data_source", sa.String(100), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_trade_flows_exporter_year", "trade_flows", ["exporter_iso3", "year"])
    op.create_index("ix_trade_flows_importer_year", "trade_flows", ["importer_iso3", "year"])

    # ── processing_risk_scores ────────────────────────────────────────────────
    op.create_table(
        "processing_risk_scores",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("country_iso3", sa.String(3), sa.ForeignKey("countries.iso3"), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("prs_score", sa.Numeric(4, 2), nullable=False),
        sa.Column("capacity_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("enforcement_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("income_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("literature_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("formal_capacity_mt", sa.Numeric(14, 2), nullable=True),
        sa.Column("import_volume_mt", sa.Numeric(14, 2), nullable=True),
        sa.Column("capacity_ratio", sa.Numeric(8, 4), nullable=True),
        sa.Column("enforcement_index", sa.Numeric(8, 4), nullable=True),
        sa.Column("income_classification", sa.String(50), nullable=True),
        sa.Column("literature_flag_level", sa.String(20), nullable=True),
        sa.Column("data_completeness", sa.Numeric(4, 3), nullable=True),
        sa.Column("methodology_version", sa.Integer(), server_default="1"),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_prs_country_year", "processing_risk_scores", ["country_iso3", "year"])

    # ── pipeline_runs ─────────────────────────────────────────────────────────
    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_name", sa.String(255), nullable=True),
        sa.Column("run_type", sa.String(50), nullable=True),
        sa.Column("status", sa.String(30), nullable=True),
        sa.Column("records_fetched", sa.Integer(), nullable=True),
        sa.Column("records_written", sa.Integer(), nullable=True),
        sa.Column("s3_prefix", sa.Text(), nullable=True),
        sa.Column("error_log", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("triggered_by", sa.String(100), nullable=True),
    )

    # ── async_jobs ────────────────────────────────────────────────────────────
    op.create_table(
        "async_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("auth0_user_id", sa.String(128), nullable=True),
        sa.Column("job_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="queued"),
        sa.Column("params", postgresql.JSONB(), nullable=True),
        sa.Column("output_url", sa.Text(), nullable=True),
        sa.Column("output_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("worker_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── user_saved_states ─────────────────────────────────────────────────────
    op.create_table(
        "user_saved_states",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("auth0_user_id", sa.String(128), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("filter_state", postgresql.JSONB(), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("auth0_user_id", "name", name="uq_user_saved_states_user_name"),
    )

    # ── embed_tokens ──────────────────────────────────────────────────────────
    op.create_table(
        "embed_tokens",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("token", sa.String(128), unique=True, nullable=False),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("allowed_origins", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("default_filters", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("request_count", sa.BigInteger(), server_default="0"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
    )

    # ── mart_choropleth_cache (dbt-managed, read-only from API) ───────────────
    op.create_table(
        "mart_choropleth_cache",
        sa.Column("country_iso3", sa.String(3), primary_key=True),
        sa.Column("year", sa.Integer(), primary_key=True),
        sa.Column("country_name", sa.String(255), nullable=True),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("subregion", sa.String(100), nullable=True),
        sa.Column("total_generation_mt", sa.Numeric(14, 2), nullable=True),
        sa.Column("per_capita_kg", sa.Numeric(8, 3), nullable=True),
        sa.Column("formal_collection_rate", sa.Numeric(5, 4), nullable=True),
        sa.Column("net_trade_mt", sa.Numeric(14, 2), nullable=True),
        sa.Column("export_volume_mt", sa.Numeric(14, 2), nullable=True),
        sa.Column("import_volume_mt", sa.Numeric(14, 2), nullable=True),
        sa.Column("prs_score", sa.Numeric(4, 2), nullable=True),
        sa.Column("export_intensity", sa.Numeric(8, 4), nullable=True),
        sa.Column("compliance_rate", sa.Numeric(5, 4), nullable=True),
        sa.Column("generation_confidence_tier", sa.String(20), nullable=True),
        sa.Column("data_vintage_year", sa.Integer(), nullable=True),
        sa.Column("generation_missing", sa.Boolean(), server_default="false"),
        sa.Column("exports_missing", sa.Boolean(), server_default="false"),
        sa.Column("imports_missing", sa.Boolean(), server_default="false"),
        sa.Column("prs_missing", sa.Boolean(), server_default="false"),
    )

    # ── mart_sankey_cache (dbt-managed, read-only from API) ───────────────────
    op.create_table(
        "mart_sankey_cache",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("exporter_iso3", sa.String(3), nullable=True),
        sa.Column("importer_iso3", sa.String(3), nullable=True),
        sa.Column("un_category_code", sa.Integer(), nullable=True),
        sa.Column("volume_mt", sa.Numeric(14, 2), nullable=True),
        sa.Column("value_usd", sa.Numeric(18, 2), nullable=True),
        sa.Column("data_source", sa.String(100), nullable=True),
        sa.Column("confidence_tier", sa.String(20), nullable=True),
        sa.Column("mapping_confidence", sa.String(20), nullable=True),
        sa.Column("has_violation", sa.Boolean(), nullable=True),
        sa.Column("prs_risk_flag", sa.Boolean(), nullable=True),
        sa.Column("importer_prs_score", sa.Numeric(4, 2), nullable=True),
        sa.Column("data_conflict", sa.Boolean(), nullable=True),
        sa.Column("exporter_name", sa.String(255), nullable=True),
        sa.Column("exporter_region", sa.String(100), nullable=True),
        sa.Column("exporter_subregion", sa.String(100), nullable=True),
        sa.Column("importer_name", sa.String(255), nullable=True),
        sa.Column("importer_region", sa.String(100), nullable=True),
        sa.Column("importer_subregion", sa.String(100), nullable=True),
        sa.Column("compliance_color", sa.String(10), nullable=True),
        sa.Column("rank_by_volume", sa.Integer(), nullable=True),
        sa.Column("violation_rank_by_volume", sa.Integer(), nullable=True),
    )
    op.create_index("ix_mart_sankey_year", "mart_sankey_cache", ["year"])


def downgrade() -> None:
    op.drop_table("mart_sankey_cache")
    op.drop_table("mart_choropleth_cache")
    op.drop_table("embed_tokens")
    op.drop_table("user_saved_states")
    op.drop_table("async_jobs")
    op.drop_table("pipeline_runs")
    op.drop_table("processing_risk_scores")
    op.drop_table("trade_flows")
    op.drop_table("ewaste_generation")
    op.drop_table("countries")
    op.drop_table("data_sources")

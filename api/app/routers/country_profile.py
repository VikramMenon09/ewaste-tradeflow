"""Country profile router.

Endpoint:
  GET /country/{iso3}/profile — full country detail with generation series,
                                top trade partners, and PRS score
"""

from __future__ import annotations

from typing import Optional
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.schemas import CountryProfile, GenerationPoint, TradePartner
from app.services.prs import prs_service

router = APIRouter(prefix="/country", tags=["country-profile"])

# Number of years in the generation time-series
_GENERATION_YEARS = 10
# Number of top trade partners to return for exports and imports
_TOP_PARTNERS = 5
# Latest year for PRS / trade partner lookup (use current data year)
_CURRENT_YEAR = date.today().year


@router.get("/{iso3}/profile", response_model=CountryProfile)
async def get_country_profile(
    iso3: str,
    db: AsyncSession = Depends(get_db),
) -> CountryProfile:
    """Return a full country profile including:

    - Basic country metadata and Basel Convention flags
    - 10-year e-waste generation time series
    - Top 5 export partners (by volume)
    - Top 5 import partners (by volume)
    - Latest PRS score and methodology version
    """
    iso3 = iso3.upper()

    # ── 1. Fetch country metadata ─────────────────────────────────────────────
    country_sql = text(
        """
        SELECT
            iso3, name, region, subregion, income_classification,
            basel_signatory, basel_ban_ratified, is_oecd_member
        FROM countries
        WHERE iso3 = :iso3
        """
    )
    country_result = await db.execute(country_sql, {"iso3": iso3})
    country_row = country_result.mappings().first()
    if country_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Country '{iso3}' not found",
        )

    # ── 2. Generation time series (last 10 years) ─────────────────────────────
    gen_sql = text(
        """
        SELECT
            year, total_mt, per_capita_kg, formal_collection_rate,
            confidence_tier, data_vintage_year, is_interpolated
        FROM ewaste_generation
        WHERE country_iso3 = :iso3
        ORDER BY year DESC
        LIMIT :limit
        """
    )
    gen_result = await db.execute(gen_sql, {"iso3": iso3, "limit": _GENERATION_YEARS})
    generation_series = [
        GenerationPoint(
            year=row["year"],
            total_mt=float(row["total_mt"]) if row["total_mt"] is not None else None,
            per_capita_kg=float(row["per_capita_kg"]) if row["per_capita_kg"] is not None else None,
            formal_collection_rate=(
                float(row["formal_collection_rate"])
                if row["formal_collection_rate"] is not None
                else None
            ),
            confidence_tier=row["confidence_tier"],
            data_vintage_year=row["data_vintage_year"],
            is_interpolated=bool(row["is_interpolated"]),
        )
        for row in gen_result.mappings().all()
    ]
    # Return series in ascending year order for charting
    generation_series.sort(key=lambda p: p.year)

    # ── 3. Top 5 export partners ──────────────────────────────────────────────
    exports_sql = text(
        """
        SELECT
            tf.importer_iso3       AS partner_iso3,
            c.name                 AS partner_name,
            SUM(tf.volume_mt)      AS volume_mt,
            SUM(tf.value_usd)      AS value_usd,
            BOOL_OR(tf.prs_risk_flag)   AS prs_risk_flag,
            -- Basel compliant if all flows for this partner are compliant
            CASE
                WHEN COUNT(*) FILTER (WHERE tf.basel_compliant IS NULL) = COUNT(*) THEN NULL
                WHEN BOOL_AND(tf.basel_compliant) THEN TRUE
                ELSE FALSE
            END                    AS basel_compliant,
            -- Compliance color: red if any flagged, green if all compliant, amber otherwise
            CASE
                WHEN BOOL_OR(tf.prs_risk_flag) THEN 'red'
                WHEN BOOL_AND(tf.basel_compliant) THEN 'green'
                ELSE 'amber'
            END                    AS compliance_color
        FROM trade_flows tf
        JOIN countries c ON c.iso3 = tf.importer_iso3
        WHERE tf.exporter_iso3 = :iso3
        GROUP BY tf.importer_iso3, c.name
        ORDER BY SUM(tf.volume_mt) DESC NULLS LAST
        LIMIT :limit
        """
    )
    exports_result = await db.execute(exports_sql, {"iso3": iso3, "limit": _TOP_PARTNERS})
    top_exports = [
        TradePartner(
            partner_iso3=row["partner_iso3"],
            partner_name=row["partner_name"],
            volume_mt=float(row["volume_mt"]) if row["volume_mt"] is not None else None,
            value_usd=float(row["value_usd"]) if row["value_usd"] is not None else None,
            basel_compliant=row["basel_compliant"],
            prs_risk_flag=bool(row["prs_risk_flag"]),
            compliance_color=row["compliance_color"],
        )
        for row in exports_result.mappings().all()
    ]

    # ── 4. Top 5 import partners ──────────────────────────────────────────────
    imports_sql = text(
        """
        SELECT
            tf.exporter_iso3       AS partner_iso3,
            c.name                 AS partner_name,
            SUM(tf.volume_mt)      AS volume_mt,
            SUM(tf.value_usd)      AS value_usd,
            BOOL_OR(tf.prs_risk_flag)  AS prs_risk_flag,
            CASE
                WHEN COUNT(*) FILTER (WHERE tf.basel_compliant IS NULL) = COUNT(*) THEN NULL
                WHEN BOOL_AND(tf.basel_compliant) THEN TRUE
                ELSE FALSE
            END                    AS basel_compliant,
            CASE
                WHEN BOOL_OR(tf.prs_risk_flag) THEN 'red'
                WHEN BOOL_AND(tf.basel_compliant) THEN 'green'
                ELSE 'amber'
            END                    AS compliance_color
        FROM trade_flows tf
        JOIN countries c ON c.iso3 = tf.exporter_iso3
        WHERE tf.importer_iso3 = :iso3
        GROUP BY tf.exporter_iso3, c.name
        ORDER BY SUM(tf.volume_mt) DESC NULLS LAST
        LIMIT :limit
        """
    )
    imports_result = await db.execute(imports_sql, {"iso3": iso3, "limit": _TOP_PARTNERS})
    top_imports = [
        TradePartner(
            partner_iso3=row["partner_iso3"],
            partner_name=row["partner_name"],
            volume_mt=float(row["volume_mt"]) if row["volume_mt"] is not None else None,
            value_usd=float(row["value_usd"]) if row["value_usd"] is not None else None,
            basel_compliant=row["basel_compliant"],
            prs_risk_flag=bool(row["prs_risk_flag"]),
            compliance_color=row["compliance_color"],
        )
        for row in imports_result.mappings().all()
    ]

    # ── 5. PRS score (latest available) ──────────────────────────────────────
    prs = await prs_service.compute_for_country(db, iso3, _CURRENT_YEAR)

    return CountryProfile(
        iso3=country_row["iso3"],
        name=country_row["name"],
        region=country_row["region"],
        subregion=country_row["subregion"],
        income_classification=country_row["income_classification"],
        basel_signatory=bool(country_row["basel_signatory"]),
        basel_ban_ratified=bool(country_row["basel_ban_ratified"]),
        is_oecd_member=bool(country_row["is_oecd_member"]),
        prs_score=prs.prs_score if prs else None,
        prs_methodology_version=prs.methodology_version if prs else None,
        generation_series=generation_series,
        top_exports=top_exports,
        top_imports=top_imports,
        processing_capacity_mt=prs.formal_capacity_mt if prs else None,
        literature_flag_level=prs.literature_flag_level if prs else None,
    )

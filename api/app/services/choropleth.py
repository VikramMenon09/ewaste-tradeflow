"""Choropleth data service.

Queries the ``mart_choropleth_cache`` dbt mart table for a given metric and
year.  The mart is pre-aggregated by the dbt pipeline and is read-only from
the API perspective.

Returns a list of ChoroplethCountry objects suitable for direct JSON
serialisation.  Countries with missing data are included with
``is_missing=True`` and ``value=None`` so the frontend can render them as
a "No Data" grey bucket.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas import ChoroplethCountry, ChoroplethResponse

# ── Metric → column name mapping ─────────────────────────────────────────────
# Maps the public API metric name to the mart_choropleth_cache column that
# holds the numeric value.

METRIC_COLUMN_MAP: dict[str, str] = {
    "generation": "total_generation_mt",
    "per_capita": "per_capita_kg",
    "formal_collection": "formal_collection_rate",
    "net_trade": "net_trade_mt",
    "exports": "export_volume_mt",
    "imports": "import_volume_mt",
    "prs": "prs_score",
    "export_intensity": "export_intensity",
    "compliance_rate": "compliance_rate",
}

# Metrics for which a NULL value should be mapped to the "missing" sentinel
# for the *specific* data type (i.e. generation_missing vs prs_missing).
_METRIC_MISSING_FLAG: dict[str, str] = {
    "generation": "generation_missing",
    "per_capita": "generation_missing",
    "formal_collection": "generation_missing",
    "net_trade": "exports_missing",
    "exports": "exports_missing",
    "imports": "imports_missing",
    "prs": "prs_missing",
    "export_intensity": "exports_missing",
    "compliance_rate": "exports_missing",
}


def _metric_missing_col(metric: str) -> str:
    return _METRIC_MISSING_FLAG.get(metric, "generation_missing")


async def get_choropleth(
    db: AsyncSession,
    metric: str,
    year: int,
) -> ChoroplethResponse:
    """Query mart_choropleth_cache and return a ChoroplethResponse.

    Args:
        db: Active async database session.
        metric: One of the keys in METRIC_COLUMN_MAP.
        year: Data year (e.g. 2020).

    Returns:
        ChoroplethResponse with one ChoroplethCountry per row in the mart.

    Raises:
        ValueError: If metric is not recognised.
    """
    value_col = METRIC_COLUMN_MAP.get(metric)
    if value_col is None:
        raise ValueError(
            f"Unknown metric '{metric}'. Valid metrics: {sorted(METRIC_COLUMN_MAP)}"
        )

    missing_col = _metric_missing_col(metric)

    # Use raw SQL for performance — avoid any ORM overhead on this hot path.
    sql = text(
        f"""
        SELECT
            country_iso3,
            country_name,
            {value_col}              AS value,
            generation_confidence_tier AS confidence_tier,
            data_vintage_year,
            {missing_col}            AS is_missing
        FROM mart_choropleth_cache
        WHERE year = :year
        ORDER BY country_iso3
        """
    )

    result = await db.execute(sql, {"year": year})
    rows = result.mappings().all()

    countries: list[ChoroplethCountry] = []
    for row in rows:
        raw_value: Optional[float] = row["value"]
        missing: bool = bool(row["is_missing"]) or raw_value is None
        countries.append(
            ChoroplethCountry(
                iso3=row["country_iso3"],
                name=row["country_name"] or row["country_iso3"],
                value=float(raw_value) if raw_value is not None else None,
                confidence_tier=row["confidence_tier"],
                data_vintage_year=row["data_vintage_year"],
                is_missing=missing,
            )
        )

    return ChoroplethResponse(year=year, metric=metric, countries=countries)

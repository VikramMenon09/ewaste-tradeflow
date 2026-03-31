"""Processing Risk Score (PRS) service.

Reads pre-computed PRS data from the ``processing_risk_scores`` table (which
is populated by the dbt pipeline) and surfaces it for the country profile UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class PRSComponents:
    """PRS score and its component breakdown for UI display."""

    country_iso3: str
    year: int
    prs_score: float
    capacity_score: Optional[float]
    enforcement_score: Optional[float]
    income_score: Optional[float]
    literature_score: Optional[float]
    formal_capacity_mt: Optional[float]
    import_volume_mt: Optional[float]
    capacity_ratio: Optional[float]
    enforcement_index: Optional[float]
    income_classification: Optional[str]
    literature_flag_level: Optional[str]
    data_completeness: Optional[float]
    methodology_version: int


class PRSService:
    """Service for retrieving Processing Risk Score data.

    Instantiate once and share across requests (it holds no per-request state).
    """

    async def compute_for_country(
        self,
        db: AsyncSession,
        country_iso3: str,
        year: int,
    ) -> Optional[PRSComponents]:
        """Return PRS components for a country / year, or None if not found.

        The score is pre-computed by the dbt pipeline.  This method fetches
        the most recent record for the given year; if no exact match is found
        it falls back to the latest available year before the requested year.

        Args:
            db: Active async database session.
            country_iso3: ISO 3166-1 alpha-3 country code.
            year: Data year.

        Returns:
            PRSComponents or None if no data is available.
        """
        sql = text(
            """
            SELECT
                country_iso3,
                year,
                prs_score,
                capacity_score,
                enforcement_score,
                income_score,
                literature_score,
                formal_capacity_mt,
                import_volume_mt,
                capacity_ratio,
                enforcement_index,
                income_classification,
                literature_flag_level,
                data_completeness,
                methodology_version
            FROM processing_risk_scores
            WHERE country_iso3 = :iso3
              AND year <= :year
            ORDER BY year DESC
            LIMIT 1
            """
        )

        result = await db.execute(sql, {"iso3": country_iso3, "year": year})
        row = result.mappings().first()

        if row is None:
            return None

        def _f(val) -> Optional[float]:
            return float(val) if val is not None else None

        return PRSComponents(
            country_iso3=row["country_iso3"],
            year=row["year"],
            prs_score=float(row["prs_score"]),
            capacity_score=_f(row["capacity_score"]),
            enforcement_score=_f(row["enforcement_score"]),
            income_score=_f(row["income_score"]),
            literature_score=_f(row["literature_score"]),
            formal_capacity_mt=_f(row["formal_capacity_mt"]),
            import_volume_mt=_f(row["import_volume_mt"]),
            capacity_ratio=_f(row["capacity_ratio"]),
            enforcement_index=_f(row["enforcement_index"]),
            income_classification=row["income_classification"],
            literature_flag_level=row["literature_flag_level"],
            data_completeness=_f(row["data_completeness"]),
            methodology_version=int(row["methodology_version"]),
        )


# Module-level singleton
prs_service = PRSService()

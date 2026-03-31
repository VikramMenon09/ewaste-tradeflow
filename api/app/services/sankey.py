"""Sankey diagram data service.

Queries the ``mart_sankey_cache`` dbt mart table for a given year with
optional region, category, and flagged-flow filters applied in SQL.

Builds a SankeyResponse with a deduplicated node list derived from the
exporter / importer iso3 values present in the filtered result set.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas import SankeyLink, SankeyNode, SankeyResponse


async def get_sankey(
    db: AsyncSession,
    year: int,
    top_n: int = 20,
    exporter_region: Optional[str] = None,
    importer_region: Optional[str] = None,
    flagged_only: bool = False,
    category: Optional[int] = None,
) -> SankeyResponse:
    """Query mart_sankey_cache and return a SankeyResponse.

    Filters are applied in SQL to keep Python-side processing minimal.
    The result is ordered by rank_by_volume so that top_n slicing is
    deterministic and consistent with the dbt pre-ranking.

    Args:
        db: Active async database session.
        year: Trade year to query.
        top_n: Maximum number of bilateral links to return (ranked by volume).
        exporter_region: If set, restrict to flows from this region.
        importer_region: If set, restrict to flows to this region.
        flagged_only: If True, return only flows where has_violation IS TRUE
                      or prs_risk_flag IS TRUE.
        category: If set, restrict to this UN category code.

    Returns:
        SankeyResponse with deduplicated nodes and filtered links.
    """
    # Build WHERE clauses dynamically to avoid unnecessary bind parameters
    conditions: list[str] = ["year = :year"]
    params: dict = {"year": year, "top_n": top_n}

    if exporter_region:
        conditions.append("exporter_region = :exporter_region")
        params["exporter_region"] = exporter_region

    if importer_region:
        conditions.append("importer_region = :importer_region")
        params["importer_region"] = importer_region

    if flagged_only:
        conditions.append("(has_violation = TRUE OR prs_risk_flag = TRUE)")

    if category is not None:
        conditions.append("un_category_code = :category")
        params["category"] = category

    where_clause = " AND ".join(conditions)

    sql = text(
        f"""
        SELECT
            exporter_iso3,
            importer_iso3,
            exporter_name,
            exporter_region,
            importer_name,
            importer_region,
            volume_mt,
            value_usd,
            compliance_color,
            has_violation,
            prs_risk_flag,
            importer_prs_score,
            data_conflict,
            confidence_tier,
            mapping_confidence,
            rank_by_volume
        FROM mart_sankey_cache
        WHERE {where_clause}
        ORDER BY rank_by_volume ASC NULLS LAST
        LIMIT :top_n
        """
    )

    result = await db.execute(sql, params)
    rows = result.mappings().all()

    # Build links
    links: list[SankeyLink] = []
    # Track nodes: iso3 → (name, region)
    node_map: dict[str, tuple[str, Optional[str]]] = {}

    for row in rows:
        exporter_iso3: str = row["exporter_iso3"]
        importer_iso3: str = row["importer_iso3"]

        # Register nodes
        node_map.setdefault(
            exporter_iso3,
            (row["exporter_name"] or exporter_iso3, row["exporter_region"]),
        )
        node_map.setdefault(
            importer_iso3,
            (row["importer_name"] or importer_iso3, row["importer_region"]),
        )

        compliance_color = row["compliance_color"] or "amber"
        # Coerce to valid literal
        if compliance_color not in ("green", "amber", "red"):
            compliance_color = "amber"

        links.append(
            SankeyLink(
                source=exporter_iso3,
                target=importer_iso3,
                volume_mt=float(row["volume_mt"]) if row["volume_mt"] is not None else None,
                value_usd=float(row["value_usd"]) if row["value_usd"] is not None else None,
                compliance_color=compliance_color,  # type: ignore[arg-type]
                has_violation=bool(row["has_violation"]),
                prs_risk_flag=bool(row["prs_risk_flag"]),
                importer_prs_score=(
                    float(row["importer_prs_score"])
                    if row["importer_prs_score"] is not None
                    else None
                ),
                data_conflict=bool(row["data_conflict"]),
                confidence_tier=row["confidence_tier"],
                mapping_confidence=row["mapping_confidence"],
            )
        )

    # Build deduplicated, sorted node list
    nodes: list[SankeyNode] = [
        SankeyNode(id=iso3, name=name, region=region)
        for iso3, (name, region) in sorted(node_map.items())
    ]

    return SankeyResponse(year=year, nodes=nodes, links=links)

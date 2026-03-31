"""Trade flows router.

Endpoint:
  GET /trade-flows — list bilateral trade flow records with rich filter support

Rate limited to 60 requests per minute per IP address.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.rate_limit import limiter
from app.models.db import TradeFlow
from app.models.schemas import TradeFlowRecord

router = APIRouter(prefix="/trade-flows", tags=["trade-flows"])

_MAX_LIMIT = 1000


@router.get("", response_model=list[TradeFlowRecord])
@limiter.limit("60/minute")
async def list_trade_flows(
    request: Request,
    exporter: Optional[str] = Query(None, description="Exporter ISO3 code"),
    importer: Optional[str] = Query(None, description="Importer ISO3 code"),
    year: Optional[int] = Query(None, ge=1990, le=2100, description="Trade year"),
    category: Optional[int] = Query(None, ge=0, le=6, description="E-waste category code"),
    compliant_only: bool = Query(False, description="Return only Basel-compliant flows"),
    flagged_only: bool = Query(False, description="Return only PRS-flagged flows"),
    limit: int = Query(100, ge=1, le=_MAX_LIMIT, description="Page size (max 1000)"),
    db: AsyncSession = Depends(get_db),
) -> list[TradeFlowRecord]:
    """Return trade flow records with optional filters.

    Supports filtering by exporter, importer, year, category, Basel compliance
    status, and PRS risk flag.  Results are sorted by year DESC then volume DESC.

    Rate limited to 60 requests per minute per IP address.
    """
    stmt = select(
        TradeFlow.exporter_iso3,
        TradeFlow.importer_iso3,
        TradeFlow.year,
        TradeFlow.hs_code,
        TradeFlow.ewaste_category_code,
        TradeFlow.volume_mt,
        TradeFlow.estimated_ewaste_volume_mt,
        TradeFlow.value_usd,
        TradeFlow.confidence_tier,
        TradeFlow.mapping_confidence,
        TradeFlow.basel_compliant,
        TradeFlow.prs_risk_flag,
    ).order_by(TradeFlow.year.desc(), TradeFlow.volume_mt.desc().nullslast()).limit(limit)

    if exporter:
        stmt = stmt.where(TradeFlow.exporter_iso3 == exporter.upper())
    if importer:
        stmt = stmt.where(TradeFlow.importer_iso3 == importer.upper())
    if year is not None:
        stmt = stmt.where(TradeFlow.year == year)
    if category is not None:
        stmt = stmt.where(TradeFlow.ewaste_category_code == category)
    if compliant_only:
        stmt = stmt.where(TradeFlow.basel_compliant.is_(True))
    if flagged_only:
        stmt = stmt.where(TradeFlow.prs_risk_flag.is_(True))

    result = await db.execute(stmt)
    rows = result.mappings().all()

    records: list[TradeFlowRecord] = []
    for row in rows:
        d = dict(row)
        # Derive compliance_color from basel_compliant + prs_risk_flag
        if d.get("prs_risk_flag"):
            d["compliance_color"] = "red"
        elif d.get("basel_compliant") is True:
            d["compliance_color"] = "green"
        elif d.get("basel_compliant") is False:
            d["compliance_color"] = "red"
        else:
            d["compliance_color"] = "amber"
        records.append(TradeFlowRecord(**d))

    return records

"""Export router — streaming CSV download of trade flow data.

Endpoint:
  GET /export/csv — stream trade flow records as CSV with the same filter
                    parameters as the /trade-flows endpoint
"""

from __future__ import annotations

import csv
import io
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.rate_limit import limiter
from app.models.db import TradeFlow

router = APIRouter(prefix="/export", tags=["export"])

_MAX_EXPORT_ROWS = 50_000
_CSV_COLUMNS = [
    "exporter_iso3",
    "importer_iso3",
    "year",
    "hs_code",
    "ewaste_category_code",
    "volume_mt",
    "estimated_ewaste_volume_mt",
    "value_usd",
    "confidence_tier",
    "mapping_confidence",
    "basel_compliant",
    "prs_risk_flag",
    "data_source",
]


@router.get("/csv")
@limiter.limit("10/minute")
async def export_csv(
    request: Request,
    exporter: Optional[str] = Query(None, description="Exporter ISO3 code"),
    importer: Optional[str] = Query(None, description="Importer ISO3 code"),
    year: Optional[int] = Query(None, ge=1990, le=2100, description="Trade year"),
    category: Optional[int] = Query(None, ge=0, le=6, description="E-waste category code"),
    compliant_only: bool = Query(False, description="Return only Basel-compliant flows"),
    flagged_only: bool = Query(False, description="Return only PRS-flagged flows"),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Stream trade flow records as a UTF-8 CSV file.

    Accepts the same filter parameters as GET /trade-flows.
    Results are capped at 50,000 rows; apply filters to narrow the result set.

    Rate limited to 10 requests per minute per IP address.
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
        TradeFlow.data_source,
    ).order_by(TradeFlow.year.desc(), TradeFlow.volume_mt.desc().nullslast()).limit(_MAX_EXPORT_ROWS)

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

    def _generate_csv():
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=_CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate()

        for row in rows:
            writer.writerow({
                col: (
                    str(row[col]) if row[col] is not None else ""
                )
                for col in _CSV_COLUMNS
            })
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate()

    filename = "ewaste_trade_flows"
    if year:
        filename += f"_{year}"
    if exporter:
        filename += f"_{exporter.upper()}"
    filename += ".csv"

    return StreamingResponse(
        _generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

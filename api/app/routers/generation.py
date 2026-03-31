"""E-waste generation data router.

Endpoint:
  GET /generation — list generation records with optional filters

Rate limited to 60 requests per minute per IP address.
"""

from __future__ import annotations

import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.rate_limit import limiter
from app.models.db import EwasteGeneration
from app.models.schemas import GenerationRecord

router = APIRouter(prefix="/generation", tags=["generation"])


def _parse_year_range(year_range: str) -> tuple[int, int]:
    """Parse a 'YYYY-YYYY' year range string into a (start, end) int tuple.

    Raises:
        HTTPException 422 if the format is invalid.
    """
    match = re.fullmatch(r"(\d{4})-(\d{4})", year_range)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="year_range must be in the format 'YYYY-YYYY' (e.g. '2010-2022')",
        )
    start, end = int(match.group(1)), int(match.group(2))
    if start > end:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="year_range start must be <= end",
        )
    return start, end


@router.get("", response_model=list[GenerationRecord])
@limiter.limit("60/minute")
async def list_generation(
    request: Request,
    country: Optional[str] = Query(None, description="ISO3 country code"),
    year_range: Optional[str] = Query(
        None, description="Year range in format 'YYYY-YYYY', e.g. '2010-2022'"
    ),
    category: Optional[int] = Query(None, ge=0, le=6, description="E-waste category code 0-6"),
    db: AsyncSession = Depends(get_db),
) -> list[GenerationRecord]:
    """Return e-waste generation records with optional country, year, and category filters.

    Rate limited to 60 requests per minute per IP address.
    """
    stmt = select(
        EwasteGeneration.country_iso3,
        EwasteGeneration.year,
        EwasteGeneration.category_code,
        EwasteGeneration.total_mt,
        EwasteGeneration.per_capita_kg,
        EwasteGeneration.formal_collection_rate,
        EwasteGeneration.confidence_tier,
        EwasteGeneration.is_interpolated,
    ).order_by(EwasteGeneration.country_iso3, EwasteGeneration.year)

    if country:
        stmt = stmt.where(EwasteGeneration.country_iso3 == country.upper())

    if year_range:
        start_year, end_year = _parse_year_range(year_range)
        stmt = stmt.where(
            EwasteGeneration.year >= start_year,
            EwasteGeneration.year <= end_year,
        )

    if category is not None:
        stmt = stmt.where(EwasteGeneration.category_code == category)

    result = await db.execute(stmt)
    rows = result.mappings().all()
    return [GenerationRecord(**dict(row)) for row in rows]

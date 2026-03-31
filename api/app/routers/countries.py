"""Countries router.

Endpoints:
  GET /countries        — list all countries with optional region / income_class filter
  GET /countries/{iso3} — single country lookup

Country rows are cached in Redis for 24 hours because the reference data
changes rarely (only when the dbt pipeline re-runs).
"""

from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.db import Country
from app.models.schemas import CountryBasic
from app.services.cache import cache_service

router = APIRouter(prefix="/countries", tags=["countries"])

_CACHE_TTL = 86400  # 24 hours


@router.get("", response_model=list[CountryBasic])
async def list_countries(
    region: Optional[str] = Query(None, description="Filter by region (e.g. 'Asia')"),
    income_class: Optional[str] = Query(None, description="Filter by income classification"),
    db: AsyncSession = Depends(get_db),
) -> list[CountryBasic]:
    """Return the list of countries, optionally filtered by region or income class.

    Results are cached in Redis for 24 hours.
    """
    cache_key = f"countries:list:{region or '*'}:{income_class or '*'}"
    cached = await cache_service.get(cache_key)
    if cached is not None:
        return [CountryBasic(**item) for item in cached]

    stmt = select(
        Country.iso3,
        Country.name,
        Country.region,
        Country.subregion,
        Country.income_classification,
        Country.basel_signatory,
        Country.basel_ban_ratified,
        Country.is_oecd_member,
    ).order_by(Country.name)

    if region:
        stmt = stmt.where(Country.region == region)
    if income_class:
        stmt = stmt.where(Country.income_classification == income_class)

    result = await db.execute(stmt)
    rows = result.mappings().all()
    countries = [CountryBasic(**dict(row)) for row in rows]

    await cache_service.set(cache_key, [c.model_dump() for c in countries], ttl_seconds=_CACHE_TTL)
    return countries


@router.get("/{iso3}", response_model=CountryBasic)
async def get_country(
    iso3: str,
    db: AsyncSession = Depends(get_db),
) -> CountryBasic:
    """Return a single country by ISO 3166-1 alpha-3 code."""
    cache_key = f"countries:single:{iso3.upper()}"
    cached = await cache_service.get(cache_key)
    if cached is not None:
        return CountryBasic(**cached)

    stmt = select(
        Country.iso3,
        Country.name,
        Country.region,
        Country.subregion,
        Country.income_classification,
        Country.basel_signatory,
        Country.basel_ban_ratified,
        Country.is_oecd_member,
    ).where(Country.iso3 == iso3.upper())

    result = await db.execute(stmt)
    row = result.mappings().first()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Country '{iso3}' not found",
        )

    country = CountryBasic(**dict(row))
    await cache_service.set(cache_key, country.model_dump(), ttl_seconds=_CACHE_TTL)
    return country

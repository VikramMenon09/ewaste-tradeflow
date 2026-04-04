"""EWasteTradeFlow API — application factory.

All routers are mounted under the /api/v1 prefix.  The lifespan context
manager handles startup/shutdown of the database pool and Redis connection.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler as _slowapi_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import engine
from app.middleware.rate_limit import _rate_limit_exceeded_handler, limiter
from app.routers import (
    countries,
    country_profile,
    embed as embed_router,
    export as export_router,
    generation,
    map as map_router,
    reports,
    saved_states,
    trade_flows,
)
from app.services.cache import cache_service

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup: warm up DB pool and Redis.  Shutdown: close both."""
    logger.info("Starting up EWasteTradeFlow API (env=%s)", settings.ENV)
    await cache_service.connect()
    yield
    logger.info("Shutting down EWasteTradeFlow API")
    await cache_service.close()
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="EWasteTradeFlow API",
        description=(
            "API for global e-waste trade flow data, choropleth map layers, "
            "Processing Risk Scores, and async PDF report generation."
        ),
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # ── Rate limiter ──────────────────────────────────────────────────────────
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ── Routers ───────────────────────────────────────────────────────────────
    _V1 = "/api/v1"
    app.include_router(countries.router, prefix=_V1)
    app.include_router(generation.router, prefix=_V1)
    app.include_router(trade_flows.router, prefix=_V1)
    app.include_router(map_router.router, prefix=_V1)
    app.include_router(country_profile.router, prefix=_V1)
    app.include_router(reports.router, prefix=_V1)
    app.include_router(export_router.router, prefix=_V1)
    app.include_router(saved_states.router, prefix=_V1)
    app.include_router(embed_router.router, prefix=_V1)

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get("/health", tags=["meta"], include_in_schema=False)
    async def health() -> dict:
        return {"status": "ok", "env": settings.ENV}

    return app


app = create_app()

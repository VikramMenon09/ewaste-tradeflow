"""Application configuration loaded from environment variables via Pydantic Settings.

All settings have sensible defaults for local development. Production deployments
must supply the required secrets (DATABASE_URL, AUTH0_DOMAIN, etc.) via the
environment or a .env file.
"""

from __future__ import annotations

from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the EWasteTradeFlow API.

    Values are read from environment variables (case-insensitive) and,
    optionally, from a .env file in the working directory.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ewaste"
    DATABASE_SYNC_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/ewaste"

    # ── Redis (optional) ─────────────────────────────────────────────────────
    REDIS_URL: Optional[str] = None

    # ── Auth0 ─────────────────────────────────────────────────────────────────
    AUTH0_DOMAIN: str = "example.auth0.com"
    AUTH0_AUDIENCE: str = "https://api.ewastetradeflow.example.com"

    # ── AWS / S3 ──────────────────────────────────────────────────────────────
    S3_BUCKET: str = "ewaste-reports"
    S3_ENDPOINT_URL: Optional[str] = None  # Override for MinIO / localstack
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None

    # ── Puppeteer microservice ────────────────────────────────────────────────
    PUPPETEER_SERVICE_URL: str = "http://puppeteer:3000/render"
    PUPPETEER_INTERNAL_KEY: str = "change-me-in-production"

    # ── Frontend (used when building internal report-render URLs) ────────────
    FRONTEND_URL: str = "http://localhost:3000"

    # ── App behaviour ────────────────────────────────────────────────────────
    ENV: str = "development"  # development | staging | production
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: str = "http://localhost:3000"

    @field_validator("ENV")
    @classmethod
    def validate_env(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"ENV must be one of {allowed}")
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS comma-separated string into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"


# Module-level singleton — import this everywhere.
settings = Settings()

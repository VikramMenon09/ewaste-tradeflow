"""Embed tokens router — manage API tokens for embeddable iframe widgets.

Endpoints:
  POST   /embed/tokens         — create a new embed token (auth required)
  GET    /embed/tokens         — list caller's active tokens (auth required)
  DELETE /embed/tokens/{id}    — deactivate a token (auth required)
"""

from __future__ import annotations

import secrets
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.middleware.rate_limit import limiter
from app.models.db import EmbedToken

router = APIRouter(prefix="/embed", tags=["embed"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class EmbedTokenCreate(BaseModel):
    label: Optional[str] = Field(None, max_length=255, description="Human-readable label")
    allowed_origins: Optional[list[str]] = Field(
        None,
        description="List of allowed Origin values. If null, all origins are permitted.",
    )
    default_filters: Optional[dict[str, Any]] = Field(
        None,
        description="Default filter state embedded in the widget (year, metric, etc.)",
    )


class EmbedTokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    token: str
    label: Optional[str]
    allowed_origins: Optional[list[str]]
    default_filters: Optional[dict[str, Any]]
    is_active: bool
    request_count: int
    created_at: str

    @classmethod
    def from_orm_row(cls, row: EmbedToken) -> "EmbedTokenResponse":
        return cls(
            id=str(row.id),
            token=row.token,
            label=row.label,
            allowed_origins=row.allowed_origins,
            default_filters=row.default_filters,
            is_active=row.is_active,
            request_count=int(row.request_count or 0),
            created_at=row.created_at.isoformat() if row.created_at else "",
        )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/tokens",
    response_model=EmbedTokenResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/minute")
async def create_embed_token(
    request: Request,
    body: EmbedTokenCreate,
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
) -> EmbedTokenResponse:
    """Create a new embed token for the authenticated user.

    The returned token is used as a `data-token` attribute on the embed widget.
    Each token can optionally scope the allowed origins and pre-set default filter
    values for the embedded map view.
    """
    token_value = secrets.token_urlsafe(32)

    row = EmbedToken(
        token=token_value,
        label=body.label,
        allowed_origins=body.allowed_origins,
        default_filters=body.default_filters,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return EmbedTokenResponse.from_orm_row(row)


@router.get("/tokens", response_model=list[EmbedTokenResponse])
@limiter.limit("30/minute")
async def list_embed_tokens(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
) -> list[EmbedTokenResponse]:
    """List active embed tokens for the authenticated user.

    Note: tokens are stored without a per-user FK in the MVP schema (the
    EmbedToken model has no auth0_user_id column).  For now this endpoint
    returns all active tokens; a user-scoped FK can be added in a later
    migration without changing the API surface.
    """
    stmt = select(EmbedToken).where(EmbedToken.is_active == True).order_by(  # noqa: E712
        EmbedToken.created_at.desc()
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [EmbedTokenResponse.from_orm_row(r) for r in rows]


@router.delete("/tokens/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("20/minute")
async def deactivate_embed_token(
    request: Request,
    token_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
) -> None:
    """Deactivate an embed token.

    Deactivated tokens are retained in the database for audit purposes but
    will not be accepted by the API on future embed widget requests.
    """
    stmt = (
        update(EmbedToken)
        .where(EmbedToken.token == token_id)
        .values(is_active=False)
        .returning(EmbedToken.id)
    )
    result = await db.execute(stmt)
    if result.fetchone() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Embed token '{token_id}' not found",
        )
    await db.commit()

"""Saved states router — persisted filter states for authenticated users.

Endpoints:
  GET    /saved-states          — list the current user's saved states
  POST   /saved-states          — create a new saved state (requires login)
  DELETE /saved-states/{id}     — delete a saved state (requires login, own states only)
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.db import UserSavedState as UserSavedStateORM
from app.models.schemas import UserSavedState, UserSavedStateCreate

router = APIRouter(prefix="/saved-states", tags=["saved-states"])


@router.get("", response_model=list[UserSavedState])
async def list_saved_states(
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
) -> list[UserSavedState]:
    """Return all saved filter states for the authenticated user, newest first."""
    stmt = (
        select(UserSavedStateORM)
        .where(UserSavedStateORM.auth0_user_id == user["sub"])
        .order_by(UserSavedStateORM.created_at.desc())
    )
    result = await db.execute(stmt)
    return [UserSavedState.model_validate(row) for row in result.scalars().all()]


@router.post("", response_model=UserSavedState, status_code=status.HTTP_201_CREATED)
async def create_saved_state(
    body: UserSavedStateCreate,
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
) -> UserSavedState:
    """Persist a new filter state for the authenticated user.

    If ``is_default`` is ``True``, any existing default is left as-is;
    call DELETE + POST to replace a default.
    """
    new_id = uuid.uuid4()
    stmt = insert(UserSavedStateORM).values(
        id=new_id,
        auth0_user_id=user["sub"],
        name=body.name,
        description=body.description,
        filter_state=body.filter_state,
        is_default=body.is_default,
    ).returning(UserSavedStateORM)

    result = await db.execute(stmt)
    await db.commit()
    row = result.scalar_one()
    return UserSavedState.model_validate(row)


@router.delete("/{state_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_state(
    state_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
) -> None:
    """Delete a saved state.  Only the owning user may delete their own states."""
    stmt = delete(UserSavedStateORM).where(
        UserSavedStateORM.id == state_id,
        UserSavedStateORM.auth0_user_id == user["sub"],
    ).returning(UserSavedStateORM.id)

    result = await db.execute(stmt)
    await db.commit()

    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saved state '{state_id}' not found or does not belong to you",
        )

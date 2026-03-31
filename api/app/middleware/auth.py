"""Auth0 JWT validation middleware and FastAPI dependencies.

Provides two dependencies:
  - `get_current_user` — raises HTTP 401 if the token is missing or invalid.
  - `get_optional_user` — returns None instead of raising, for endpoints that
    accept both anonymous and authenticated callers.

JWKS keys are cached in-process for 1 hour to avoid hitting Auth0 on every
request.
"""

from __future__ import annotations

import time
from typing import Any, Optional

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import settings

# ── JWKS in-memory cache ──────────────────────────────────────────────────────
_jwks_cache: dict[str, Any] = {}
_jwks_fetched_at: float = 0.0
_JWKS_TTL_SECONDS = 3600  # Re-fetch JWKS after 1 hour

_bearer_scheme = HTTPBearer(auto_error=False)


async def _get_jwks() -> dict[str, Any]:
    """Fetch JWKS from Auth0, using an in-process time-based cache."""
    global _jwks_cache, _jwks_fetched_at

    now = time.monotonic()
    if _jwks_cache and (now - _jwks_fetched_at) < _JWKS_TTL_SECONDS:
        return _jwks_cache

    jwks_url = f"https://{settings.AUTH0_DOMAIN}/.well-known/jwks.json"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(jwks_url)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        _jwks_fetched_at = now
        return _jwks_cache


async def verify_token(token: str) -> dict[str, Any]:
    """Validate an Auth0 JWT and return its decoded payload.

    Args:
        token: Raw JWT string (without 'Bearer ' prefix).

    Returns:
        Decoded token payload dict.

    Raises:
        HTTPException 401 on any validation failure.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        jwks = await _get_jwks()

        # Decode header to find the matching key
        unverified_header = jwt.get_unverified_header(token)
        rsa_key: dict[str, str] = {}

        for key in jwks.get("keys", []):
            if key.get("kid") == unverified_header.get("kid"):
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"],
                }
                break

        if not rsa_key:
            raise credentials_exception

        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=settings.AUTH0_AUDIENCE,
            issuer=f"https://{settings.AUTH0_DOMAIN}/",
        )
        return payload

    except JWTError:
        raise credentials_exception
    except httpx.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to reach authentication service",
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> dict[str, Any]:
    """FastAPI dependency — returns the decoded token or raises HTTP 401."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await verify_token(credentials.credentials)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Optional[dict[str, Any]]:
    """FastAPI dependency — returns the decoded token or None.

    Never raises; suitable for endpoints that work for both authenticated
    and anonymous callers.
    """
    if credentials is None:
        return None
    try:
        return await verify_token(credentials.credentials)
    except HTTPException:
        return None

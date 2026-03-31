"""slowapi rate-limiter setup.

Exports a shared `limiter` instance that is attached to the FastAPI app in
`main.py`.  Individual route handlers import `limiter` and apply the
`@limiter.limit(...)` decorator.

The limiter uses the client's remote IP address as the key by default, which
works correctly behind a proxy when FORWARDED / X-Forwarded-For headers are
trusted (configure your reverse proxy accordingly).
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request
from starlette.responses import JSONResponse

# ── Limiter instance shared across the entire application ─────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


# ── Custom 429 handler ────────────────────────────────────────────────────────
def _rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Return a structured JSON 429 response instead of slowapi's plain text."""
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded",
            "limit": str(exc.detail),
            "retry_after": request.headers.get("Retry-After"),
        },
        headers={"Retry-After": request.headers.get("Retry-After", "60")},
    )

"""Optional Redis cache service for the EWasteTradeFlow API.

If Redis is unavailable (or REDIS_URL is not configured) all cache operations
are silently no-ops.  This keeps the API fully functional without Redis — at
the cost of serving uncached responses.

Usage::

    from app.services.cache import cache_service, make_cache_key

    key = make_cache_key("choropleth", metric, year)
    cached = await cache_service.get(key)
    if cached is None:
        cached = await compute_expensive_thing()
        await cache_service.set(key, cached, ttl_seconds=21600)
    return cached
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# redis.asyncio is the async interface shipped with the redis-py package (>=4.2)
try:
    import redis.asyncio as aioredis  # type: ignore[import]
    _REDIS_AVAILABLE = True
except ImportError:
    _REDIS_AVAILABLE = False


def make_cache_key(*args: Any) -> str:
    """Return a deterministic SHA-256 cache key from the given positional args.

    Args are JSON-serialised (sorted keys for dicts) and joined before hashing
    so that ``make_cache_key("choropleth", "prs", 2020)`` is stable across
    Python runtimes.
    """
    normalised = json.dumps(args, sort_keys=True, default=str)
    return hashlib.sha256(normalised.encode()).hexdigest()


class CacheService:
    """Thin wrapper around redis.asyncio with graceful degradation.

    All public methods silently swallow connection errors so that a Redis
    outage never brings down the API.
    """

    def __init__(self, redis_url: Optional[str] = None) -> None:
        self._client: Optional[Any] = None  # aioredis.Redis
        self._redis_url = redis_url

    async def _get_client(self) -> Optional[Any]:
        """Lazily initialise the Redis connection pool."""
        if not _REDIS_AVAILABLE or self._redis_url is None:
            return None

        if self._client is None:
            try:
                self._client = aioredis.from_url(
                    self._redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                )
            except Exception as exc:
                logger.warning("Redis connection failed: %s", exc)
                return None

        return self._client

    async def get(self, key: str) -> Optional[dict[str, Any]]:
        """Return a cached value or None if not found / Redis unavailable."""
        client = await self._get_client()
        if client is None:
            return None
        try:
            raw = await client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as exc:
            logger.warning("Cache GET error for key=%s: %s", key, exc)
            return None

    async def set(
        self,
        key: str,
        value: dict[str, Any],
        ttl_seconds: int = 3600,
    ) -> None:
        """Serialise and store a value with the given TTL.  No-op on failure."""
        client = await self._get_client()
        if client is None:
            return
        try:
            serialised = json.dumps(value, default=str)
            await client.set(key, serialised, ex=ttl_seconds)
        except Exception as exc:
            logger.warning("Cache SET error for key=%s: %s", key, exc)

    async def invalidate_prefix(self, prefix: str) -> None:
        """Delete all keys matching ``prefix*``.  No-op on failure.

        Uses SCAN to avoid blocking the Redis event loop with KEYS.
        """
        client = await self._get_client()
        if client is None:
            return
        try:
            cursor = 0
            while True:
                cursor, keys = await client.scan(cursor, match=f"{prefix}*", count=100)
                if keys:
                    await client.delete(*keys)
                if cursor == 0:
                    break
        except Exception as exc:
            logger.warning("Cache INVALIDATE error for prefix=%s: %s", prefix, exc)

    async def close(self) -> None:
        """Close the underlying Redis connection pool."""
        if self._client is not None:
            try:
                await self._client.aclose()
            except Exception:
                pass
            self._client = None


# Module-level singleton initialised lazily from config during app startup.
# Routers and services should import this instance.
cache_service: CacheService = CacheService()


def init_cache(redis_url: Optional[str]) -> None:
    """Call once during application startup to configure the Redis URL."""
    global cache_service
    cache_service = CacheService(redis_url=redis_url)

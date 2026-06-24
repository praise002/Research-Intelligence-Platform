"""
Redis client — does double duty as Celery's message broker AND the
platform's caching layer.

Three caching levels share this one client, distinguished only by TTL:
  - semantic cache   → SEMANTIC_CACHE_TTL (24h) — query embedding + result
  - news/social cache → NEWS_CACHE_TTL (24h)     — changes daily
  - website cache     → WEBSITE_CACHE_TTL (7d)    — pricing pages rarely change overnight

Cache key format everywhere: competitor_name + source_type + date
(see src/utils/cache.py for the key builder).
"""

import json
from typing import Any

import redis.asyncio as redis

from src.config import settings
from src.custom_logging import get_logger
from src.exceptions import ServiceError

log = get_logger(__name__)


class RedisClient:
    """Async wrapper around redis.asyncio — get/set/delete/exists with TTL support."""

    def __init__(self):
        self.redis = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )

    async def get(self, key: str) -> Any | None:
        """
        Fetch and JSON-decode a cached value. Returns None on cache miss
        OR on Redis failure — a Redis outage should never crash a research
        job, just force a fresh fetch instead.
        """
        try:
            raw = await self.redis.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except redis.RedisError as exc:
            log.warning("redis.get.failed", key=key, error=str(exc))
            return None  # treat as cache miss, don't propagate — caching is an optimisation, not a dependency

    async def set(self, key: str, value: Any, ttl: int) -> bool:
        """
        JSON-encode and store a value with a TTL in seconds.

        USAGE:
            await redis_client.set(
                build_cache_key("grey", "website", today),
                extracted_content,
                ttl=settings.WEBSITE_CACHE_TTL,
            )
        """
        try:
            await self.redis.set(key, json.dumps(value), ex=ttl)
            return True
        except redis.RedisError as exc:
            log.warning("redis.set.failed", key=key, error=str(exc))
            return False  # caching failure should not block the pipeline

    async def delete(self, key: str) -> bool:
        """Remove a key — used when invalidating stale cache entries."""
        try:
            await self.redis.delete(key)
            return True
        except redis.RedisError as exc:
            log.warning("redis.delete.failed", key=key, error=str(exc))
            return False

    async def exists(self, key: str) -> bool:
        """Check if a key exists without fetching its value."""
        try:
            return bool(await self.redis.exists(key))
        except redis.RedisError as exc:
            log.warning("redis.exists.failed", key=key, error=str(exc))
            return False

    async def increment(self, key: str, ttl: int) -> int:
        """
        Atomic increment with TTL — used for the on-demand research
        rate limiter (10 jobs/user/day, Section 13). First call sets
        the TTL; subsequent calls within the window just increment.

        USAGE:
            count = await redis_client.increment(f"rate_limit:{user_id}", ttl=86400)
            if count > settings.ON_DEMAND_JOBS_PER_DAY:
                raise RateLimitExceeded()
        """
        try:
            count = await self.redis.incr(key)  # type: ignore
            if count == 1:
                await self.redis.expire(key, ttl)
            return count
        except redis.RedisError as exc:
            log.error("redis.increment.failed", key=key, error=str(exc))
            # Unlike get/set, a rate-limit check failing open is a real risk —
            # raise here so the caller decides whether to fail open or closed.
            raise ServiceError("Rate limit check unavailable") from exc

    async def close(self):
        """Call during FastAPI/Celery shutdown to close the connection pool."""
        await self.redis.aclose()
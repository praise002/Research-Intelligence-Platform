"""
Cache key builder + thin convenience wrapper around RedisClient
(Phase 3.4), so the agent nodes don't have to remember the exact key
format or which TTL constant applies to which source type every time
they want to read or write the cache.

Cache key format everywhere (Section 2): competitor_name + source_type + date
"""

from datetime import date

from src.config import settings
from providers.redis_client import RedisClient

# TTL lookup by source_type — keeps the "which TTL applies to what" decision
# in exactly one place instead of scattered across every node that caches.
_TTL_BY_SOURCE_TYPE = {
    "website": settings.WEBSITE_CACHE_TTL,   # 7 days — pricing pages rarely change overnight
    "news": settings.NEWS_CACHE_TTL,         # 24 hours — changes daily
    "social": settings.NEWS_CACHE_TTL,       # 24 hours — same cadence as news
    "semantic": settings.SEMANTIC_CACHE_TTL, # 24 hours — similar queries return cached result
}


def build_cache_key(competitor_name: str, source_type: str, as_of: date | None = None) -> str:
    """
    Builds a consistent cache key: "grey:website:2026-06-19"

    USAGE:
        key = build_cache_key("grey", "website")
        cached = await get_cached(key)
    """
    as_of = as_of or date.today()
    normalised_name = competitor_name.lower().strip().replace(" ", "_")
    return f"{normalised_name}:{source_type}:{as_of.isoformat()}"


async def get_cached(redis_client: RedisClient, key: str):
    """Thin pass-through — kept here so callers import from cache.py, not redis_client.py directly."""
    return await redis_client.get(key)


async def set_cached(redis_client: RedisClient, key: str, value, source_type: str) -> bool:
    """
    Stores a value using the correct TTL for its source_type automatically —
    callers never need to know or pass a TTL number themselves.

    USAGE:
        await set_cached(redis_client, key, extracted_content, source_type="website")
    """
    ttl = _TTL_BY_SOURCE_TYPE.get(source_type, settings.NEWS_CACHE_TTL)
    return await redis_client.set(key, value, ttl=ttl)


async def invalidate_cache(redis_client: RedisClient, key: str) -> bool:
    """Removes a cache entry — used rarely, e.g. if a competitor's URL is manually corrected."""
    return await redis_client.delete(key)
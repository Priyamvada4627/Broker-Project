import json
import logging
import os
from typing import Any, Optional
import redis
from ..config import settings

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None

DEFAULT_CACHE_TTL_SECONDS = 300  # 5 minutes


def get_redis_client() -> Optional[redis.Redis]:
    """Return a connected Redis client, or None if unavailable."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    if os.getenv("TESTING") == "True":
        return None

    try:
        client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        client.ping()
        _redis_client = client
        logger.info("Connected to Redis cache.")
        return _redis_client
    except Exception as exc:
        logger.warning(f"Redis unavailable ({exc}). Continuing without cache.")
        return None


def build_property_cache_key(
    city: Optional[str] = None,
    purpose: Optional[str] = None,
    property_type: Optional[str] = None,
    price_min: Optional[int] = None,
    price_max: Optional[int] = None,
    limit: int = 10,
    offset: int = 0,
) -> str:
    """Build a deterministic Redis key for property list queries."""
    c = city.strip().lower() if city else "any"
    p = purpose.strip().lower() if purpose else "any"
    pt = property_type.strip().lower() if property_type else "any"
    pmin = str(price_min) if price_min is not None else "any"
    pmax = str(price_max) if price_max is not None else "any"
    return f"properties:list:c={c}:p={p}:pt={pt}:min={pmin}:max={pmax}:lim={limit}:off={offset}"


def get_cache(key: str) -> Optional[Any]:
    """Retrieve and deserialize a JSON value from Redis, returning None on miss or error."""
    global _redis_client
    client = get_redis_client()
    if not client:
        return None

    try:
        raw = client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as exc:
        logger.warning(f"Redis GET failed for key '{key}': {exc}")
        _redis_client = None
        return None


def set_cache(key: str, value: Any, ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS) -> None:
    """Serialize and store a JSON value in Redis with an expiration TTL."""
    global _redis_client
    client = get_redis_client()
    if not client:
        return

    try:
        client.setex(key, ttl_seconds, json.dumps(value))
    except Exception as exc:
        logger.warning(f"Redis SETEX failed for key '{key}': {exc}")
        _redis_client = None


def invalidate_properties_cache() -> None:
    """Invalidate all cached property listing queries using non-blocking SCAN."""
    global _redis_client
    client = get_redis_client()
    if not client:
        return

    try:
        keys = list(client.scan_iter(match="properties:list:*"))
        if keys:
            client.delete(*keys)
            logger.info(f"Invalidated {len(keys)} cached property list key(s).")
    except Exception as exc:
        logger.warning(f"Redis cache invalidation failed: {exc}")
        _redis_client = None

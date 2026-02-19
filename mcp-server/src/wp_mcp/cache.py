"""Redis cache manager for WordPress MCP server."""

from __future__ import annotations

import functools
import json
import logging
from typing import Any, Callable, Optional, cast

import redis.asyncio as redis

from wp_mcp.config import config

logger = logging.getLogger(__name__)


def ensure_redis_connection(func: Callable) -> Callable:
    """Decorator to ensure Redis connection before executing cache operations."""

    @functools.wraps(func)
    async def wrapper(self: CacheManager, *args: Any, **kwargs: Any) -> Any:
        if not self.redis:
            await self.connect()
            if not self.redis:
                # Return appropriate default based on operation
                if func.__name__ == "get":
                    return None
                return
        return await func(self, *args, **kwargs)

    return wrapper


class CacheManager:
    """Async Redis cache manager with TTL support."""

    def __init__(self) -> None:
        """Initialize Redis connection."""
        self.redis: Optional[redis.Redis] = None

    async def connect(self) -> None:
        """Connect to Redis server."""
        if self.redis is None:
            try:
                self.redis = await redis.from_url(
                    config.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                )
                # Test connection
                await self.redis.ping()
                logger.info("Connected to Redis at %s", config.redis_url)
            except Exception as e:
                logger.error("Failed to connect to Redis: %s", e)
                self.redis = None

    async def disconnect(self) -> None:
        """Disconnect from Redis server."""
        if self.redis:
            await self.redis.aclose()
            self.redis = None
            logger.info("Disconnected from Redis")

    @ensure_redis_connection
    async def get(self, key: str) -> Optional[dict[str, Any]]:
        """Get cached value by key.

        Args:
            key: Cache key

        Returns:
            Cached value as dict, or None if not found or Redis unavailable
        """
        assert self.redis is not None  # Guaranteed by decorator
        try:
            value = await self.redis.get(key)
            if value:
                logger.debug("Cache HIT: %s", key)
                return cast(dict[str, Any], json.loads(value))
            logger.debug("Cache MISS: %s", key)
            return None
        except Exception as e:
            logger.warning("Cache get error for key %s: %s", key, e)
            return None

    @ensure_redis_connection
    async def set(self, key: str, value: dict[str, Any], ttl: int = 300) -> None:
        """Set cached value with TTL.

        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl: Time to live in seconds (default 5 minutes)
        """
        assert self.redis is not None  # Guaranteed by decorator
        try:
            await self.redis.setex(key, ttl, json.dumps(value))
            logger.debug("Cache SET: %s (TTL: %ds)", key, ttl)
        except Exception as e:
            logger.warning("Cache set error for key %s: %s", key, e)

    @ensure_redis_connection
    async def delete(self, key: str) -> None:
        """Delete cached value by key.

        Args:
            key: Cache key
        """
        assert self.redis is not None  # Guaranteed by decorator
        try:
            await self.redis.delete(key)
            logger.debug("Cache DELETE: %s", key)
        except Exception as e:
            logger.warning("Cache delete error for key %s: %s", key, e)

    @ensure_redis_connection
    async def invalidate_pattern(self, pattern: str) -> None:
        """Invalidate all keys matching pattern.

        Args:
            pattern: Redis pattern (e.g., "post:*", "posts:*")
        """
        assert self.redis is not None  # Guaranteed by decorator
        try:
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                await self.redis.delete(*keys)
                logger.debug("Cache INVALIDATE: %s (%d keys)", pattern, len(keys))
        except Exception as e:
            logger.warning("Cache invalidate error for pattern %s: %s", pattern, e)

    @ensure_redis_connection
    async def clear_all(self) -> None:
        """Clear all cached data (use with caution)."""
        assert self.redis is not None  # Guaranteed by decorator
        try:
            await self.redis.flushdb()
            logger.info("Cache cleared (flushdb)")
        except Exception as e:
            logger.warning("Cache clear error: %s", e)


# Global cache instance
cache = CacheManager()

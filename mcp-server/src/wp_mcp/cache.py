"""Redis cache manager for WordPress MCP server."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import redis.asyncio as redis

from wp_mcp.config import config

logger = logging.getLogger(__name__)


class CacheManager:
    """Async Redis cache manager with TTL support."""

    def __init__(self):
        """Initialize Redis connection."""
        self.redis: Optional[redis.Redis] = None

    async def connect(self):
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

    async def disconnect(self):
        """Disconnect from Redis server."""
        if self.redis:
            await self.redis.aclose()
            self.redis = None
            logger.info("Disconnected from Redis")

    async def get(self, key: str) -> Optional[dict[str, Any]]:
        """Get cached value by key.

        Args:
            key: Cache key

        Returns:
            Cached value as dict, or None if not found or Redis unavailable
        """
        if not self.redis:
            await self.connect()
            if not self.redis:
                return None

        try:
            value = await self.redis.get(key)
            if value:
                logger.debug("Cache HIT: %s", key)
                return json.loads(value)
            logger.debug("Cache MISS: %s", key)
            return None
        except Exception as e:
            logger.warning("Cache get error for key %s: %s", key, e)
            return None

    async def set(self, key: str, value: dict[str, Any], ttl: int = 300):
        """Set cached value with TTL.

        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl: Time to live in seconds (default 5 minutes)
        """
        if not self.redis:
            await self.connect()
            if not self.redis:
                return

        try:
            await self.redis.setex(key, ttl, json.dumps(value))
            logger.debug("Cache SET: %s (TTL: %ds)", key, ttl)
        except Exception as e:
            logger.warning("Cache set error for key %s: %s", key, e)

    async def delete(self, key: str):
        """Delete cached value by key.

        Args:
            key: Cache key
        """
        if not self.redis:
            await self.connect()
            if not self.redis:
                return

        try:
            await self.redis.delete(key)
            logger.debug("Cache DELETE: %s", key)
        except Exception as e:
            logger.warning("Cache delete error for key %s: %s", key, e)

    async def invalidate_pattern(self, pattern: str):
        """Invalidate all keys matching pattern.

        Args:
            pattern: Redis pattern (e.g., "post:*", "posts:*")
        """
        if not self.redis:
            await self.connect()
            if not self.redis:
                return

        try:
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                await self.redis.delete(*keys)
                logger.debug("Cache INVALIDATE: %s (%d keys)", pattern, len(keys))
        except Exception as e:
            logger.warning("Cache invalidate error for pattern %s: %s", pattern, e)

    async def clear_all(self):
        """Clear all cached data (use with caution)."""
        if not self.redis:
            await self.connect()
            if not self.redis:
                return

        try:
            await self.redis.flushdb()
            logger.info("Cache cleared (flushdb)")
        except Exception as e:
            logger.warning("Cache clear error: %s", e)


# Global cache instance
cache = CacheManager()

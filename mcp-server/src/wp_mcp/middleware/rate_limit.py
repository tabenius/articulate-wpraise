"""Rate limiting middleware using Redis."""

from __future__ import annotations

import logging
import time
from typing import Optional

from wp_mcp.cache import cache

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, limit: int, window: int, retry_after: int):
        self.limit = limit
        self.window = window
        self.retry_after = retry_after
        super().__init__(
            f"Rate limit exceeded: {limit} requests per {window}s. Retry after {retry_after}s"
        )


class RateLimiter:
    """Redis-based rate limiter with sliding window."""

    def __init__(
        self,
        max_requests: int = 100,
        window: int = 60,
        identifier_prefix: str = "rate_limit",
    ):
        """Initialize rate limiter.

        Args:
            max_requests: Maximum number of requests allowed in the window
            window: Time window in seconds
            identifier_prefix: Prefix for Redis keys
        """
        self.max_requests = max_requests
        self.window = window
        self.identifier_prefix = identifier_prefix

    async def check_rate_limit(
        self, identifier: str, cost: int = 1
    ) -> tuple[bool, int]:
        """Check if request is within rate limit.

        Args:
            identifier: User/client identifier (e.g., user_id, IP address)
            cost: Cost of this request (default 1, some operations may cost more)

        Returns:
            Tuple of (allowed: bool, remaining: int)

        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        if cache.redis is None:
            await cache.connect()
        if cache.redis is None:
            # Redis unavailable, allow request (fail open)
            return True, self.max_requests

        key = f"{self.identifier_prefix}:{identifier}"

        try:
            # Try to get current count
            current_str = await cache.redis.get(key)
            current = int(current_str) if current_str else 0

            # Check if limit would be exceeded
            if current + cost > self.max_requests:
                # Get TTL to calculate retry_after
                ttl = await cache.redis.ttl(key)
                retry_after = ttl if ttl > 0 else self.window
                raise RateLimitExceeded(self.max_requests, self.window, retry_after)

            # Increment counter
            new_count = await cache.redis.incrby(key, cost)

            # Set expiry on first request
            if new_count == cost:
                await cache.redis.expire(key, self.window)

            remaining = max(0, self.max_requests - new_count)
            return True, remaining

        except RateLimitExceeded:
            raise
        except Exception as e:
            # If Redis is unavailable, allow the request (fail open)
            logger.warning("Rate limit check failed, allowing request: %s", e)
            return True, self.max_requests

    async def reset(self, identifier: str) -> None:
        """Reset rate limit for an identifier.

        Args:
            identifier: User/client identifier
        """
        if cache.redis is None:
            await cache.connect()
        if cache.redis is None:
            return

        key = f"{self.identifier_prefix}:{identifier}"
        try:
            await cache.redis.delete(key)
            logger.info("Rate limit reset for %s", identifier)
        except Exception as e:
            logger.warning("Failed to reset rate limit for %s: %s", identifier, e)

    async def get_status(self, identifier: str) -> dict:
        """Get rate limit status for an identifier.

        Args:
            identifier: User/client identifier

        Returns:
            Dict with limit, remaining, reset_at
        """
        if cache.redis is None:
            await cache.connect()
        if cache.redis is None:
            return {
                "limit": self.max_requests,
                "remaining": self.max_requests,
                "used": 0,
                "reset_at": None,
            }

        key = f"{self.identifier_prefix}:{identifier}"
        try:
            current_str = await cache.redis.get(key)
            current = int(current_str) if current_str else 0
            ttl = await cache.redis.ttl(key)

            return {
                "limit": self.max_requests,
                "remaining": max(0, self.max_requests - current),
                "used": current,
                "reset_at": int(time.time() + ttl) if ttl > 0 else None,
            }
        except Exception as e:
            logger.warning("Failed to get rate limit status for %s: %s", identifier, e)
            return {
                "limit": self.max_requests,
                "remaining": self.max_requests,
                "used": 0,
                "reset_at": None,
            }


# Default rate limiters with different limits
tool_rate_limiter = RateLimiter(
    max_requests=100,  # 100 tool calls per minute
    window=60,
    identifier_prefix="rate_limit:tool",
)

graphql_rate_limiter = RateLimiter(
    max_requests=1000,  # 1000 GraphQL queries per hour
    window=3600,
    identifier_prefix="rate_limit:graphql",
)

ai_chat_rate_limiter = RateLimiter(
    max_requests=10,  # 10 concurrent AI requests
    window=60,
    identifier_prefix="rate_limit:ai_chat",
)

# Heavy operation rate limiter
heavy_operation_limiter = RateLimiter(
    max_requests=10,  # 10 heavy operations per 5 minutes
    window=300,
    identifier_prefix="rate_limit:heavy",
)

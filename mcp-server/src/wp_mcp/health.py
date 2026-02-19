"""Health check and monitoring endpoints."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from wp_mcp.cache import cache
from wp_mcp.config import config
from wp_mcp.logging_config import metrics

logger = logging.getLogger(__name__)


async def check_redis_health() -> dict[str, Any]:
    """Check Redis connection health.

    Returns:
        Health status dict
    """
    try:
        if cache.redis is None:
            await cache.connect()

        if cache.redis:
            # Test ping
            await cache.redis.ping()  # type: ignore[misc]
            # Get info
            info = await cache.redis.info()
            return {
                "status": "healthy",
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "uptime_seconds": info.get("uptime_in_seconds", 0),
            }
        else:
            return {
                "status": "unavailable",
                "message": "Redis not configured or unavailable",
            }
    except Exception as e:
        logger.error("Redis health check failed: %s", e)
        return {
            "status": "unhealthy",
            "error": str(e),
        }


async def check_wordpress_health() -> dict[str, Any]:
    """Check WordPress connection health.

    Returns:
        Health status dict
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Try to reach WordPress
            response = await client.get(config.wp_url)
            response.raise_for_status()

            # Try to reach GraphQL endpoint
            graphql_response = await client.post(
                config.wp_graphql_endpoint,
                json={"query": "{ __typename }"},
                auth=config.wp_auth,  # type: ignore[arg-type]
            )
            graphql_response.raise_for_status()

            return {
                "status": "healthy",
                "url": config.wp_url,
                "graphql_endpoint": config.wp_graphql_endpoint,
                "response_time_ms": int(response.elapsed.total_seconds() * 1000),
            }
    except httpx.HTTPStatusError as e:
        logger.error("WordPress health check failed with HTTP error: %s", e)
        return {
            "status": "unhealthy",
            "error": f"HTTP {e.response.status_code}",
            "url": config.wp_url,
        }
    except Exception as e:
        logger.error("WordPress health check failed: %s", e)
        return {
            "status": "unhealthy",
            "error": str(e),
            "url": config.wp_url,
        }


async def check_celery_health() -> dict[str, Any]:
    """Check Celery worker health.

    Returns:
        Health status dict
    """
    try:
        from wp_mcp.tasks import celery_app

        # Check if workers are available
        inspect = celery_app.control.inspect()
        stats = inspect.stats()

        if stats:
            worker_count = len(stats)
            return {
                "status": "healthy",
                "workers": worker_count,
                "broker": config.celery_broker_url,
            }
        else:
            return {
                "status": "degraded",
                "message": "No workers responding",
                "broker": config.celery_broker_url,
            }
    except Exception as e:
        logger.error("Celery health check failed: %s", e)
        return {
            "status": "unhealthy",
            "error": str(e),
        }


async def get_health_status() -> dict[str, Any]:
    """Get overall health status of all services.

    Returns:
        Complete health status
    """
    redis_health = await check_redis_health()
    wordpress_health = await check_wordpress_health()
    celery_health = await check_celery_health()

    # Determine overall status
    statuses = [
        redis_health.get("status"),
        wordpress_health.get("status"),
        celery_health.get("status"),
    ]

    if all(s == "healthy" for s in statuses):
        overall_status = "healthy"
    elif any(s == "unhealthy" for s in statuses):
        overall_status = "unhealthy"
    else:
        overall_status = "degraded"

    return {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "services": {
            "redis": redis_health,
            "wordpress": wordpress_health,
            "celery": celery_health,
        },
        "metrics": metrics.get_stats(),
    }


async def get_readiness_status() -> dict[str, Any]:
    """Get readiness status (can accept traffic).

    Returns:
        Readiness status
    """
    wordpress_health = await check_wordpress_health()

    # Server is ready if WordPress is accessible
    is_ready = wordpress_health.get("status") == "healthy"

    return {
        "ready": is_ready,
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "services": {
            "wordpress": wordpress_health,
        },
    }


async def get_liveness_status() -> dict[str, Any]:
    """Get liveness status (server is running).

    Returns:
        Liveness status
    """
    return {
        "alive": True,
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
    }

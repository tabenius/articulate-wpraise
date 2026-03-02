"""Health check and monitoring endpoints."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from articulate_mcp.cache import cache
from articulate_mcp.config import config
from articulate_mcp.database import db
from articulate_mcp.logging_config import metrics

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
    tenants: list[dict[str, Any]] = []
    try:
        # Only poll active/running tenants to avoid expected failures on stopped/deleted sites.
        tenants = await db.fetchall(
            """SELECT id, name, domain, wp_url, wp_graphql_endpoint, status
               FROM tenants
               WHERE status IN ('running', 'active')
               ORDER BY created_at DESC"""
        )
    except Exception as e:
        logger.warning("Failed to load tenants for health check: %s", e)

    # Backward-compatible fallback for single-site deployments.
    if not tenants and config.wp_url:
        tenants = [{
            "id": None,
            "name": "default",
            "domain": None,
            "wp_url": config.wp_url,
            "wp_graphql_endpoint": config.wp_graphql_endpoint,
            "status": "running",
        }]

    if not tenants:
        return {
            "status": "unavailable",
            "message": "No running tenants found",
            "checked_tenants": 0,
        }

    try:
        async def check_tenant(tenant: dict[str, Any], client: httpx.AsyncClient) -> dict[str, Any]:
            wp_url = str(tenant.get("wp_url") or "").rstrip("/")
            graphql_endpoint = str(tenant.get("wp_graphql_endpoint") or "").rstrip("/")
            check_url = f"{wp_url}/wp-json/"
            try:
                response = await client.get(check_url)
                response.raise_for_status()

                # Probe GraphQL when endpoint is available; don't fail tenant if GraphQL is disabled.
                graphql_status = "skipped"
                if graphql_endpoint:
                    try:
                        graphql_response = await client.post(
                            graphql_endpoint,
                            json={"query": "{ __typename }"},
                            auth=config.wp_auth,  # type: ignore[arg-type]
                        )
                        graphql_response.raise_for_status()
                        graphql_status = "healthy"
                    except Exception as graphql_error:
                        graphql_status = f"unhealthy: {graphql_error}"

                return {
                    "tenant_id": tenant.get("id"),
                    "tenant_name": tenant.get("name"),
                    "tenant_domain": tenant.get("domain"),
                    "status": "healthy",
                    "url": wp_url,
                    "graphql_endpoint": graphql_endpoint,
                    "graphql_status": graphql_status,
                    "response_time_ms": int(response.elapsed.total_seconds() * 1000),
                }
            except httpx.HTTPStatusError as e:
                logger.error("Tenant WordPress health failed with HTTP error [%s]: %s", tenant.get("name"), e)
                return {
                    "tenant_id": tenant.get("id"),
                    "tenant_name": tenant.get("name"),
                    "tenant_domain": tenant.get("domain"),
                    "status": "unhealthy",
                    "error": f"HTTP {e.response.status_code}",
                    "url": wp_url,
                    "graphql_endpoint": graphql_endpoint,
                }
            except Exception as e:
                logger.error("Tenant WordPress health failed [%s]: %s", tenant.get("name"), e)
                return {
                    "tenant_id": tenant.get("id"),
                    "tenant_name": tenant.get("name"),
                    "tenant_domain": tenant.get("domain"),
                    "status": "unhealthy",
                    "error": str(e),
                    "url": wp_url,
                    "graphql_endpoint": graphql_endpoint,
                }

        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            tenant_results = await asyncio.gather(*(check_tenant(tenant, client) for tenant in tenants))

        healthy_count = sum(1 for result in tenant_results if result.get("status") == "healthy")
        total_count = len(tenant_results)

        if healthy_count == total_count:
            overall_status = "healthy"
        elif healthy_count == 0:
            overall_status = "unhealthy"
        else:
            overall_status = "degraded"

        return {
            "status": overall_status,
            "checked_tenants": total_count,
            "healthy_tenants": healthy_count,
            "unhealthy_tenants": total_count - healthy_count,
            "tenants": tenant_results,
        }
    except Exception as e:
        logger.error("WordPress tenant health check failed: %s", e)
        return {
            "status": "unhealthy",
            "error": str(e),
            "checked_tenants": 0,
        }


async def check_celery_health() -> dict[str, Any]:
    """Check Celery worker health.

    Returns:
        Health status dict
    """
    try:
        from articulate_mcp.tasks import celery_app

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

    # Server is ready as long as at least one tenant is healthy and none are globally unavailable.
    is_ready = wordpress_health.get("status") in {"healthy", "degraded"}

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

"""Health, metrics, audit, and profiling endpoints."""

from __future__ import annotations

import logging
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


async def health_endpoint(request):
    """Basic health check endpoint."""
    from wp_mcp.health import get_liveness_status

    status = await get_liveness_status()
    return JSONResponse(status)


async def health_ready_endpoint(request):
    """Readiness check endpoint (can accept traffic)."""
    from wp_mcp.health import get_readiness_status

    status = await get_readiness_status()
    status_code = 200 if status.get("ready") else 503
    return JSONResponse(status, status_code=status_code)


async def health_deep_endpoint(request):
    """Deep health check endpoint (all dependencies)."""
    from wp_mcp.health import get_health_status

    status = await get_health_status()
    status_code = 200 if status.get("status") == "healthy" else 503
    return JSONResponse(status, status_code=status_code)


async def metrics_endpoint(request):
    """Metrics endpoint."""
    from wp_mcp.logging_config import metrics

    stats = metrics.get_stats()
    return JSONResponse(stats)


async def audit_logs_endpoint(request):
    """Audit logs query endpoint (requires authentication)."""
    from wp_mcp.audit import AuditLog

    # User will be in request.state if authenticated
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    # Parse query parameters
    limit = int(request.query_params.get("limit", "100"))
    event_type = request.query_params.get("event_type")

    # Get logs
    logs = await AuditLog.get_recent_events(
        limit=min(limit, 1000),  # Cap at 1000
        user_id=user.get("id") if not user.get("is_admin") else None,  # Regular users see only their own logs
        event_type=event_type,
    )

    return JSONResponse({"logs": logs})


async def audit_summary_endpoint(request):
    """Security event summary endpoint (requires authentication)."""
    from wp_mcp.audit import AuditLog

    # User will be in request.state if authenticated
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    hours = int(request.query_params.get("hours", "24"))

    # Get security summary
    summary = await AuditLog.get_security_summary(hours=hours)

    return JSONResponse(summary)


async def profiling_stats_endpoint(request):
    """Get profiling statistics endpoint."""
    from wp_mcp.profiling import get_profiling_stats

    try:
        data = await request.json()
        organization_id = data.get("organization_id")
        function_name = data.get("function_name")
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        limit = data.get("limit", 100)

        stats = await get_profiling_stats(
            organization_id=organization_id,
            function_name=function_name,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )

        return JSONResponse({
            "success": True,
            "stats": stats,
        })
    except Exception as e:
        logger.error(f"Failed to get profiling stats: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

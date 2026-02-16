"""WordPress MCP Server entry point.

Exposes WordPress content management tools via the Model Context Protocol.
Supports HTTP/SSE transport for Docker deployment.
"""

from __future__ import annotations

import logging
import os

from mcp.server.fastmcp import FastMCP
from starlette.responses import JSONResponse
from starlette.routing import Route

from wp_mcp.config import config
from wp_mcp.logging_config import configure_logging
from wp_mcp.tools import posts, pages, blocks, media, search, taxonomies, revisions

# Configure structured logging
json_format = os.getenv("LOG_FORMAT", "human") == "json"
log_level = os.getenv("LOG_LEVEL", "INFO")
configure_logging(json_format=json_format, log_level=log_level)

logger = logging.getLogger("wp-mcp")

# Initialize MCP server
mcp = FastMCP(
    "WordPress MCP Server",
    instructions=(
        "This server provides tools for managing WordPress content via WPGraphQL. "
        "You can create, read, update, and delete posts and pages. "
        "You can also manipulate individual blocks within posts, including "
        "inserting, removing, moving, and updating blocks. "
        "Block types include: core/paragraph, core/heading, core/image, "
        "core/list, core/quote, core/code, core/columns, core/group, "
        "core/buttons, core/spacer, core/separator, and more."
    ),
)

# Register all tool modules
posts.register(mcp)
pages.register(mcp)
blocks.register(mcp)
media.register(mcp)
search.register(mcp)
taxonomies.register(mcp)
revisions.register(mcp)

logger.info("WordPress MCP Server initialized")
logger.info("Transport: %s", config.mcp_transport)
logger.info("WordPress URL: %s", config.wp_url)


# Health check endpoints
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


# Add custom routes to the FastMCP app
if hasattr(mcp, "_app"):
    # Add health check routes
    mcp._app.routes.extend(
        [
            Route("/health", health_endpoint),
            Route("/health/ready", health_ready_endpoint),
            Route("/health/live", health_endpoint),
            Route("/health/deep", health_deep_endpoint),
            Route("/metrics", metrics_endpoint),
        ]
    )


async def startup():
    """Initialize services on startup."""
    from wp_mcp.cache import cache
    from wp_mcp.database import db

    # Try to connect to Redis (optional)
    try:
        await cache.connect()
        logger.info("Redis caching enabled at %s", config.redis_url)
    except Exception as e:
        logger.warning("Redis unavailable, running without cache: %s", e)

    # Connect to database
    try:
        await db.connect()
        logger.info("Database connection established")
    except Exception as e:
        logger.error("Database connection failed: %s", e)


def main() -> None:
    """Run the MCP server."""
    import asyncio

    # Initialize cache on startup
    asyncio.run(startup())

    transport = config.mcp_transport

    if transport == "streamable-http":
        # For HTTP transport, use uvicorn to serve FastMCP directly
        import uvicorn

        uvicorn.run(
            mcp,
            host=config.mcp_host,
            port=config.mcp_port,
            log_level="info",
        )
    elif transport == "sse":
        # For SSE transport, use uvicorn as well
        import uvicorn

        uvicorn.run(
            mcp,
            host=config.mcp_host,
            port=config.mcp_port,
            log_level="info",
        )
    else:
        # Default to stdio for local development
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

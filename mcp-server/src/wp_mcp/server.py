"""WordPress MCP Server entry point.

Exposes WordPress content management tools via the Model Context Protocol.
Supports HTTP/SSE transport for Docker deployment.
"""

from __future__ import annotations

import logging
import os

from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import JSONResponse
from starlette.routing import Route

from wp_mcp.config import config
from wp_mcp.logging_config import configure_logging
from wp_mcp.middleware.auth import AuthMiddleware
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


# Authentication endpoints
async def register_endpoint(request):
    """User registration endpoint."""
    from wp_mcp.user_manager import UserManager

    try:
        data = await request.json()
        email = data.get("email")
        password = data.get("password")
        name = data.get("name", "")

        user = await UserManager.register_user(email, password, name)
        return JSONResponse(user, status_code=201)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Registration error: %s", e)
        return JSONResponse({"error": "Registration failed"}, status_code=500)


async def login_endpoint(request):
    """User login endpoint."""
    from wp_mcp.user_manager import UserManager

    try:
        data = await request.json()
        email = data.get("email")
        password = data.get("password")

        result = await UserManager.authenticate(email, password)
        if result:
            return JSONResponse(result)
        else:
            return JSONResponse({"error": "Invalid credentials"}, status_code=401)
    except Exception as e:
        logger.error("Login error: %s", e)
        return JSONResponse({"error": "Login failed"}, status_code=500)


async def logout_endpoint(request):
    """User logout endpoint."""
    from wp_mcp.user_manager import UserManager

    try:
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return JSONResponse({"error": "Session ID required"}, status_code=400)

        success = await UserManager.logout(session_id)
        if success:
            return JSONResponse({"success": True})
        else:
            return JSONResponse({"error": "Invalid session"}, status_code=404)
    except Exception as e:
        logger.error("Logout error: %s", e)
        return JSONResponse({"error": "Logout failed"}, status_code=500)


# Connection management endpoints
async def get_connections_endpoint(request):
    """Get user's WordPress connections."""
    from wp_mcp.user_manager import UserManager
    from wp_mcp.connection_manager import connection_manager

    try:
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return JSONResponse({"error": "Session required"}, status_code=401)

        user = await UserManager.get_user_from_session(session_id)
        if not user:
            return JSONResponse({"error": "Invalid session"}, status_code=401)

        connections = await connection_manager.get_connections(user["id"])
        return JSONResponse(connections)
    except Exception as e:
        logger.error("Get connections error: %s", e)
        return JSONResponse({"error": "Failed to get connections"}, status_code=500)


async def add_connection_endpoint(request):
    """Add new WordPress connection."""
    from wp_mcp.user_manager import UserManager
    from wp_mcp.connection_manager import connection_manager

    try:
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return JSONResponse({"error": "Session required"}, status_code=401)

        user = await UserManager.get_user_from_session(session_id)
        if not user:
            return JSONResponse({"error": "Invalid session"}, status_code=401)

        data = await request.json()
        connection = await connection_manager.add_connection(
            user_id=user["id"],
            name=data.get("name"),
            wp_url=data.get("wp_url"),
            wp_graphql_endpoint=data.get("wp_graphql_endpoint"),
            wp_user=data.get("wp_user"),
            wp_app_password=data.get("wp_app_password"),
        )
        return JSONResponse(connection, status_code=201)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Add connection error: %s", e)
        return JSONResponse({"error": "Failed to add connection"}, status_code=500)


async def update_connection_endpoint(request):
    """Update WordPress connection."""
    from wp_mcp.user_manager import UserManager
    from wp_mcp.connection_manager import connection_manager

    try:
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return JSONResponse({"error": "Session required"}, status_code=401)

        user = await UserManager.get_user_from_session(session_id)
        if not user:
            return JSONResponse({"error": "Invalid session"}, status_code=401)

        # Get connection ID from path
        connection_id = int(request.path_params.get("id"))
        data = await request.json()

        await connection_manager.update_connection(
            connection_id=connection_id,
            user_id=user["id"],
            name=data.get("name"),
            wp_url=data.get("wp_url"),
            wp_graphql_endpoint=data.get("wp_graphql_endpoint"),
            wp_user=data.get("wp_user"),
            wp_app_password=data.get("wp_app_password"),
        )
        return JSONResponse({"success": True})
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Update connection error: %s", e)
        return JSONResponse({"error": "Failed to update connection"}, status_code=500)


async def delete_connection_endpoint(request):
    """Delete WordPress connection."""
    from wp_mcp.user_manager import UserManager
    from wp_mcp.connection_manager import connection_manager

    try:
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return JSONResponse({"error": "Session required"}, status_code=401)

        user = await UserManager.get_user_from_session(session_id)
        if not user:
            return JSONResponse({"error": "Invalid session"}, status_code=401)

        connection_id = int(request.path_params.get("id"))
        await connection_manager.delete_connection(connection_id, user["id"])
        return JSONResponse({"success": True})
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Delete connection error: %s", e)
        return JSONResponse({"error": "Failed to delete connection"}, status_code=500)


async def activate_connection_endpoint(request):
    """Set connection as active."""
    from wp_mcp.user_manager import UserManager
    from wp_mcp.connection_manager import connection_manager

    try:
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return JSONResponse({"error": "Session required"}, status_code=401)

        user = await UserManager.get_user_from_session(session_id)
        if not user:
            return JSONResponse({"error": "Invalid session"}, status_code=401)

        connection_id = int(request.path_params.get("id"))
        await connection_manager.set_active_connection(connection_id, user["id"])
        return JSONResponse({"success": True})
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Activate connection error: %s", e)
        return JSONResponse({"error": "Failed to activate connection"}, status_code=500)


# Add custom routes to the FastMCP app
# Get or create the app attribute
if not hasattr(mcp, "_app"):
    # FastMCP might not have _app yet, try to get/create it
    mcp._app = Starlette()
    logger.info("Created Starlette app for FastMCP")

# Add health check routes BEFORE wrapping with middleware
mcp._app.routes.extend(
    [
        Route("/health", health_endpoint),
        Route("/health/ready", health_ready_endpoint),
        Route("/health/live", health_endpoint),
        Route("/health/deep", health_deep_endpoint),
        Route("/metrics", metrics_endpoint),
        # Auth routes
        Route("/register", register_endpoint, methods=["POST"]),
        Route("/login", login_endpoint, methods=["POST"]),
        Route("/logout", logout_endpoint, methods=["POST"]),
        # Connection routes
        Route("/connections", get_connections_endpoint, methods=["GET"]),
        Route("/connections", add_connection_endpoint, methods=["POST"]),
        Route("/connections/{id:int}", update_connection_endpoint, methods=["PUT"]),
        Route("/connections/{id:int}", delete_connection_endpoint, methods=["DELETE"]),
        Route("/connections/{id:int}/activate", activate_connection_endpoint, methods=["POST"]),
    ]
)

# NOW wrap app with authentication middleware AFTER routes are added
mcp._app = AuthMiddleware(mcp._app)
logger.info("Authentication middleware enabled")


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
    transport = config.mcp_transport

    if transport == "streamable-http":
        # For HTTP transport, use uvicorn to serve FastMCP's ASGI app
        import uvicorn

        # Try different attributes to get the ASGI app
        app = getattr(mcp, '_app', None) or getattr(mcp, 'app', None) or mcp

        # Add startup event to the app
        @app.on_event("startup")
        async def on_startup():
            await startup()

        uvicorn.run(
            app,
            host=config.mcp_host,
            port=config.mcp_port,
            log_level="info",
        )
    elif transport == "sse":
        # For SSE transport, use uvicorn as well
        import uvicorn

        # Try different attributes to get the ASGI app
        app = getattr(mcp, '_app', None) or getattr(mcp, 'app', None) or mcp

        # Add startup event to the app
        @app.on_event("startup")
        async def on_startup():
            await startup()

        uvicorn.run(
            app,
            host=config.mcp_host,
            port=config.mcp_port,
            log_level="info",
        )
    else:
        # Default to stdio for local development
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

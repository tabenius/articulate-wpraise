"""WordPress MCP Server entry point.

Exposes WordPress content management tools via the Model Context Protocol.
Supports HTTP/SSE transport for Docker deployment.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.responses import JSONResponse as StarletteJSONResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles

from wp_mcp.config import config
from wp_mcp.exceptions import APIException
from wp_mcp.logging_config import configure_logging
from wp_mcp.middleware.auth import AuthMiddleware
from wp_mcp.middleware.logging import RequestLoggingMiddleware
from wp_mcp.tools import (
    posts, pages, blocks, media, fonts, preview, search, taxonomies,
    revisions, image_tools, settings, menus, templates, seo_tools,
    export_tools, generated
)

# Import route handlers
from wp_mcp.routes.auth import (
    register_endpoint, login_endpoint, logout_endpoint, me_endpoint
)
from wp_mcp.routes.profile import (
    get_profile_endpoint, update_profile_endpoint,
    get_profile_by_username_endpoint, delete_user_account_endpoint
)
from wp_mcp.routes.organizations import (
    create_organization_endpoint, get_organizations_endpoint,
    get_organization_endpoint, update_organization_endpoint,
    delete_organization_endpoint, transfer_organization_ownership_endpoint,
    search_organizations_endpoint, join_organization_endpoint,
    get_organization_members_endpoint, update_member_role_endpoint,
    remove_member_endpoint, get_user_activities_endpoint,
    get_organization_activities_endpoint, get_activity_feed_endpoint,
    create_org_api_key_endpoint, list_org_api_keys_endpoint,
    revoke_org_api_key_endpoint, register_remote_wordpress_endpoint
)
from wp_mcp.routes.invites import (
    create_invite_endpoint, get_organization_invites_endpoint,
    get_user_invites_endpoint, accept_invite_endpoint,
    reject_invite_endpoint, cancel_invite_endpoint
)
from wp_mcp.routes.connections import (
    get_connections_endpoint, add_connection_endpoint,
    update_connection_endpoint, delete_connection_endpoint,
    activate_connection_endpoint, setup_remote_wordpress_endpoint
)
from wp_mcp.routes.monitoring import (
    health_endpoint, health_ready_endpoint, health_deep_endpoint,
    metrics_endpoint, audit_logs_endpoint, audit_summary_endpoint,
    profiling_stats_endpoint
)
from wp_mcp.routes.upload import upload_file_endpoint
from wp_mcp.routes.mcp import mcp_jsonrpc_endpoint
from wp_mcp.routes.ai_preferences import (
    get_ai_preferences_endpoint, update_ai_preferences_endpoint
)
from wp_mcp.routes.seo_generator import generate_seo_endpoint
from wp_mcp.routes.image_alt_text import generate_alt_text_endpoint
from wp_mcp.routes.content_assistant import (
    analyze_content_endpoint, improve_content_endpoint
)

# Configure structured logging
json_format = os.getenv("LOG_FORMAT", "human") == "json"
log_level = os.getenv("LOG_LEVEL", "INFO")
configure_logging(json_format=json_format, log_level=log_level)

logger = logging.getLogger("wp-mcp")

# Initialize MCP server with transport security settings
mcp = FastMCP(
    "Articulate MCP Server",
    instructions=(
        "This server provides tools for managing WordPress content via WPGraphQL. "
        "You can create, read, update, and delete posts and pages. "
        "You can also manipulate individual blocks within posts, including "
        "inserting, removing, moving, and updating blocks. "
        "Block types include: core/paragraph, core/heading, core/image, "
        "core/list, core/quote, core/code, core/columns, core/group, "
        "core/buttons, core/spacer, core/separator, and more."
    ),
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[
            "localhost",
            "127.0.0.1",
            "mcp-server",
            "mcp-server:8000",
            "wp-ai-mcp",
            "wp-ai-mcp:8000",
        ],
        allowed_origins=[
            "http://localhost:3000",
            "http://localhost:4500",
            "http://web:3000",
            "http://wp-ai-web:3000",
        ],
    ),
)

# Register all tool modules
posts.register(mcp)
pages.register(mcp)
blocks.register(mcp)
media.register(mcp)
fonts.register(mcp)
preview.register(mcp)
search.register(mcp)
taxonomies.register(mcp)
revisions.register(mcp)
image_tools.register(mcp)
settings.register(mcp)
menus.register(mcp)
templates.register(mcp)
seo_tools.register(mcp)
export_tools.register(mcp)
generated.register(mcp)

logger.info("Articulate MCP Server initialized")
logger.info("Transport: %s", config.mcp_transport)
logger.info("WordPress URL: %s", config.wp_url)

# Create Starlette app for custom routing
mcp._app = Starlette()  # type: ignore[attr-defined]
logger.info("Created Starlette app for custom JSON-RPC handling")


# Exception handlers for clean error responses
@mcp._app.exception_handler(APIException)  # type: ignore[attr-defined]
async def api_exception_handler(request, exc: APIException):
    """Handle custom API exceptions."""
    response_data: dict[str, Any] = {"error": exc.message}
    if exc.details:
        response_data["details"] = exc.details
    return StarletteJSONResponse(response_data, status_code=exc.status_code)


@mcp._app.exception_handler(ValueError)  # type: ignore[attr-defined]
async def value_error_handler(request, exc: ValueError):
    """Handle ValueError as 400 Bad Request."""
    return StarletteJSONResponse({"error": str(exc)}, status_code=400)


@mcp._app.exception_handler(Exception)  # type: ignore[attr-defined]
async def generic_exception_handler(request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return StarletteJSONResponse(
        {"error": "Internal server error"},
        status_code=500
    )


# Create uploads directory if it doesn't exist
uploads_dir = Path(__file__).parent.parent.parent / "uploads"
uploads_dir.mkdir(exist_ok=True)
(uploads_dir / "avatar").mkdir(exist_ok=True)
(uploads_dir / "banner").mkdir(exist_ok=True)


# MCP JSON-RPC endpoint wrapper (binds mcp instance)
async def mcp_endpoint_wrapper(request):
    """Wrapper to pass mcp instance to mcp_jsonrpc_endpoint."""
    return await mcp_jsonrpc_endpoint(request, mcp)


# Add all routes
mcp._app.routes.extend([  # type: ignore[attr-defined]
    # MCP JSON-RPC
    Route("/mcp", mcp_endpoint_wrapper, methods=["POST"]),

    # Health & Monitoring
    Route("/health", health_endpoint),
    Route("/health/ready", health_ready_endpoint),
    Route("/health/live", health_endpoint),
    Route("/health/deep", health_deep_endpoint),
    Route("/metrics", metrics_endpoint),
    Route("/audit/logs", audit_logs_endpoint, methods=["GET"]),
    Route("/audit/summary", audit_summary_endpoint, methods=["GET"]),
    Route("/profiling/stats", profiling_stats_endpoint, methods=["POST"]),

    # Authentication
    Route("/register", register_endpoint, methods=["POST"]),
    Route("/login", login_endpoint, methods=["POST"]),
    Route("/logout", logout_endpoint, methods=["POST"]),
    Route("/me", me_endpoint, methods=["GET"]),

    # Profile
    Route("/profile", get_profile_endpoint, methods=["GET"]),
    Route("/profile", update_profile_endpoint, methods=["PUT"]),
    Route("/profile", delete_user_account_endpoint, methods=["DELETE"]),
    Route("/profile/{username}", get_profile_by_username_endpoint, methods=["GET"]),

    # Organizations
    Route("/organizations", get_organizations_endpoint, methods=["GET"]),
    Route("/organizations", create_organization_endpoint, methods=["POST"]),
    Route("/organizations/{id:int}", get_organization_endpoint, methods=["GET"]),
    Route("/organizations/{id:int}", update_organization_endpoint, methods=["PUT"]),
    Route("/organizations/{id:int}", delete_organization_endpoint, methods=["DELETE"]),
    Route("/organizations/{id:int}/transfer", transfer_organization_ownership_endpoint, methods=["POST"]),
    Route("/organizations/search", search_organizations_endpoint, methods=["GET"]),
    Route("/organizations/{id:int}/join", join_organization_endpoint, methods=["POST"]),
    Route("/organizations/{id:int}/members", get_organization_members_endpoint, methods=["GET"]),
    Route("/organizations/{id:int}/members/{member_id:int}", update_member_role_endpoint, methods=["PUT"]),
    Route("/organizations/{id:int}/members/{member_id:int}", remove_member_endpoint, methods=["DELETE"]),

    # Organization API Keys
    Route("/organizations/{id:int}/api-keys", create_org_api_key_endpoint, methods=["POST"]),
    Route("/organizations/{id:int}/api-keys", list_org_api_keys_endpoint, methods=["GET"]),
    Route("/organizations/{id:int}/api-keys/{key_id:int}", revoke_org_api_key_endpoint, methods=["DELETE"]),
    Route("/api/register-wordpress", register_remote_wordpress_endpoint, methods=["POST"]),

    # Invites
    Route("/organizations/{id:int}/invites", create_invite_endpoint, methods=["POST"]),
    Route("/organizations/{id:int}/invites", get_organization_invites_endpoint, methods=["GET"]),
    Route("/organizations/{id:int}/invites/{invite_id:int}", cancel_invite_endpoint, methods=["DELETE"]),
    Route("/invites", get_user_invites_endpoint, methods=["GET"]),
    Route("/invites/accept", accept_invite_endpoint, methods=["POST"]),
    Route("/invites/reject", reject_invite_endpoint, methods=["POST"]),

    # Activities
    Route("/activities", get_user_activities_endpoint, methods=["GET"]),
    Route("/activities/feed", get_activity_feed_endpoint, methods=["GET"]),
    Route("/organizations/{id:int}/activities", get_organization_activities_endpoint, methods=["GET"]),

    # Connections
    Route("/connections", get_connections_endpoint, methods=["GET"]),
    Route("/connections", add_connection_endpoint, methods=["POST"]),
    Route("/connections/{id:int}", update_connection_endpoint, methods=["PUT"]),
    Route("/connections/{id:int}", delete_connection_endpoint, methods=["DELETE"]),
    Route("/connections/{id:int}/activate", activate_connection_endpoint, methods=["POST"]),
    Route("/connections/setup-remote", setup_remote_wordpress_endpoint, methods=["POST"]),

    # Upload
    Route("/upload", upload_file_endpoint, methods=["POST"]),

    # AI Preferences
    Route("/ai/preferences", get_ai_preferences_endpoint, methods=["GET"]),
    Route("/ai/preferences", update_ai_preferences_endpoint, methods=["PUT"]),

    # AI SEO Generator
    Route("/ai/generate-seo", generate_seo_endpoint, methods=["POST"]),

    # AI Alt Text Generator
    Route("/ai/generate-alt-text", generate_alt_text_endpoint, methods=["POST"]),

    # AI Content Assistant
    Route("/ai/analyze-content", analyze_content_endpoint, methods=["POST"]),
    Route("/ai/improve-content", improve_content_endpoint, methods=["POST"]),

    # Static files
    Mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads"),
])

# Wrap app with middleware AFTER routes are added
bare_starlette_app = mcp._app  # type: ignore[attr-defined]
mcp._app = AuthMiddleware(mcp._app)  # type: ignore[attr-defined]
logger.info("Authentication middleware enabled")
mcp._app = RequestLoggingMiddleware(mcp._app)  # type: ignore[attr-defined]
logger.info("Request logging middleware enabled")


# Register startup event
@bare_starlette_app.on_event("startup")
async def on_startup():
    """Initialize services on startup."""
    await startup()


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

    if transport in ("streamable-http", "sse"):
        # For HTTP/SSE transport, use uvicorn to serve FastMCP's ASGI app
        import uvicorn

        # Get the wrapped app (middleware wrapping Starlette)
        wrapped_app = getattr(mcp, '_app', None) or getattr(mcp, 'app', None) or mcp

        uvicorn.run(
            wrapped_app,  # type: ignore[arg-type]
            host=config.mcp_host,
            port=config.mcp_port,
            log_level="info",
        )
    else:
        # Default to stdio for local development
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

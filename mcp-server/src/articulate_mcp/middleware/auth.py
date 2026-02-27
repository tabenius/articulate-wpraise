"""Authentication middleware for MCP server."""

from __future__ import annotations

import logging
import os
from typing import Awaitable, Callable

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from articulate_mcp.audit import AuditLog
from articulate_mcp.connection_manager import connection_manager
from articulate_mcp.middleware.rate_limit import (
    RateLimitExceeded,
    tool_rate_limiter,
    ai_chat_rate_limiter,
)
from articulate_mcp.user_manager import UserManager

logger = logging.getLogger(__name__)

# Check if testing mode is enabled (disable rate limiting for tests)
TESTING_MODE = os.getenv("TESTING_MODE", "false").lower() == "true"


class AuthMiddleware:
    """Middleware to enforce authentication on MCP endpoints."""

    def __init__(self, app):
        self.app = app

    async def __call__(
        self, scope: dict, receive: Callable, send: Callable
    ) -> None:
        """Process request and enforce authentication.
        
        Args:
            scope: ASGI scope
            receive: ASGI receive callable
            send: ASGI send callable
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        path = request.url.path
        method = scope.get("method", "GET")

        # Public endpoints (no authentication required)
        public_paths = [
            "/health",
            "/metrics",
            "/register",
            "/login",
            "/me",
            "/auth/verify-email",
            "/auth/resend-verification",
            "/auth/forgot-password",
            "/auth/reset-password",
            "/auth/validate-wp-login-token",
            "/organizations/search",  # Public organization search
            "/api/register-wordpress",  # Public WordPress registration with API key
        ]

        # Public GET endpoints (read-only access)
        public_get_paths = [
            "/profile/",  # GET /profile/{username}
            "/organizations/",  # GET /organizations/{id}
        ]

        # Check if path is public
        is_public = (
            any(path.startswith(p) for p in public_paths) or
            (method == "GET" and any(path.startswith(p) for p in public_get_paths))
        )

        if is_public:
            # Still apply rate limiting to auth endpoints (unless in testing mode)
            if path in ["/register", "/login"] and not TESTING_MODE:
                try:
                    # Use IP address as identifier for unauthenticated endpoints
                    client = scope.get("client")
                    client_ip = client[0] if client else "unknown"
                    await ai_chat_rate_limiter.check_rate_limit(f"auth:{client_ip}")
                except RateLimitExceeded as e:
                    # Log rate limit violation
                    await AuditLog.log_rate_limit_event(
                        user_id=None,
                        endpoint=path,
                        ip_address=client_ip,
                        limit=e.limit if hasattr(e, "limit") else None,
                        retry_after=e.retry_after,
                    )

                    response = JSONResponse(
                        {
                            "error": f"Rate limit exceeded. Try again in {e.retry_after} seconds.",
                            "retry_after": e.retry_after,
                        },
                        status_code=429,
                        headers={"Retry-After": str(e.retry_after)},
                    )
                    await response(scope, receive, send)
                    return
            await self.app(scope, receive, send)
            return

        # Require authentication for all other endpoints
        session_id = request.headers.get("X-Session-ID")
        client = scope.get("client")
        client_ip = client[0] if client else None

        if not session_id:
            # Log unauthenticated access attempt
            await AuditLog.log_access_denied(
                user_id=None,
                resource_type="endpoint",
                resource_id=path,
                reason="No session ID provided",
                ip_address=client_ip,
            )

            response = JSONResponse(
                {"error": "Authentication required. Provide X-Session-ID header."},
                status_code=401,
            )
            await response(scope, receive, send)
            return

        # Validate session
        user = await UserManager.get_user_from_session(session_id)
        if not user:
            # Log invalid session attempt
            await AuditLog.log_access_denied(
                user_id=None,
                resource_type="endpoint",
                resource_id=path,
                reason="Invalid or expired session",
                ip_address=client_ip,
            )

            response = JSONResponse(
                {"error": "Invalid or expired session"}, status_code=401
            )
            await response(scope, receive, send)
            return

        # Apply rate limiting based on user ID (unless in testing mode)
        if not TESTING_MODE:
            user_identifier = f"user:{user['id']}"

            try:
                if path.startswith("/mcp"):
                    # Rate limit MCP tool calls (100 per minute)
                    await tool_rate_limiter.check_rate_limit(user_identifier)
                else:
                    # Rate limit connection management endpoints (10 per minute)
                    await ai_chat_rate_limiter.check_rate_limit(user_identifier)
            except RateLimitExceeded as e:
                # Log rate limit violation for authenticated user
                await AuditLog.log_rate_limit_event(
                    user_id=user["id"],
                    endpoint=path,
                    ip_address=client_ip,
                    limit=e.limit if hasattr(e, "limit") else None,
                    retry_after=e.retry_after,
                )

                response = JSONResponse(
                    {
                        "error": f"Rate limit exceeded. Try again in {e.retry_after} seconds.",
                        "retry_after": e.retry_after,
                    },
                    status_code=429,
                    headers={"Retry-After": str(e.retry_after)},
                )
                await response(scope, receive, send)
                return

        # For MCP tool endpoints, validate active WordPress connection
        if path.startswith("/mcp"):
            active_conn = await connection_manager.get_active_connection(user["id"])
            if not active_conn:
                # Log access denied - no active connection
                await AuditLog.log_access_denied(
                    user_id=user["id"],
                    resource_type="mcp_endpoint",
                    resource_id=path,
                    reason="No active WordPress connection",
                    ip_address=client_ip,
                )

                response = JSONResponse(
                    {
                        "error": "No active WordPress connection. Please add and activate a connection."
                    },
                    status_code=403,
                )
                await response(scope, receive, send)
                return

            # Add user and connection to request state for use by tools
            scope["state"] = {
                "user": user,
                "connection": active_conn,
            }
            logger.info(
                "Authenticated request: user=%s, connection=%s",
                user["email"],
                active_conn["name"],
            )

            # Fetch and cache WordPress roles for capability checking
            try:
                from articulate_mcp.graphql.client import get_graphql_client
                from articulate_mcp.graphql.queries import GET_VIEWER_CAPABILITIES
                gql_client = await get_graphql_client(active_conn["id"], user["id"])
                viewer_result = await gql_client.query(
                    GET_VIEWER_CAPABILITIES,
                    use_cache=True,
                    user_id=user["id"],
                )
                viewer = viewer_result.get("viewer")
                if viewer:
                    wp_roles = [n["name"] for n in viewer.get("roles", {}).get("nodes", [])]
                    scope["state"]["wp_roles"] = wp_roles
                else:
                    scope["state"]["wp_roles"] = []
            except Exception as e:
                logger.warning("Could not fetch WP roles for MCP endpoint: %s", e)
                scope["state"]["wp_roles"] = []

        # Add user to scope for non-MCP authenticated endpoints
        if "state" not in scope:
            scope["state"] = {"user": user}

            # Try to fetch WP roles for non-MCP endpoints
            try:
                from articulate_mcp.connection_manager import connection_manager as conn_mgr
                from articulate_mcp.graphql.client import get_graphql_client
                from articulate_mcp.graphql.queries import GET_VIEWER_CAPABILITIES
                active_conn = await conn_mgr.get_active_connection(user["id"])
                if active_conn:
                    gql_client = await get_graphql_client(active_conn["id"], user["id"])
                    viewer_result = await gql_client.query(
                        GET_VIEWER_CAPABILITIES,
                        use_cache=True,
                        user_id=user["id"],
                    )
                    viewer = viewer_result.get("viewer")
                    if viewer:
                        wp_roles = [n["name"] for n in viewer.get("roles", {}).get("nodes", [])]
                        scope["state"]["wp_roles"] = wp_roles
                    else:
                        scope["state"]["wp_roles"] = []
                else:
                    scope["state"]["wp_roles"] = []
            except Exception:
                scope["state"]["wp_roles"] = []

        await self.app(scope, receive, send)

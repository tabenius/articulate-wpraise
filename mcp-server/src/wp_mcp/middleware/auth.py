"""Authentication middleware for MCP server."""

from __future__ import annotations

import logging
from typing import Awaitable, Callable

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from wp_mcp.connection_manager import connection_manager
from wp_mcp.middleware.rate_limit import (
    RateLimitExceeded,
    tool_rate_limiter,
    ai_chat_rate_limiter,
)
from wp_mcp.user_manager import UserManager

logger = logging.getLogger(__name__)


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

        # Skip authentication for health, metrics, and public auth endpoints
        if path.startswith(("/health", "/metrics", "/register", "/login")) or path == "/me":
            # Still apply rate limiting to auth endpoints
            if path in ["/register", "/login"]:
                try:
                    # Use IP address as identifier for unauthenticated endpoints
                    client = scope.get("client")
                    client_ip = client[0] if client else "unknown"
                    await ai_chat_rate_limiter.check_rate_limit(f"auth:{client_ip}")
                except RateLimitExceeded as e:
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
        if not session_id:
            response = JSONResponse(
                {"error": "Authentication required. Provide X-Session-ID header."},
                status_code=401,
            )
            await response(scope, receive, send)
            return

        # Validate session
        user = await UserManager.get_user_from_session(session_id)
        if not user:
            response = JSONResponse(
                {"error": "Invalid or expired session"}, status_code=401
            )
            await response(scope, receive, send)
            return

        # Apply rate limiting based on user ID
        user_identifier = f"user:{user['id']}"

        try:
            if path.startswith("/mcp"):
                # Rate limit MCP tool calls (100 per minute)
                await tool_rate_limiter.check_rate_limit(user_identifier)
            else:
                # Rate limit connection management endpoints (10 per minute)
                await ai_chat_rate_limiter.check_rate_limit(user_identifier)
        except RateLimitExceeded as e:
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

        # Add user to scope for non-MCP authenticated endpoints
        if "state" not in scope:
            scope["state"] = {"user": user}

        await self.app(scope, receive, send)

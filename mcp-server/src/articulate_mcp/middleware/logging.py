"""Request/response logging middleware with correlation IDs."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Callable, cast

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("articulate-mcp.requests")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests and responses.

    Logs:
    - Correlation ID (auto-generated or from X-Correlation-ID header)
    - Request method, path, and query parameters
    - Request headers (sanitized)
    - Response status code
    - Response time in milliseconds
    - User ID if authenticated
    """

    SENSITIVE_HEADERS = {
        "authorization",
        "x-session-id",
        "cookie",
        "x-api-key",
        "x-auth-token",
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details."""
        # Generate or reuse correlation ID
        correlation_id = (
            request.headers.get("X-Correlation-ID")
            or request.headers.get("X-Request-ID")
            or uuid.uuid4().hex[:12]
        )
        # Store on request state so handlers can access it
        request.state.correlation_id = correlation_id

        # Record start time
        start_time = time.time()

        # Extract request info
        method = request.method
        path = request.url.path
        query_params = dict(request.query_params) if request.query_params else None

        # Get user info if available (set by auth middleware)
        user_id = None
        if hasattr(request.state, "user") and request.state.user:
            user_id = request.state.user.get("id")

        # Log request
        logger.info(
            "Request started",
            extra={
                "request_id": correlation_id,
                "method": method,
                "path": path,
                "query_params": query_params,
                "user_id": user_id,
                "client_ip": request.client.host if request.client else None,
            }
        )

        # Process request
        try:
            response = cast(Response, await call_next(request))
        except Exception as e:
            # Log exception and re-raise
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "Request failed with exception",
                extra={
                    "request_id": correlation_id,
                    "method": method,
                    "path": path,
                    "error": str(e),
                    "duration_ms": round(duration_ms, 2),
                },
                exc_info=True
            )
            raise

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log response
        log_level = logging.INFO if response.status_code < 400 else logging.WARNING
        logger.log(
            log_level,
            "Request completed",
            extra={
                "request_id": correlation_id,
                "method": method,
                "path": path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "user_id": user_id,
            }
        )

        # Add correlation and timing headers to response
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

        return response

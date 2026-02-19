"""Request/response logging middleware."""

from __future__ import annotations

import logging
import time
from typing import Callable, cast

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("wp-mcp.requests")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests and responses.

    Logs:
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
        # Record start time
        start_time = time.time()

        # Extract request info
        method = request.method
        path = request.url.path
        query_params = dict(request.query_params) if request.query_params else None

        # Sanitize headers (remove sensitive data)
        headers = {
            k.lower(): v if k.lower() not in self.SENSITIVE_HEADERS else "[REDACTED]"
            for k, v in request.headers.items()
        }

        # Get user info if available (set by auth middleware)
        user_id = None
        if hasattr(request.state, "user") and request.state.user:
            user_id = request.state.user.get("id")

        # Log request
        logger.info(
            f"Request started",
            extra={
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
                f"Request failed with exception",
                extra={
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
            f"Request completed",
            extra={
                "method": method,
                "path": path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "user_id": user_id,
            }
        )

        # Add custom header with response time
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

        return response

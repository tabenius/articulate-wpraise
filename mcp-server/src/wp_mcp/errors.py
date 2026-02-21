"""Standardized error handling and formatting."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


class StandardError:
    """Standard error response format for consistent API errors."""

    @staticmethod
    def format_error(
        message: str,
        error_code: str,
        details: Optional[dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Format an error response with standard structure.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code (e.g., "VALIDATION_ERROR")
            details: Optional additional error details
            request_id: Optional request ID for tracing

        Returns:
            Standardized error dict
        """
        error_id = request_id or str(uuid.uuid4())

        error_response = {
            "error": True,
            "error_id": error_id,
            "error_code": error_code,
            "message": message,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        if details:
            error_response["details"] = details

        # Log error for monitoring
        logger.error(
            f"Error {error_code}: {message}",
            extra={"error_id": error_id, "details": details},
        )

        return error_response

    @staticmethod
    def validation_error(
        message: str,
        field: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Format a validation error.

        Args:
            message: Validation error message
            field: Optional field name that failed validation
            request_id: Optional request ID

        Returns:
            Standardized validation error
        """
        details = {"field": field} if field else None
        return StandardError.format_error(
            message=message,
            error_code="VALIDATION_ERROR",
            details=details,
            request_id=request_id,
        )

    @staticmethod
    def authentication_error(
        message: str = "Authentication required",
        request_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Format an authentication error.

        Args:
            message: Authentication error message
            request_id: Optional request ID

        Returns:
            Standardized authentication error
        """
        return StandardError.format_error(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            request_id=request_id,
        )

    @staticmethod
    def authorization_error(
        message: str = "Insufficient permissions",
        required_permission: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Format an authorization error.

        Args:
            message: Authorization error message
            required_permission: Optional required permission
            request_id: Optional request ID

        Returns:
            Standardized authorization error
        """
        details = {"required_permission": required_permission} if required_permission else None
        return StandardError.format_error(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            details=details,
            request_id=request_id,
        )

    @staticmethod
    def not_found_error(
        resource: str,
        resource_id: Optional[Any] = None,
        request_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Format a not found error.

        Args:
            resource: Type of resource not found
            resource_id: Optional ID of the resource
            request_id: Optional request ID

        Returns:
            Standardized not found error
        """
        message = f"{resource} not found"
        if resource_id:
            message += f": {resource_id}"

        details = {"resource": resource, "resource_id": resource_id}
        return StandardError.format_error(
            message=message,
            error_code="NOT_FOUND",
            details=details,
            request_id=request_id,
        )

    @staticmethod
    def rate_limit_error(
        limit: int,
        retry_after: int,
        request_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Format a rate limit error.

        Args:
            limit: Rate limit threshold
            retry_after: Seconds to wait before retrying
            request_id: Optional request ID

        Returns:
            Standardized rate limit error
        """
        return StandardError.format_error(
            message=f"Rate limit exceeded. Retry after {retry_after} seconds.",
            error_code="RATE_LIMIT_EXCEEDED",
            details={"limit": limit, "retry_after": retry_after},
            request_id=request_id,
        )

    @staticmethod
    def internal_error(
        message: str = "Internal server error",
        exception: Optional[Exception] = None,
        request_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Format an internal server error.

        Args:
            message: Error message
            exception: Optional exception that caused the error
            request_id: Optional request ID

        Returns:
            Standardized internal error
        """
        details = None
        if exception:
            details = {
                "exception_type": type(exception).__name__,
                "exception_message": str(exception),
            }

        return StandardError.format_error(
            message=message,
            error_code="INTERNAL_ERROR",
            details=details,
            request_id=request_id,
        )

    @staticmethod
    def database_error(
        message: str = "Database operation failed",
        operation: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Format a database error.

        Args:
            message: Error message
            operation: Optional database operation that failed
            request_id: Optional request ID

        Returns:
            Standardized database error
        """
        details = {"operation": operation} if operation else None
        return StandardError.format_error(
            message=message,
            error_code="DATABASE_ERROR",
            details=details,
            request_id=request_id,
        )

    @staticmethod
    def external_service_error(
        service: str,
        message: str = "External service unavailable",
        request_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Format an external service error.

        Args:
            service: Name of the external service
            message: Error message
            request_id: Optional request ID

        Returns:
            Standardized external service error
        """
        return StandardError.format_error(
            message=message,
            error_code="EXTERNAL_SERVICE_ERROR",
            details={"service": service},
            request_id=request_id,
        )

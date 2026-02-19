"""Custom exceptions for API error handling."""

from __future__ import annotations


class APIException(Exception):
    """Base exception for API errors.

    All API exceptions should inherit from this class.
    Automatically converted to JSON error responses by exception handler.
    """

    def __init__(self, message: str, status_code: int = 400, details: dict = None):
        """Initialize API exception.

        Args:
            message: Error message
            status_code: HTTP status code (default: 400)
            details: Optional additional error details
        """
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class AuthenticationError(APIException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, status_code=401)


class PermissionError(APIException):
    """Raised when user lacks permission for an action."""

    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, status_code=403)


class NotFoundError(APIException):
    """Raised when a resource is not found."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class ValidationError(APIException):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: str = None):
        details = {"field": field} if field else {}
        super().__init__(message, status_code=400, details=details)


class ConflictError(APIException):
    """Raised when an operation conflicts with existing state."""

    def __init__(self, message: str):
        super().__init__(message, status_code=409)


class RateLimitError(APIException):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, status_code=429)


class InternalServerError(APIException):
    """Raised for unexpected server errors."""

    def __init__(self, message: str = "Internal server error"):
        super().__init__(message, status_code=500)

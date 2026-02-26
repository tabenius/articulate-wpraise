"""Endpoint decorators for authentication and authorization."""

from __future__ import annotations

from functools import wraps
from typing import Callable, Optional

from starlette.responses import JSONResponse


def require_auth(f: Callable) -> Callable:
    """Decorator to require authentication for endpoints.

    Checks for valid session and injects authenticated user into request.state.user

    Usage:
        @require_auth
        async def my_endpoint(request):
            user = request.state.user  # Already authenticated!
            # ... endpoint logic

    Returns:
        401 error if session is missing or invalid
    """
    @wraps(f)
    async def wrapper(request):
        from articulate_mcp.user_manager import UserManager

        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return JSONResponse({"error": "Session required"}, status_code=401)

        user = await UserManager.get_user_from_session(session_id)
        if not user:
            return JSONResponse({"error": "Invalid session"}, status_code=401)

        # Inject user into request state
        request.state.user = user
        return await f(request)

    return wrapper


def optional_auth(f: Callable) -> Callable:
    """Decorator for endpoints that work with or without authentication.

    If session is present and valid, injects user into request.state.user
    If session is missing or invalid, sets request.state.user = None

    Usage:
        @optional_auth
        async def my_endpoint(request):
            user = request.state.user  # May be None
            if user:
                # Show personalized content
            else:
                # Show public content
    """
    @wraps(f)
    async def wrapper(request):
        from articulate_mcp.user_manager import UserManager

        session_id = request.headers.get("X-Session-ID") or request.headers.get("x-session-id")
        if not session_id:
            request.state.user = None
            return await f(request)

        user = await UserManager.get_user_from_session(session_id)
        request.state.user = user
        return await f(request)

    return wrapper


def require_org_member(role: Optional[str] = None) -> Callable:
    """Decorator to require organization membership and optionally a specific role.

    Must be used with @require_auth.
    Expects organization_id in path_params.

    Args:
        role: Required role (owner, admin, member, viewer). If None, any member is allowed.

    Usage:
        @require_auth
        @require_org_member(role="owner")
        async def transfer_ownership(request):
            user = request.state.user
            org_id = request.path_params["organization_id"]
            # User is guaranteed to be owner of this org

    Returns:
        403 error if user is not a member or doesn't have required role
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        async def wrapper(request):
            from articulate_mcp.database import db

            user = request.state.user
            org_id = request.path_params.get("organization_id") or request.path_params.get("id")

            if not org_id:
                return JSONResponse({"error": "Organization ID required"}, status_code=400)

            # Check membership and role
            member = await db.fetchone(
                """
                SELECT role FROM wp_organization_members
                WHERE organization_id = %s AND user_id = %s
                """,
                (org_id, user["id"]),
            )

            if not member:
                return JSONResponse(
                    {"error": "Not a member of this organization"},
                    status_code=403
                )

            # Check role if specified
            if role:
                role_hierarchy = {"viewer": 1, "member": 2, "admin": 3, "owner": 4}
                user_role_level = role_hierarchy.get(member["role"], 0)
                required_role_level = role_hierarchy.get(role, 99)

                if user_role_level < required_role_level:
                    return JSONResponse(
                        {"error": f"Requires {role} role or higher"},
                        status_code=403
                    )

            # Inject membership info
            request.state.org_member = member
            return await f(request)

        return wrapper
    return decorator

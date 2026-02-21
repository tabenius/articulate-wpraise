"""User profile management endpoints."""

from __future__ import annotations

import logging
from starlette.responses import JSONResponse

from wp_mcp.decorators import require_auth
from wp_mcp.json_utils import sanitize_for_json

logger = logging.getLogger(__name__)


@require_auth
async def get_profile_endpoint(request):
    """Get user profile."""
    from wp_mcp.profile_manager import ProfileManager

    user = request.state.user  # Injected by @require_auth
    profile = await ProfileManager.get_profile(user["id"])
    return JSONResponse(sanitize_for_json(profile))


@require_auth
async def update_profile_endpoint(request):
    """Update user profile."""
    from wp_mcp.profile_manager import ProfileManager

    user = request.state.user  # Injected by @require_auth
    data = await request.json()
    # ValueError is automatically caught by exception handler
    profile = await ProfileManager.update_profile(
        user_id=user["id"],
        username=data.get("username"),
        name=data.get("name"),
        avatar=data.get("avatar"),
        banner=data.get("banner"),
        bio=data.get("bio"),
        visibility=data.get("visibility"),
    )
    return JSONResponse(sanitize_for_json(profile))


async def get_profile_by_username_endpoint(request):
    """Get user profile by username (respects visibility settings)."""
    from wp_mcp.profile_manager import ProfileManager

    try:
        username = request.path_params.get("username")

        # Get requesting user ID from session if available
        session_id = request.headers.get("x-session-id")
        requesting_user_id = None
        if session_id:
            from wp_mcp.user_manager import UserManager
            user = await UserManager.get_user_from_session(session_id)
            if user:
                requesting_user_id = user["id"]

        profile = await ProfileManager.get_profile_by_username(username, requesting_user_id)
        if not profile:
            return JSONResponse({"error": "User not found or profile is private"}, status_code=404)
        return JSONResponse(sanitize_for_json(profile))
    except Exception as e:
        logger.error("Get profile by username error: %s", e)
        return JSONResponse({"error": "Failed to get profile"}, status_code=500)


async def delete_user_account_endpoint(request):
    """Delete user's own account (requires password confirmation)."""
    from wp_mcp.user_manager import UserManager

    try:
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return JSONResponse({"error": "Session required"}, status_code=401)

        user = await UserManager.get_user_from_session(session_id)
        if not user:
            return JSONResponse({"error": "Invalid session"}, status_code=401)

        data = await request.json()
        password = data.get("password")

        if not password:
            return JSONResponse(
                {"error": "Password confirmation required"},
                status_code=400
            )

        # Delete user account
        await UserManager.delete_user(user["id"], password)

        logger.info(f"User account deleted: {user['email']} (ID: {user['id']})")

        return JSONResponse({
            "success": True,
            "message": "Account deleted successfully"
        })

    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except RuntimeError as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    except Exception as e:
        logger.error("Delete user account error: %s", e)
        return JSONResponse(
            {"error": "Failed to delete account"},
            status_code=500
        )

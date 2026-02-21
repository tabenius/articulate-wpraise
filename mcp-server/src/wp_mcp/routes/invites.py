"""Organization invite endpoints."""

from __future__ import annotations

import logging
from starlette.responses import JSONResponse

from wp_mcp.decorators import require_auth
from wp_mcp.json_utils import sanitize_for_json

logger = logging.getLogger(__name__)


@require_auth
async def create_invite_endpoint(request):
    """Create organization invite."""
    from wp_mcp.invite_manager import InviteManager

    try:
        user = request.state.user

        org_id = int(request.path_params.get("id"))
        data = await request.json()

        invite = await InviteManager.create_invite(
            org_id=org_id,
            inviter_id=user["id"],
            invitee_email=data.get("email"),
            role=data.get("role", "member"),
        )
        return JSONResponse(sanitize_for_json(invite), status_code=201)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Create invite error: %s", e)
        return JSONResponse({"error": "Failed to create invite"}, status_code=500)


@require_auth
async def get_organization_invites_endpoint(request):
    """Get organization invites."""
    from wp_mcp.invite_manager import InviteManager

    try:
        user = request.state.user

        org_id = int(request.path_params.get("id"))
        invites = await InviteManager.get_invites_for_organization(org_id, user["id"])
        return JSONResponse(sanitize_for_json(invites))
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Get invites error: %s", e)
        return JSONResponse({"error": "Failed to get invites"}, status_code=500)


@require_auth
async def get_user_invites_endpoint(request):
    """Get current user's pending invites."""
    from wp_mcp.invite_manager import InviteManager

    try:
        user = request.state.user

        invites = await InviteManager.get_invites_for_user(user["email"])
        return JSONResponse(sanitize_for_json(invites))
    except Exception as e:
        logger.error("Get user invites error: %s", e)
        return JSONResponse({"error": "Failed to get invites"}, status_code=500)


@require_auth
async def accept_invite_endpoint(request):
    """Accept organization invite."""
    from wp_mcp.invite_manager import InviteManager

    try:
        user = request.state.user

        data = await request.json()
        token = data.get("token")

        org = await InviteManager.accept_invite(token, user["id"])
        return JSONResponse(sanitize_for_json(org))
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Accept invite error: %s", e)
        return JSONResponse({"error": "Failed to accept invite"}, status_code=500)


@require_auth
async def reject_invite_endpoint(request):
    """Reject organization invite."""
    from wp_mcp.invite_manager import InviteManager

    try:
        user = request.state.user

        data = await request.json()
        token = data.get("token")

        await InviteManager.reject_invite(token, user["id"])
        return JSONResponse({"success": True})
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Reject invite error: %s", e)
        return JSONResponse({"error": "Failed to reject invite"}, status_code=500)


@require_auth
async def cancel_invite_endpoint(request):
    """Cancel organization invite."""
    from wp_mcp.invite_manager import InviteManager

    try:
        user = request.state.user

        invite_id = int(request.path_params.get("invite_id"))
        await InviteManager.cancel_invite(invite_id, user["id"])
        return JSONResponse({"success": True})
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Cancel invite error: %s", e)
        return JSONResponse({"error": "Failed to cancel invite"}, status_code=500)

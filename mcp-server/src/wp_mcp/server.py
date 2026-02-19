"""WordPress MCP Server entry point.

Exposes WordPress content management tools via the Model Context Protocol.
Supports HTTP/SSE transport for Docker deployment.
"""

from __future__ import annotations

import logging
import os

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import JSONResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles

from wp_mcp.config import config
from wp_mcp.decorators import require_auth, optional_auth
from wp_mcp.json_utils import sanitize_for_json
from wp_mcp.logging_config import configure_logging
from wp_mcp.middleware.auth import AuthMiddleware
from wp_mcp.tools import posts, pages, blocks, media, search, taxonomies, revisions, image_tools

# Configure structured logging
json_format = os.getenv("LOG_FORMAT", "human") == "json"
log_level = os.getenv("LOG_LEVEL", "INFO")
configure_logging(json_format=json_format, log_level=log_level)

logger = logging.getLogger("wp-mcp")

# Initialize MCP server with transport security settings
# Allow Docker service names and localhost for internal communication
mcp = FastMCP(
    "WordPress MCP Server",
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
search.register(mcp)
taxonomies.register(mcp)
revisions.register(mcp)
image_tools.register(mcp)

logger.info("WordPress MCP Server initialized")
logger.info("Transport: %s", config.mcp_transport)
logger.info("WordPress URL: %s", config.wp_url)


# Health check endpoints
async def health_endpoint(request):
    """Basic health check endpoint."""
    from wp_mcp.health import get_liveness_status

    status = await get_liveness_status()
    return JSONResponse(status)


async def health_ready_endpoint(request):
    """Readiness check endpoint (can accept traffic)."""
    from wp_mcp.health import get_readiness_status

    status = await get_readiness_status()
    status_code = 200 if status.get("ready") else 503
    return JSONResponse(status, status_code=status_code)


async def health_deep_endpoint(request):
    """Deep health check endpoint (all dependencies)."""
    from wp_mcp.health import get_health_status

    status = await get_health_status()
    status_code = 200 if status.get("status") == "healthy" else 503
    return JSONResponse(status, status_code=status_code)


async def metrics_endpoint(request):
    """Metrics endpoint."""
    from wp_mcp.logging_config import metrics

    stats = metrics.get_stats()
    return JSONResponse(stats)


async def audit_logs_endpoint(request):
    """Audit logs query endpoint (requires authentication)."""
    from wp_mcp.audit import AuditLog

    # User will be in request.state if authenticated
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    # Parse query parameters
    limit = int(request.query_params.get("limit", "100"))
    event_type = request.query_params.get("event_type")

    # Get logs
    logs = await AuditLog.get_recent_events(
        limit=min(limit, 1000),  # Cap at 1000
        user_id=user.get("id") if not user.get("is_admin") else None,  # Regular users see only their own logs
        event_type=event_type,
    )

    return JSONResponse({"logs": logs})


async def audit_summary_endpoint(request):
    """Security event summary endpoint (requires authentication)."""
    from wp_mcp.audit import AuditLog

    # User will be in request.state if authenticated
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    hours = int(request.query_params.get("hours", "24"))

    # Get security summary
    summary = await AuditLog.get_security_summary(hours=hours)

    return JSONResponse(summary)


# Authentication endpoints
async def register_endpoint(request):
    """User registration endpoint."""
    from wp_mcp.audit import AuditLog
    from wp_mcp.user_manager import UserManager

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    try:
        data = await request.json()
        email = data.get("email")
        password = data.get("password")
        name = data.get("name", "")

        user = await UserManager.register_user(email, password, name)

        # Log successful registration
        await AuditLog.log_auth_event(
            event_type="register",
            status="success",
            user_id=user["id"],
            email=email,
            ip_address=client_ip,
            user_agent=user_agent,
            message=f"New user registered: {email}",
        )

        return JSONResponse(user, status_code=201)
    except ValueError as e:
        # Log failed registration (validation error)
        await AuditLog.log_auth_event(
            event_type="register",
            status="failure",
            email=data.get("email") if 'data' in locals() else None,
            ip_address=client_ip,
            user_agent=user_agent,
            message=f"Registration failed: {str(e)}",
        )
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Registration error: %s", e)
        await AuditLog.log_auth_event(
            event_type="register",
            status="error",
            ip_address=client_ip,
            user_agent=user_agent,
            message=f"Registration error: {str(e)}",
        )
        return JSONResponse({"error": "Registration failed"}, status_code=500)


async def login_endpoint(request):
    """User login endpoint."""
    from wp_mcp.audit import AuditLog
    from wp_mcp.user_manager import UserManager

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    try:
        data = await request.json()
        email = data.get("email")
        password = data.get("password")

        result = await UserManager.authenticate(email, password)
        if result:
            # Log successful login
            await AuditLog.log_auth_event(
                event_type="login",
                status="success",
                user_id=result["user"]["id"],
                email=email,
                ip_address=client_ip,
                user_agent=user_agent,
                message=f"User logged in: {email}",
            )
            return JSONResponse(result)
        else:
            # Log failed login
            await AuditLog.log_auth_event(
                event_type="login",
                status="failure",
                email=email,
                ip_address=client_ip,
                user_agent=user_agent,
                message=f"Login failed for {email}: Invalid credentials",
            )
            return JSONResponse({"error": "Invalid credentials"}, status_code=401)
    except Exception as e:
        logger.error("Login error: %s", e)
        await AuditLog.log_auth_event(
            event_type="login",
            status="error",
            ip_address=client_ip,
            user_agent=user_agent,
            message=f"Login error: {str(e)}",
        )
        return JSONResponse({"error": "Login failed"}, status_code=500)


async def logout_endpoint(request):
    """User logout endpoint."""
    from wp_mcp.audit import AuditLog
    from wp_mcp.user_manager import UserManager

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    try:
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return JSONResponse({"error": "Session ID required"}, status_code=400)

        # Get user info before logout
        user = await UserManager.get_user_from_session(session_id)

        success = await UserManager.logout(session_id)
        if success:
            # Log successful logout
            if user:
                await AuditLog.log_auth_event(
                    event_type="logout",
                    status="success",
                    user_id=user["id"],
                    email=user["email"],
                    ip_address=client_ip,
                    user_agent=user_agent,
                    message=f"User logged out: {user['email']}",
                )
            return JSONResponse({"success": True})
        else:
            return JSONResponse({"error": "Invalid session"}, status_code=404)
    except Exception as e:
        logger.error("Logout error: %s", e)
        return JSONResponse({"error": "Logout failed"}, status_code=500)


async def me_endpoint(request):
    """Get current user info from session."""
    from wp_mcp.user_manager import UserManager

    try:
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return JSONResponse({"error": "Session ID required"}, status_code=401)

        user = await UserManager.get_user_from_session(session_id)
        if user:
            return JSONResponse(user)
        else:
            return JSONResponse({"error": "Invalid or expired session"}, status_code=401)
    except Exception as e:
        logger.error("Get user error: %s", e)
        return JSONResponse({"error": "Failed to get user"}, status_code=500)


# Profile management endpoints
@require_auth
async def get_profile_endpoint(request):
    """Get user profile."""
    from wp_mcp.profile_manager import ProfileManager

    try:
        user = request.state.user  # Injected by @require_auth
        profile = await ProfileManager.get_profile(user["id"])
        return JSONResponse(sanitize_for_json(profile))
    except Exception as e:
        logger.error("Get profile error: %s", e)
        return JSONResponse({"error": "Failed to get profile"}, status_code=500)


@require_auth
async def update_profile_endpoint(request):
    """Update user profile."""
    from wp_mcp.profile_manager import ProfileManager

    try:
        user = request.state.user  # Injected by @require_auth
        data = await request.json()
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
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Update profile error: %s", e)
        return JSONResponse({"error": "Failed to update profile"}, status_code=500)


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


# Organization management endpoints
@require_auth
async def create_organization_endpoint(request):
    """Create a new organization."""
    from wp_mcp.organization_manager import OrganizationManager

    try:
        user = request.state.user
        data = await request.json()
        org = await OrganizationManager.create_organization(
            owner_id=user["id"],
            name=data.get("name"),
            slug=data.get("slug"),
            avatar=data.get("avatar"),
            banner=data.get("banner"),
            bio=data.get("bio"),
        )
        return JSONResponse(sanitize_for_json(org), status_code=201)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Create organization error: %s", e)
        return JSONResponse({"error": "Failed to create organization"}, status_code=500)


@require_auth
async def get_organizations_endpoint(request):
    """Get user's organizations."""
    from wp_mcp.organization_manager import OrganizationManager

    try:
        user = request.state.user
        orgs = await OrganizationManager.get_organizations_for_user(user["id"])
        return JSONResponse(sanitize_for_json(orgs))
    except Exception as e:
        logger.error("Get organizations error: %s", e)
        return JSONResponse({"error": "Failed to get organizations"}, status_code=500)


async def get_organization_endpoint(request):
    """Get organization details."""
    from wp_mcp.organization_manager import OrganizationManager

    try:
        org_id = int(request.path_params.get("id"))
        org = await OrganizationManager.get_organization(org_id)
        if not org:
            return JSONResponse({"error": "Organization not found"}, status_code=404)
        return JSONResponse(sanitize_for_json(org))
    except Exception as e:
        logger.error("Get organization error: %s", e)
        return JSONResponse({"error": "Failed to get organization"}, status_code=500)


@require_auth
async def update_organization_endpoint(request):
    """Update organization."""
    from wp_mcp.organization_manager import OrganizationManager

    try:
        user = request.state.user
        org_id = int(request.path_params.get("id"))
        data = await request.json()

        org = await OrganizationManager.update_organization(
            org_id=org_id,
            user_id=user["id"],
            name=data.get("name"),
            avatar=data.get("avatar"),
            banner=data.get("banner"),
            bio=data.get("bio"),
        )
        return JSONResponse(sanitize_for_json(org))
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Update organization error: %s", e)
        return JSONResponse({"error": "Failed to update organization"}, status_code=500)


@require_auth
async def delete_organization_endpoint(request):
    """Delete organization."""
    from wp_mcp.organization_manager import OrganizationManager

    try:
        user = request.state.user
        org_id = int(request.path_params.get("id"))
        await OrganizationManager.delete_organization(org_id, user["id"])
        return JSONResponse({"success": True})
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Delete organization error: %s", e)
        return JSONResponse({"error": "Failed to delete organization"}, status_code=500)


@require_auth
async def transfer_organization_ownership_endpoint(request):
    """Transfer organization ownership to another admin."""
    from wp_mcp.organization_manager import OrganizationManager

    try:
        user = request.state.user
        org_id = int(request.path_params.get("id"))
        data = await request.json()

        new_owner_id = data.get("new_owner_id")
        password = data.get("password")

        if not new_owner_id or not password:
            return JSONResponse(
                {"error": "new_owner_id and password are required"}, status_code=400
            )

        await OrganizationManager.transfer_ownership(
            org_id, user["id"], new_owner_id, password
        )
        return JSONResponse({"success": True})
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Transfer ownership error: %s", e)
        return JSONResponse({"error": "Failed to transfer ownership"}, status_code=500)


async def search_organizations_endpoint(request):
    """Search for public organizations."""
    from wp_mcp.organization_manager import OrganizationManager

    try:
        query = request.query_params.get("q")
        visibility = request.query_params.get("visibility", "public")
        limit = int(request.query_params.get("limit", 50))
        offset = int(request.query_params.get("offset", 0))

        orgs = await OrganizationManager.search_organizations(
            query=query,
            visibility=visibility,
            limit=limit,
            offset=offset
        )
        return JSONResponse(sanitize_for_json(orgs))
    except Exception as e:
        logger.error("Search organizations error: %s", e)
        return JSONResponse({"error": "Failed to search organizations"}, status_code=500)


async def join_organization_endpoint(request):
    """Join a public organization."""
    from wp_mcp.user_manager import UserManager
    from wp_mcp.organization_manager import OrganizationManager

    try:
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return JSONResponse({"error": "Session required"}, status_code=401)

        user = await UserManager.get_user_from_session(session_id)
        if not user:
            return JSONResponse({"error": "Invalid session"}, status_code=401)

        org_id = int(request.path_params.get("id"))
        org = await OrganizationManager.request_to_join(org_id, user["id"])
        return JSONResponse(sanitize_for_json(org))
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Join organization error: %s", e)
        return JSONResponse({"error": "Failed to join organization"}, status_code=500)


async def get_organization_members_endpoint(request):
    """Get organization members."""
    from wp_mcp.organization_manager import OrganizationManager

    try:
        org_id = int(request.path_params.get("id"))
        members = await OrganizationManager.get_members(org_id)
        return JSONResponse(sanitize_for_json(members))
    except Exception as e:
        logger.error("Get members error: %s", e)
        return JSONResponse({"error": "Failed to get members"}, status_code=500)


async def update_member_role_endpoint(request):
    """Update member role."""
    from wp_mcp.user_manager import UserManager
    from wp_mcp.organization_manager import OrganizationManager

    try:
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return JSONResponse({"error": "Session required"}, status_code=401)

        user = await UserManager.get_user_from_session(session_id)
        if not user:
            return JSONResponse({"error": "Invalid session"}, status_code=401)

        org_id = int(request.path_params.get("id"))
        member_id = int(request.path_params.get("member_id"))
        data = await request.json()

        await OrganizationManager.update_member_role(
            org_id=org_id,
            target_user_id=member_id,
            new_role=data.get("role"),
            requester_user_id=user["id"],
        )
        return JSONResponse({"success": True})
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Update member role error: %s", e)
        return JSONResponse({"error": "Failed to update role"}, status_code=500)


@require_auth
async def remove_member_endpoint(request):
    """Remove member from organization."""
    from wp_mcp.organization_manager import OrganizationManager

    try:
        user = request.state.user

        org_id = int(request.path_params.get("id"))
        member_id = int(request.path_params.get("member_id"))

        await OrganizationManager.remove_member(
            org_id=org_id,
            target_user_id=member_id,
            requester_user_id=user["id"],
        )
        return JSONResponse({"success": True})
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Remove member error: %s", e)
        return JSONResponse({"error": "Failed to remove member"}, status_code=500)


# Organization invite endpoints
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
    """Get current user\'s pending invites."""
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


# Activity feed endpoints
async def get_user_activities_endpoint(request):
    """Get activities for a user."""
    from wp_mcp.user_manager import UserManager
    from wp_mcp.activity_manager import ActivityManager

    try:
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return JSONResponse({"error": "Session required"}, status_code=401)

        user = await UserManager.get_user_from_session(session_id)
        if not user:
            return JSONResponse({"error": "Invalid session"}, status_code=401)

        limit = int(request.query_params.get("limit", 50))
        offset = int(request.query_params.get("offset", 0))

        activities = await ActivityManager.get_user_activities(user["id"], limit, offset)
        return JSONResponse(sanitize_for_json(activities))
    except Exception as e:
        logger.error("Get user activities error: %s", e)
        return JSONResponse({"error": "Failed to get activities"}, status_code=500)


async def get_organization_activities_endpoint(request):
    """Get activities for an organization."""
    from wp_mcp.activity_manager import ActivityManager

    try:
        org_id = int(request.path_params.get("id"))
        limit = int(request.query_params.get("limit", 50))
        offset = int(request.query_params.get("offset", 0))

        activities = await ActivityManager.get_organization_activities(org_id, limit, offset)
        return JSONResponse(sanitize_for_json(activities))
    except Exception as e:
        logger.error("Get organization activities error: %s", e)
        return JSONResponse({"error": "Failed to get activities"}, status_code=500)


async def get_activity_feed_endpoint(request):
    """Get activity feed for the current user."""
    from wp_mcp.user_manager import UserManager
    from wp_mcp.activity_manager import ActivityManager

    try:
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return JSONResponse({"error": "Session required"}, status_code=401)

        user = await UserManager.get_user_from_session(session_id)
        if not user:
            return JSONResponse({"error": "Invalid session"}, status_code=401)

        limit = int(request.query_params.get("limit", 50))
        offset = int(request.query_params.get("offset", 0))

        activities = await ActivityManager.get_feed(user["id"], limit, offset)
        return JSONResponse(sanitize_for_json(activities))
    except Exception as e:
        logger.error("Get activity feed error: %s", e)
        return JSONResponse({"error": "Failed to get feed"}, status_code=500)


# Connection management endpoints
async def get_connections_endpoint(request):
    """Get user's WordPress connections."""
    from wp_mcp.user_manager import UserManager
    from wp_mcp.connection_manager import connection_manager

    try:
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return JSONResponse({"error": "Session required"}, status_code=401)

        user = await UserManager.get_user_from_session(session_id)
        if not user:
            return JSONResponse({"error": "Invalid session"}, status_code=401)

        connections = await connection_manager.get_connections(user["id"])
        return JSONResponse(sanitize_for_json(connections))
    except Exception as e:
        logger.error("Get connections error: %s", e)
        return JSONResponse({"error": "Failed to get connections"}, status_code=500)


async def add_connection_endpoint(request):
    """Add new WordPress connection."""
    from wp_mcp.user_manager import UserManager
    from wp_mcp.connection_manager import connection_manager

    try:
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return JSONResponse({"error": "Session required"}, status_code=401)

        user = await UserManager.get_user_from_session(session_id)
        if not user:
            return JSONResponse({"error": "Invalid session"}, status_code=401)

        data = await request.json()
        connection = await connection_manager.add_connection(
            user_id=user["id"],
            name=data.get("name"),
            wp_url=data.get("wp_url"),
            wp_graphql_endpoint=data.get("wp_graphql_endpoint"),
            wp_user=data.get("wp_user"),
            wp_app_password=data.get("wp_app_password"),
        )
        return JSONResponse(sanitize_for_json(connection), status_code=201)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Add connection error: %s", e)
        return JSONResponse({"error": "Failed to add connection"}, status_code=500)


async def update_connection_endpoint(request):
    """Update WordPress connection."""
    from wp_mcp.user_manager import UserManager
    from wp_mcp.connection_manager import connection_manager

    try:
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return JSONResponse({"error": "Session required"}, status_code=401)

        user = await UserManager.get_user_from_session(session_id)
        if not user:
            return JSONResponse({"error": "Invalid session"}, status_code=401)

        # Get connection ID from path
        connection_id = int(request.path_params.get("id"))
        data = await request.json()

        await connection_manager.update_connection(
            connection_id=connection_id,
            user_id=user["id"],
            name=data.get("name"),
            wp_url=data.get("wp_url"),
            wp_graphql_endpoint=data.get("wp_graphql_endpoint"),
            wp_user=data.get("wp_user"),
            wp_app_password=data.get("wp_app_password"),
        )
        return JSONResponse({"success": True})
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Update connection error: %s", e)
        return JSONResponse({"error": "Failed to update connection"}, status_code=500)


async def delete_connection_endpoint(request):
    """Delete WordPress connection."""
    from wp_mcp.user_manager import UserManager
    from wp_mcp.connection_manager import connection_manager

    try:
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return JSONResponse({"error": "Session required"}, status_code=401)

        user = await UserManager.get_user_from_session(session_id)
        if not user:
            return JSONResponse({"error": "Invalid session"}, status_code=401)

        connection_id = int(request.path_params.get("id"))
        await connection_manager.delete_connection(connection_id, user["id"])
        return JSONResponse({"success": True})
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Delete connection error: %s", e)
        return JSONResponse({"error": "Failed to delete connection"}, status_code=500)


async def activate_connection_endpoint(request):
    """Set connection as active."""
    from wp_mcp.user_manager import UserManager
    from wp_mcp.connection_manager import connection_manager

    try:
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return JSONResponse({"error": "Session required"}, status_code=401)

        user = await UserManager.get_user_from_session(session_id)
        if not user:
            return JSONResponse({"error": "Invalid session"}, status_code=401)

        connection_id = int(request.path_params.get("id"))
        await connection_manager.set_active_connection(connection_id, user["id"])
        return JSONResponse({"success": True})
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Activate connection error: %s", e)
        return JSONResponse({"error": "Failed to activate connection"}, status_code=500)


async def upload_file_endpoint(request):
    """Upload avatar or banner image with optional compression."""
    import uuid
    from pathlib import Path
    from wp_mcp.user_manager import UserManager
    from wp_mcp.image_compressor import ImageCompressor

    try:
        logger.info("Upload request received")
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return JSONResponse({"error": "Session required"}, status_code=401)

        user = await UserManager.get_user_from_session(session_id)
        if not user:
            return JSONResponse({"error": "Invalid session"}, status_code=401)

        # Get form data
        logger.info(f"Getting form data for user {user['id']}")
        form = await request.form()
        file = form.get("file")
        upload_type = form.get("type", "avatar")  # avatar or banner
        logger.info(f"Form data: file={'present' if file else 'missing'}, type={upload_type}")

        # Compression options (optional)
        compress = form.get("compress", "true").lower() == "true"  # Default: compress
        output_format = form.get("format")  # webp, avif, jpeg, png
        quality = form.get("quality")  # 1-100
        max_width = form.get("max_width")
        max_height = form.get("max_height")

        if not file:
            return JSONResponse({"error": "No file provided"}, status_code=400)

        # Validate file type
        allowed_extensions = {".jpg", ".jpeg", ".png", ".webp", ".avif"}
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in allowed_extensions:
            return JSONResponse(
                {"error": f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"},
                status_code=400
            )

        # Read file content
        content = await file.read()

        # Validate file size (max 10MB before compression)
        max_size = 10 * 1024 * 1024  # 10MB
        if len(content) > max_size:
            return JSONResponse(
                {"error": "File too large. Maximum size is 10MB"},
                status_code=400
            )

        compression_metadata = None

        # Compress image if requested
        if compress and ImageCompressor.is_available():
            try:
                # Parse numeric parameters
                quality_int = int(quality) if quality else None
                max_width_int = int(max_width) if max_width else None
                max_height_int = int(max_height) if max_height else None

                # Apply sane defaults based on upload type
                if not output_format:
                    output_format = "webp"  # Default to WebP

                if not quality_int:
                    quality_int = 85  # Default quality

                if upload_type == "avatar" and not max_width_int:
                    max_width_int = 512  # Max 512px for avatars

                if upload_type == "banner" and not max_width_int:
                    max_width_int = 2048  # Max 2048px for banners

                content, compression_metadata = ImageCompressor.compress_image(
                    content,
                    output_format=output_format,
                    quality=quality_int,
                    max_width=max_width_int,
                    max_height=max_height_int,
                    preserve_exif=False,  # Strip EXIF for privacy
                    auto_orient=True,
                )

                # Update file extension based on output format
                if output_format:
                    file_ext = f".{output_format.lower()}"

                logger.info(f"Image compressed: {compression_metadata}")

            except Exception as e:
                logger.warning(f"Compression failed, using original: {e}")
                # Continue with original file if compression fails

        # Validate final size
        if len(content) > 5 * 1024 * 1024:
            return JSONResponse(
                {"error": "File too large after compression. Maximum size is 5MB"},
                status_code=400
            )

        # Create uploads directory if it doesn't exist
        uploads_dir = Path(__file__).parent.parent.parent / "uploads" / upload_type
        uploads_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        unique_filename = f"{user['id']}_{uuid.uuid4().hex}{file_ext}"
        file_path = uploads_dir / unique_filename

        # Save file
        with open(file_path, "wb") as f:
            f.write(content)

        # Return URL
        file_url = f"/uploads/{upload_type}/{unique_filename}"

        logger.info(f"File uploaded: {file_url} by user {user['id']}")

        response_data = {
            "success": True,
            "url": file_url,
            "filename": unique_filename,
            "size": len(content),
        }

        if compression_metadata:
            response_data["metadata"] = compression_metadata

        return JSONResponse(response_data)

    except ValueError as e:
        logger.warning(f"Upload validation error: {e}")
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error(f"File upload error: {e}", exc_info=True)
        return JSONResponse(
            {"error": "Upload failed", "details": str(e)},
            status_code=500
        )


async def setup_remote_wordpress_endpoint(request):
    """Setup remote WordPress via SSH and optionally create connection."""
    import asyncio
    import json
    import tempfile
    from pathlib import Path
    from wp_mcp.user_manager import UserManager
    from wp_mcp.connection_manager import connection_manager

    try:
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return JSONResponse({"error": "Session required"}, status_code=401)

        user = await UserManager.get_user_from_session(session_id)
        if not user:
            return JSONResponse({"error": "Invalid session"}, status_code=401)

        data = await request.json()
        host = data.get("host")
        ssh_user = data.get("user")
        port = data.get("port", 22)
        ssh_key = data.get("ssh_key")  # SSH private key content
        ssh_password = data.get("ssh_password")
        wp_path = data.get("wp_path")  # Optional WordPress directory path
        discover_only = data.get("discover", False)  # Discovery mode
        auto_create = data.get("auto_create", False)  # Auto-create connection

        # Defensive: validate inputs
        if not host or not ssh_user:
            return JSONResponse(
                {"error": "host and user are required"},
                status_code=400
            )

        if not ssh_key and not ssh_password:
            return JSONResponse(
                {"error": "Either ssh_key or ssh_password is required"},
                status_code=400
            )

        # Defensive: validate port
        if not isinstance(port, int) or port < 1 or port > 65535:
            return JSONResponse(
                {"error": "Invalid port number"},
                status_code=400
            )

        # Defensive: sanitize wp_path if provided
        if wp_path:
            if not isinstance(wp_path, str) or not wp_path.startswith('/'):
                return JSONResponse(
                    {"error": "Invalid wp_path: must be absolute path"},
                    status_code=400
                )

        # Find the setup script
        script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "setup-remote-wordpress.py"
        if not script_path.exists():
            return JSONResponse(
                {"error": "Setup script not found"},
                status_code=500
            )

        # Prepare command
        cmd = ["python3", str(script_path), "--host", host, "--user", ssh_user, "--port", str(port)]

        # Add discovery flag if requested
        if discover_only:
            cmd.append("--discover")

        # Add wp_path if provided
        if wp_path and not discover_only:
            cmd.extend(["--wp-path", wp_path])

        # Handle SSH key (write to temp file)
        key_file = None
        if ssh_key:
            key_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem')
            key_file.write(ssh_key)
            key_file.close()
            # Set proper permissions for SSH key
            Path(key_file.name).chmod(0o600)
            cmd.extend(["--key", key_file.name])
        else:
            cmd.extend(["--password", ssh_password])

        # Run setup script
        logger.info(f"Running remote WordPress setup for {host}")
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        # Clean up temp key file
        if key_file:
            try:
                Path(key_file.name).unlink()
            except:
                pass

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Setup failed"
            logger.error(f"Remote setup failed: {error_msg}")
            return JSONResponse(
                {"error": "Remote setup failed", "details": error_msg},
                status_code=500
            )

        # Parse output
        output = stdout.decode()
        logger.info(f"Remote setup output: {output}")

        # Extract JSON from output
        try:
            # Find the JSON block in output
            json_start = output.find('{')
            json_end = output.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                result = json.loads(output[json_start:json_end])
            else:
                return JSONResponse(
                    {"error": "Failed to parse output"},
                    status_code=500
                )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse output: {e}")
            return JSONResponse(
                {"error": "Failed to parse output", "details": output},
                status_code=500
            )

        # Handle discovery mode
        if discover_only:
            return JSONResponse({
                "success": True,
                "discover": True,
                "installations": result.get("installations", []),
                "count": result.get("count", 0)
            })

        # Handle setup mode
        connection_info = result

        # Auto-create connection if requested
        connection = None
        if auto_create:
            try:
                connection = await connection_manager.add_connection(
                    user_id=user["id"],
                    name=connection_info.get("name"),
                    wp_url=connection_info.get("wp_url"),
                    wp_graphql_endpoint=connection_info.get("wp_graphql_endpoint"),
                    wp_user=connection_info.get("wp_user"),
                    wp_app_password=connection_info.get("wp_app_password"),
                )
                logger.info(f"Auto-created connection {connection['id']} for user {user['id']}")
            except Exception as e:
                logger.error(f"Failed to auto-create connection: {e}")
                # Don't fail the whole request if connection creation fails

        return JSONResponse({
            "success": True,
            "connection_info": connection_info,
            "connection": connection,
            "output": output
        }, status_code=201)

    except Exception as e:
        logger.error(f"Remote WordPress setup error: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"error": "Setup failed", "details": str(e)},
            status_code=500
        )


# Create a simple Starlette app instead of using FastMCP's transport
# We'll handle JSON-RPC directly and call FastMCP tools
from starlette.applications import Starlette
from starlette.responses import JSONResponse as StarletteJSONResponse

mcp._app = Starlette()
logger.info("Created Starlette app for custom JSON-RPC handling")


# Custom JSON-RPC endpoint for MCP tool calls
async def mcp_jsonrpc_endpoint(request):
    """Handle JSON-RPC requests for MCP tools"""
    try:
        body = await request.json()
        logger.info(f"MCP JSON-RPC request: {body}")

        # Validate JSON-RPC format
        if body.get("jsonrpc") != "2.0":
            return StarletteJSONResponse(
                {"jsonrpc": "2.0", "id": body.get("id"), "error": {"code": -32600, "message": "Invalid JSON-RPC version"}},
                status_code=400
            )

        method = body.get("method")
        params = body.get("params", {})
        request_id = body.get("id")

        if method == "tools/list":
            # List available tools
            tools = await mcp.list_tools()
            return StarletteJSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"tools": tools}
            })

        elif method == "tools/call":
            # Call a tool
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})

            # Extract connection context from request scope (set by auth middleware)
            state = request.scope.get("state", {})
            connection = state.get("connection")
            user = state.get("user")

            # Add connection context to tool args if available
            if connection and user:
                tool_args["context"] = {
                    "connection_id": connection.get("id"),
                    "user_id": user.get("id"),
                }
                logger.info(f"Calling tool: {tool_name} with connection_id={connection.get('id')}, user_id={user.get('id')}")
            else:
                logger.warning(f"Calling tool: {tool_name} without connection context")

            # Call the MCP tool directly
            result = await mcp.call_tool(tool_name, tool_args)

            logger.info(f"Tool result: {result}")

            # Extract the actual data from MCP result format
            # result is a ToolCallResult with content array and metadata
            if hasattr(result, 'content') and result.content:
                # Extract text from first TextContent
                text_content = result.content[0]
                if hasattr(text_content, 'text'):
                    # Try to parse as JSON, otherwise return as string
                    try:
                        import json as json_lib
                        data = json_lib.loads(text_content.text)
                        return StarletteJSONResponse({
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": {
                                "content": [{"type": "text", "text": text_content.text}]
                            }
                        })
                    except:
                        return StarletteJSONResponse({
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": {
                                "content": [{"type": "text", "text": text_content.text}]
                            }
                        })

            # Fallback: return as-is (shouldn't happen)
            return StarletteJSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"content": [{"type": "text", "text": str(result)}]}
            })

        else:
            return StarletteJSONResponse(
                {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Method not found: {method}"}},
                status_code=404
            )

    except Exception as e:
        logger.error(f"MCP JSON-RPC error: {e}", exc_info=True)
        return StarletteJSONResponse(
            {"jsonrpc": "2.0", "id": body.get("id") if 'body' in locals() else None, "error": {"code": -32603, "message": str(e)}},
            status_code=500
        )

# Create uploads directory if it doesn't exist
from pathlib import Path
uploads_dir = Path(__file__).parent.parent.parent / "uploads"
uploads_dir.mkdir(exist_ok=True)
(uploads_dir / "avatar").mkdir(exist_ok=True)
(uploads_dir / "banner").mkdir(exist_ok=True)

# Add all routes including the custom MCP JSON-RPC endpoint
mcp._app.routes.extend(
    [
        Route("/mcp", mcp_jsonrpc_endpoint, methods=["POST"]),
        Route("/health", health_endpoint),
        Route("/health/ready", health_ready_endpoint),
        Route("/health/live", health_endpoint),
        Route("/health/deep", health_deep_endpoint),
        Route("/metrics", metrics_endpoint),
        # Auth routes
        Route("/register", register_endpoint, methods=["POST"]),
        Route("/login", login_endpoint, methods=["POST"]),
        Route("/logout", logout_endpoint, methods=["POST"]),
        Route("/me", me_endpoint, methods=["GET"]),
        # Profile routes
        Route("/profile", get_profile_endpoint, methods=["GET"]),
        Route("/profile", update_profile_endpoint, methods=["PUT"]),
        Route("/profile", delete_user_account_endpoint, methods=["DELETE"]),
        Route("/profile/{username}", get_profile_by_username_endpoint, methods=["GET"]),
        # Organization routes
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
        # Organization invite routes
        Route("/organizations/{id:int}/invites", create_invite_endpoint, methods=["POST"]),
        Route("/organizations/{id:int}/invites", get_organization_invites_endpoint, methods=["GET"]),
        Route("/organizations/{id:int}/invites/{invite_id:int}", cancel_invite_endpoint, methods=["DELETE"]),
        Route("/invites", get_user_invites_endpoint, methods=["GET"]),
        Route("/invites/accept", accept_invite_endpoint, methods=["POST"]),
        Route("/invites/reject", reject_invite_endpoint, methods=["POST"]),
        # Activity feed routes
        Route("/activities", get_user_activities_endpoint, methods=["GET"]),
        Route("/activities/feed", get_activity_feed_endpoint, methods=["GET"]),
        Route("/organizations/{id:int}/activities", get_organization_activities_endpoint, methods=["GET"]),
        # Connection routes
        Route("/connections", get_connections_endpoint, methods=["GET"]),
        Route("/connections", add_connection_endpoint, methods=["POST"]),
        Route("/connections/{id:int}", update_connection_endpoint, methods=["PUT"]),
        Route("/connections/{id:int}", delete_connection_endpoint, methods=["DELETE"]),
        Route("/connections/{id:int}/activate", activate_connection_endpoint, methods=["POST"]),
        Route("/connections/setup-remote", setup_remote_wordpress_endpoint, methods=["POST"]),
        # Upload route
        Route("/upload", upload_file_endpoint, methods=["POST"]),
        # Audit logs routes (require authentication)
        Route("/audit/logs", audit_logs_endpoint, methods=["GET"]),
        Route("/audit/summary", audit_summary_endpoint, methods=["GET"]),
        # Static files
        Mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads"),
    ]
)

# NOW wrap app with authentication middleware AFTER routes are added
mcp._app = AuthMiddleware(mcp._app)
logger.info("Authentication middleware enabled")


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

    if transport == "streamable-http":
        # For HTTP transport, use uvicorn to serve FastMCP's ASGI app
        import uvicorn

        # Get the wrapped app (AuthMiddleware wrapping Starlette)
        wrapped_app = getattr(mcp, '_app', None) or getattr(mcp, 'app', None) or mcp

        # Get the underlying Starlette app to register startup event
        # AuthMiddleware.app contains the actual Starlette instance
        starlette_app = wrapped_app.app if hasattr(wrapped_app, 'app') else wrapped_app

        # Add startup event to the underlying Starlette app
        @starlette_app.on_event("startup")
        async def on_startup():
            await startup()

        uvicorn.run(
            wrapped_app,
            host=config.mcp_host,
            port=config.mcp_port,
            log_level="info",
        )
    elif transport == "sse":
        # For SSE transport, use uvicorn as well
        import uvicorn

        # Get the wrapped app (AuthMiddleware wrapping Starlette)
        wrapped_app = getattr(mcp, '_app', None) or getattr(mcp, 'app', None) or mcp

        # Get the underlying Starlette app to register startup event
        starlette_app = wrapped_app.app if hasattr(wrapped_app, 'app') else wrapped_app

        # Add startup event to the underlying Starlette app
        @starlette_app.on_event("startup")
        async def on_startup():
            await startup()

        uvicorn.run(
            wrapped_app,
            host=config.mcp_host,
            port=config.mcp_port,
            log_level="info",
        )
    else:
        # Default to stdio for local development
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

"""Organization management endpoints."""

from __future__ import annotations

import logging
from starlette.responses import JSONResponse

from wp_mcp.audit import EventCategory, Severity
from wp_mcp.decorators import require_auth
from wp_mcp.json_utils import sanitize_for_json

logger = logging.getLogger(__name__)


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


@require_auth
async def create_org_api_key_endpoint(request):
    """Create organization API key for remote WordPress registration."""
    from wp_mcp.org_api_key_manager import OrgApiKeyManager

    try:
        user = request.state.user
        org_id = int(request.path_params.get("id"))
        data = await request.json()

        key_data = await OrgApiKeyManager.create_api_key(
            organization_id=org_id,
            created_by=user["id"],
            description=data.get("description"),
            expiry_days=data.get("expiry_days", 7),
        )
        return JSONResponse(sanitize_for_json(key_data), status_code=201)
    except ValueError as e:
        logger.warning("Create API key error: %s", e)
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Create API key error: %s", e, exc_info=True)
        return JSONResponse({"error": "Failed to create API key"}, status_code=500)


@require_auth
async def list_org_api_keys_endpoint(request):
    """List organization API keys."""
    from wp_mcp.org_api_key_manager import OrgApiKeyManager

    try:
        user = request.state.user
        org_id = int(request.path_params.get("id"))

        keys = await OrgApiKeyManager.list_keys(org_id, user["id"])
        return JSONResponse(sanitize_for_json(keys))
    except ValueError as e:
        logger.warning("List API keys error: %s", e)
        return JSONResponse({"error": str(e)}, status_code=403)
    except Exception as e:
        logger.error("List API keys error: %s", e, exc_info=True)
        return JSONResponse({"error": "Failed to list API keys"}, status_code=500)


@require_auth
async def revoke_org_api_key_endpoint(request):
    """Revoke organization API key."""
    from wp_mcp.org_api_key_manager import OrgApiKeyManager

    try:
        user = request.state.user
        org_id = int(request.path_params.get("id"))
        key_id = int(request.path_params.get("key_id"))

        await OrgApiKeyManager.revoke_key(key_id, org_id, user["id"])
        return JSONResponse({"success": True})
    except ValueError as e:
        logger.warning("Revoke API key error: %s", e)
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Revoke API key error: %s", e, exc_info=True)
        return JSONResponse({"error": "Failed to revoke API key"}, status_code=500)


async def register_remote_wordpress_endpoint(request):
    """Register a remote WordPress site using organization API key (PUBLIC endpoint)."""
    from wp_mcp.org_api_key_manager import OrgApiKeyManager
    from wp_mcp.connection_manager import connection_manager
    from wp_mcp.audit import AuditLog

    client_ip = request.client.host if request.client else None

    try:
        data = await request.json()
        api_key = data.get("api_key")
        site_name = data.get("site_name")
        wp_url = data.get("wp_url")
        wp_graphql_endpoint = data.get("wp_graphql_endpoint")
        wp_user = data.get("wp_user")
        wp_app_password = data.get("wp_app_password")

        # Validate required fields
        if not all([api_key, site_name, wp_url, wp_graphql_endpoint, wp_user, wp_app_password]):
            return JSONResponse(
                {"error": "Missing required fields: api_key, site_name, wp_url, wp_graphql_endpoint, wp_user, wp_app_password"},
                status_code=400
            )

        # Validate and consume API key (single-use)
        org_data = await OrgApiKeyManager.validate_and_consume_key(api_key)
        if not org_data:
            await AuditLog.log_access_denied(
                user_id=None,
                resource_type="api_registration",
                resource_id="wordpress_connection",
                reason="Invalid or expired API key",
                ip_address=client_ip,
            )
            return JSONResponse(
                {"error": "Invalid, expired, or already used API key"},
                status_code=401
            )

        # Create organization connection
        connection = await connection_manager.add_org_connection(
            organization_id=org_data["organization_id"],
            name=site_name,
            wp_url=wp_url,
            wp_graphql_endpoint=wp_graphql_endpoint,
            wp_user=wp_user,
            wp_app_password=wp_app_password,
        )

        # Log successful registration
        await AuditLog.log_event(
            event_type="api_registration",
            category=EventCategory.ACCESS,
            severity=Severity.INFO,
            user_id=None,
            ip_address=client_ip,
            resource_type="wordpress_connection",
            resource_id=str(connection["id"]),
            action="create_org_connection",
            status="success",
            message=f"Remote WordPress registered: {site_name}",
            metadata={
                "organization_id": org_data["organization_id"],
                "site_name": site_name,
            }
        )

        logger.info(
            f"Remote WordPress registered: {site_name} for org {org_data['organization_id']}"
        )

        return JSONResponse({
            "success": True,
            "connection_id": connection["id"],
            "organization": {
                "id": org_data["organization_id"],
                "name": org_data["organization_name"],
                "slug": org_data["organization_slug"],
            },
            "message": f"Successfully registered with {org_data['organization_name']}"
        }, status_code=201)

    except ValueError as e:
        logger.warning(f"Registration validation error: {e}")
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error(f"Registration error: {e}", exc_info=True)
        return JSONResponse(
            {"error": "Registration failed. Please check your WordPress configuration."},
            status_code=500
        )

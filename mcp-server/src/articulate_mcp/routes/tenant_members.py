"""REST endpoints for managing tenant team members and role sync."""

import os
import logging
from starlette.requests import Request
from starlette.responses import JSONResponse

from articulate_mcp.database import db
from articulate_mcp.user_manager import UserManager
from articulate_mcp.json_utils import sanitize_for_json
from articulate_mcp.tenants.wp_user_sync import (
    create_wp_user_for_tenant,
    update_wp_user_role_for_tenant,
    ROLE_MAP,
)

logger = logging.getLogger(__name__)


async def _get_user(request):
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        return None
    return await UserManager.get_user_from_session(session_id)


def _get_crypto():
    from articulate_mcp.tenants.crypto import TenantCrypto
    encryption_key = os.getenv("ENCRYPTION_KEY")
    if not encryption_key:
        raise RuntimeError("ENCRYPTION_KEY required")
    return TenantCrypto(encryption_key)


async def list_tenant_members_endpoint(request: Request):
    """List members of a tenant with their WP roles."""
    user = await _get_user(request)
    if not user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    tenant_id = request.path_params["tenant_id"]

    # Check requester is a member
    requester = await db.fetchone(
        "SELECT role FROM tenant_users WHERE tenant_id = %s AND user_id = %s",
        (tenant_id, user["id"]),
    )
    if not requester:
        return JSONResponse({"error": "Not a member of this tenant"}, status_code=403)

    members = await db.fetchall(
        """SELECT tu.user_id, tu.role, tu.wp_user_id, tu.wp_username, tu.wp_role,
                  ua.email, ua.name
           FROM tenant_users tu
           JOIN articulate_users_auth ua ON tu.user_id = ua.id
           WHERE tu.tenant_id = %s
           ORDER BY FIELD(tu.role, 'owner', 'admin', 'editor', 'viewer'), ua.name""",
        (tenant_id,),
    )

    return JSONResponse(sanitize_for_json({"members": members}))


async def add_tenant_member_endpoint(request: Request):
    """Add a user to a tenant and create their WordPress account."""
    user = await _get_user(request)
    if not user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    tenant_id = request.path_params["tenant_id"]
    data = await request.json()

    email = data.get("email", "").strip()
    role = data.get("role", "viewer")

    if not email:
        return JSONResponse({"error": "Email required"}, status_code=400)

    if role not in ("admin", "editor", "viewer"):
        return JSONResponse({"error": "Invalid role. Must be admin, editor, or viewer"}, status_code=400)

    # Check requester is tenant owner or admin
    requester_role = await db.fetchone(
        "SELECT role FROM tenant_users WHERE tenant_id = %s AND user_id = %s",
        (tenant_id, user["id"]),
    )
    if not requester_role or requester_role["role"] not in ("owner", "admin"):
        return JSONResponse({"error": "Not authorized"}, status_code=403)

    # Find the user to add
    target_user = await db.fetchone(
        "SELECT id, email, name FROM articulate_users_auth WHERE email = %s",
        (email,),
    )
    if not target_user:
        return JSONResponse({"error": "User not found. They must register on Articulate first."}, status_code=404)

    # Check not already a member
    existing = await db.fetchone(
        "SELECT id FROM tenant_users WHERE tenant_id = %s AND user_id = %s",
        (tenant_id, target_user["id"]),
    )
    if existing:
        return JSONResponse({"error": "User is already a member of this tenant"}, status_code=409)

    # Get tenant info for WP user creation
    tenant = await db.fetchone(
        """SELECT t.id, t.slug, ts.wp_admin_password
           FROM tenants t
           JOIN tenant_secrets ts ON ts.tenant_id = t.id
           WHERE t.id = %s""",
        (tenant_id,),
    )
    if not tenant:
        return JSONResponse({"error": "Tenant not found"}, status_code=404)

    # Add to tenant_users
    await db.insert(
        "INSERT INTO tenant_users (tenant_id, user_id, role) VALUES (%s, %s, %s)",
        (tenant_id, target_user["id"], role),
    )

    # Create WordPress user
    wp_user = None
    try:
        crypto = _get_crypto()
        wp_admin_pass = crypto.decrypt(tenant["wp_admin_password"])
        wp_user = await create_wp_user_for_tenant(
            wp_url=f"http://tenant_{tenant_id}_wordpress:80",
            wp_admin_user="admin",
            wp_admin_password=wp_admin_pass,
            articulate_user_email=target_user["email"],
            articulate_user_name=target_user.get("name", ""),
            articulate_role=role,
        )
        if wp_user:
            await db.execute(
                """UPDATE tenant_users
                   SET wp_user_id = %s, wp_username = %s, wp_role = %s
                   WHERE tenant_id = %s AND user_id = %s""",
                (wp_user["wp_user_id"], wp_user["wp_username"], wp_user["wp_role"],
                 tenant_id, target_user["id"]),
            )
    except Exception as e:
        logger.warning("Could not create WP user for new tenant member: %s", e)

    return JSONResponse({
        "success": True,
        "member": {
            "user_id": target_user["id"],
            "email": target_user["email"],
            "name": target_user.get("name", ""),
            "role": role,
            "wp_username": wp_user["wp_username"] if wp_user else None,
            "wp_role": wp_user["wp_role"] if wp_user else None,
        },
    }, status_code=201)


async def update_tenant_member_role_endpoint(request: Request):
    """Update a tenant member's role and sync to WordPress."""
    user = await _get_user(request)
    if not user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    tenant_id = request.path_params["tenant_id"]
    member_user_id = int(request.path_params["member_id"])
    data = await request.json()

    new_role = data.get("role")
    if new_role not in ("admin", "editor", "viewer"):
        return JSONResponse({"error": "Invalid role. Must be admin, editor, or viewer"}, status_code=400)

    # Check requester is owner or admin
    requester_role = await db.fetchone(
        "SELECT role FROM tenant_users WHERE tenant_id = %s AND user_id = %s",
        (tenant_id, user["id"]),
    )
    if not requester_role or requester_role["role"] not in ("owner", "admin"):
        return JSONResponse({"error": "Not authorized"}, status_code=403)

    # Get current member info
    member = await db.fetchone(
        "SELECT * FROM tenant_users WHERE tenant_id = %s AND user_id = %s",
        (tenant_id, member_user_id),
    )
    if not member:
        return JSONResponse({"error": "Member not found"}, status_code=404)

    if member["role"] == "owner":
        return JSONResponse({"error": "Cannot change owner role"}, status_code=400)

    # Update Articulate role
    await db.execute(
        "UPDATE tenant_users SET role = %s WHERE tenant_id = %s AND user_id = %s",
        (new_role, tenant_id, member_user_id),
    )

    # Sync to WordPress if wp_user_id exists
    wp_synced = False
    if member.get("wp_user_id"):
        try:
            tenant = await db.fetchone(
                """SELECT t.slug, ts.wp_admin_password
                   FROM tenants t
                   JOIN tenant_secrets ts ON ts.tenant_id = t.id
                   WHERE t.id = %s""",
                (tenant_id,),
            )
            if tenant:
                crypto = _get_crypto()
                wp_admin_pass = crypto.decrypt(tenant["wp_admin_password"])
                wp_synced = await update_wp_user_role_for_tenant(
                    wp_url=f"http://tenant_{tenant_id}_wordpress:80",
                    wp_admin_user="admin",
                    wp_admin_password=wp_admin_pass,
                    wp_user_id=member["wp_user_id"],
                    new_articulate_role=new_role,
                )
                if wp_synced:
                    new_wp_role = ROLE_MAP.get(new_role, "subscriber")
                    await db.execute(
                        "UPDATE tenant_users SET wp_role = %s WHERE tenant_id = %s AND user_id = %s",
                        (new_wp_role, tenant_id, member_user_id),
                    )
        except Exception as e:
            logger.warning("Could not sync WP role for tenant member: %s", e)

    return JSONResponse({
        "success": True,
        "role": new_role,
        "wp_synced": wp_synced,
    })


async def remove_tenant_member_endpoint(request: Request):
    """Remove a member from a tenant."""
    user = await _get_user(request)
    if not user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    tenant_id = request.path_params["tenant_id"]
    member_user_id = int(request.path_params["member_id"])

    # Check requester is owner or admin
    requester_role = await db.fetchone(
        "SELECT role FROM tenant_users WHERE tenant_id = %s AND user_id = %s",
        (tenant_id, user["id"]),
    )
    if not requester_role or requester_role["role"] not in ("owner", "admin"):
        return JSONResponse({"error": "Not authorized"}, status_code=403)

    # Can't remove owner
    member = await db.fetchone(
        "SELECT role FROM tenant_users WHERE tenant_id = %s AND user_id = %s",
        (tenant_id, member_user_id),
    )
    if not member:
        return JSONResponse({"error": "Member not found"}, status_code=404)
    if member["role"] == "owner":
        return JSONResponse({"error": "Cannot remove tenant owner"}, status_code=400)

    await db.execute(
        "DELETE FROM tenant_users WHERE tenant_id = %s AND user_id = %s",
        (tenant_id, member_user_id),
    )

    return JSONResponse({"success": True})

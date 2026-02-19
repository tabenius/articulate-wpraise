"""
MCP Tools for Multi-Tenant Management

Allows users to create and manage multiple WordPress instances.
"""

import os
import logging
from typing import Optional
from wp_mcp.server import mcp
from wp_mcp.tenant_manager import TenantManager

logger = logging.getLogger(__name__)

# Initialize tenant manager with encryption key
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    logger.warning("ENCRYPTION_KEY not set - tenant management will be disabled")
    tenant_manager = None
else:
    tenant_manager = TenantManager(ENCRYPTION_KEY)


@mcp.tool()
async def create_tenant(
    name: str,
    slug: str,
    wp_url: str,
    wp_graphql_endpoint: str,
    wp_admin_user: str,
    wp_admin_email: Optional[str] = None,
    db_host: Optional[str] = None,
    db_name: Optional[str] = None,
    db_user: Optional[str] = None,
    db_password: Optional[str] = None,
    max_posts: int = 1000,
    max_storage_mb: int = 5000,
    max_users: int = 10,
) -> dict:
    """
    Create a new tenant (isolated WordPress instance)

    Args:
        name: Human-readable tenant name (e.g., "Acme Corporation")
        slug: URL-safe identifier (e.g., "acme-corp")
        wp_url: WordPress instance URL
        wp_graphql_endpoint: WordPress GraphQL endpoint
        wp_admin_user: WordPress admin username
        wp_admin_email: WordPress admin email
        db_host: Database host (optional, for separate DB)
        db_name: Database name
        db_user: Database username
        db_password: Database password (will be encrypted)
        max_posts: Maximum posts allowed
        max_storage_mb: Maximum storage in MB
        max_users: Maximum users allowed

    Returns:
        Tenant information including tenant_id
    """
    if not tenant_manager:
        return {"error": "Multi-tenancy not configured (missing ENCRYPTION_KEY)"}

    # Get current user from context
    from wp_mcp.middleware import get_current_user  # type: ignore[attr-defined]  # type: ignore[attr-defined]

    user = get_current_user()
    if not user:
        return {"error": "Authentication required"}

    try:
        tenant_id = tenant_manager.create_tenant(
            name=name,
            slug=slug,
            owner_user_id=user["id"],
            wp_url=wp_url,
            wp_graphql_endpoint=wp_graphql_endpoint,
            wp_admin_user=wp_admin_user,
            wp_admin_email=wp_admin_email,
            db_host=db_host,
            db_name=db_name,
            db_user=db_user,
            db_password=db_password,
            max_posts=max_posts,
            max_storage_mb=max_storage_mb,
            max_users=max_users,
        )

        return {
            "success": True,
            "tenant_id": tenant_id,
            "name": name,
            "slug": slug,
            "message": f"Tenant '{name}' created successfully",
        }

    except Exception as e:
        logger.error(f"Failed to create tenant: {e}")
        return {"error": f"Failed to create tenant: {str(e)}"}


@mcp.tool()
async def list_my_tenants() -> dict:
    """
    List all tenants accessible by the current user

    Returns:
        List of tenant information
    """
    if not tenant_manager:
        return {"error": "Multi-tenancy not configured"}

    from wp_mcp.middleware import get_current_user  # type: ignore[attr-defined]

    user = get_current_user()
    if not user:
        return {"error": "Authentication required"}

    try:
        tenants = tenant_manager.get_user_tenants(user["id"])

        return {
            "success": True,
            "tenants": tenants,
            "count": len(tenants),
        }

    except Exception as e:
        logger.error(f"Failed to list tenants: {e}")
        return {"error": f"Failed to list tenants: {str(e)}"}


@mcp.tool()
async def get_tenant_details(tenant_id: str) -> dict:
    """
    Get detailed information about a specific tenant

    Args:
        tenant_id: UUID of the tenant

    Returns:
        Tenant details including usage statistics
    """
    if not tenant_manager:
        return {"error": "Multi-tenancy not configured"}

    from wp_mcp.middleware import get_current_user  # type: ignore[attr-defined]

    user = get_current_user()
    if not user:
        return {"error": "Authentication required"}

    try:
        tenant = tenant_manager.get_tenant(tenant_id)
        if not tenant:
            return {"error": "Tenant not found"}

        # Get usage statistics
        usage = tenant_manager.get_tenant_usage(tenant_id)

        return {
            "success": True,
            "tenant": tenant,
            "usage": usage,
        }

    except Exception as e:
        logger.error(f"Failed to get tenant details: {e}")
        return {"error": f"Failed to get tenant details: {str(e)}"}


@mcp.tool()
async def update_tenant_status(tenant_id: str, status: str) -> dict:
    """
    Update tenant status (active, suspended, deleted)

    Args:
        tenant_id: UUID of the tenant
        status: New status (active, suspended, deleted)

    Returns:
        Success confirmation
    """
    if not tenant_manager:
        return {"error": "Multi-tenancy not configured"}

    from wp_mcp.middleware import get_current_user  # type: ignore[attr-defined]

    user = get_current_user()
    if not user:
        return {"error": "Authentication required"}

    try:
        # Verify user has permission (owner or admin)
        success = tenant_manager.update_tenant_status(tenant_id, status)

        if success:
            return {
                "success": True,
                "tenant_id": tenant_id,
                "status": status,
                "message": f"Tenant status updated to {status}",
            }
        else:
            return {"error": "Tenant not found or no permission"}

    except Exception as e:
        logger.error(f"Failed to update tenant status: {e}")
        return {"error": f"Failed to update tenant status: {str(e)}"}


@mcp.tool()
async def add_user_to_tenant(
    tenant_id: str, user_email: str, role: str = "viewer"
) -> dict:
    """
    Add a user to a tenant with specified role

    Args:
        tenant_id: UUID of the tenant
        user_email: Email of the user to add
        role: Role to assign (owner, admin, editor, viewer)

    Returns:
        Success confirmation
    """
    if not tenant_manager:
        return {"error": "Multi-tenancy not configured"}

    from wp_mcp.middleware import get_current_user  # type: ignore[attr-defined]
    from wp_mcp.database import get_connection  # type: ignore[attr-defined]

    current_user = get_current_user()
    if not current_user:
        return {"error": "Authentication required"}

    try:
        # Find user by email
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM users WHERE email = %s", (user_email,))
        target_user = cursor.fetchone()
        cursor.close()

        if not target_user:
            return {"error": f"User not found: {user_email}"}

        # Add user to tenant
        tenant_manager.add_user_to_tenant(tenant_id, target_user["id"], role)

        return {
            "success": True,
            "tenant_id": tenant_id,
            "user_email": user_email,
            "role": role,
            "message": f"User {user_email} added to tenant with role {role}",
        }

    except Exception as e:
        logger.error(f"Failed to add user to tenant: {e}")
        return {"error": f"Failed to add user to tenant: {str(e)}"}


@mcp.tool()
async def remove_user_from_tenant(tenant_id: str, user_email: str) -> dict:
    """
    Remove a user from a tenant

    Args:
        tenant_id: UUID of the tenant
        user_email: Email of the user to remove

    Returns:
        Success confirmation
    """
    if not tenant_manager:
        return {"error": "Multi-tenancy not configured"}

    from wp_mcp.middleware import get_current_user  # type: ignore[attr-defined]
    from wp_mcp.database import get_connection  # type: ignore[attr-defined]

    current_user = get_current_user()
    if not current_user:
        return {"error": "Authentication required"}

    try:
        # Find user by email
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM users WHERE email = %s", (user_email,))
        target_user = cursor.fetchone()
        cursor.close()

        if not target_user:
            return {"error": f"User not found: {user_email}"}

        # Remove user from tenant
        success = tenant_manager.remove_user_from_tenant(tenant_id, target_user["id"])

        if success:
            return {
                "success": True,
                "tenant_id": tenant_id,
                "user_email": user_email,
                "message": f"User {user_email} removed from tenant",
            }
        else:
            return {"error": "User not in tenant or cannot be removed"}

    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Failed to remove user from tenant: {e}")
        return {"error": f"Failed to remove user from tenant: {str(e)}"}

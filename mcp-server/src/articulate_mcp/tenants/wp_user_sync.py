"""Sync Articulate users to WordPress tenant users.

When a user is added to a tenant (or a tenant is provisioned), this module
creates corresponding WordPress users on the tenant's WordPress instance and
maps Articulate tenant roles to WordPress roles.
"""

import logging
import secrets
import httpx

logger = logging.getLogger("articulate-mcp")

# Map Articulate tenant roles to WordPress roles
ROLE_MAP = {
    "owner": "administrator",
    "admin": "administrator",
    "editor": "editor",
    "viewer": "subscriber",
}


async def create_wp_user_for_tenant(
    wp_url: str,
    wp_admin_user: str,
    wp_admin_password: str,
    articulate_user_email: str,
    articulate_user_name: str,
    articulate_role: str,
) -> dict | None:
    """Create a WordPress user on a tenant site mapped to an Articulate user.

    Args:
        wp_url: Tenant's WordPress URL (internal Docker URL)
        wp_admin_user: Admin username for the tenant
        wp_admin_password: Admin app password for the tenant
        articulate_user_email: The Articulate user's email
        articulate_user_name: The Articulate user's display name
        articulate_role: Articulate tenant role (owner, admin, editor, viewer)

    Returns:
        Dict with wp_user_id, wp_role, wp_username, or None on failure
    """
    wp_role = ROLE_MAP.get(articulate_role, "subscriber")

    # Generate a username from email (prefix before @)
    username = f"art_{articulate_user_email.split('@')[0]}"

    try:
        async with httpx.AsyncClient(
            base_url=f"{wp_url}/wp-json/wp/v2",
            auth=(wp_admin_user, wp_admin_password),
            timeout=30.0,
        ) as client:
            # Check if user already exists by email
            response = await client.get(
                "/users",
                params={"search": articulate_user_email, "context": "edit"},
            )
            if response.status_code == 200:
                users = response.json()
                for u in users:
                    if u.get("email", "").lower() == articulate_user_email.lower():
                        # User exists, update role if needed
                        current_roles = u.get("roles", [])
                        if wp_role not in current_roles:
                            await client.post(
                                f"/users/{u['id']}",
                                json={"roles": [wp_role]},
                            )
                            logger.info(
                                "Updated existing WP user %s role to %s",
                                u["username"], wp_role,
                            )
                        return {
                            "wp_user_id": u["id"],
                            "wp_role": wp_role,
                            "wp_username": u["username"],
                        }

            # Create new user
            password = secrets.token_urlsafe(32)
            name_parts = articulate_user_name.split() if articulate_user_name else []

            response = await client.post("/users", json={
                "username": username,
                "email": articulate_user_email,
                "password": password,
                "roles": [wp_role],
                "first_name": name_parts[0] if name_parts else "",
                "last_name": " ".join(name_parts[1:]) if len(name_parts) > 1 else "",
            })

            if response.status_code in (200, 201):
                user = response.json()
                logger.info("Created WP user %s with role %s", username, wp_role)
                return {
                    "wp_user_id": user["id"],
                    "wp_role": wp_role,
                    "wp_username": user["username"],
                }
            else:
                error = {}
                if response.headers.get("content-type", "").startswith("application/json"):
                    error = response.json()
                logger.error(
                    "Failed to create WP user: %s %s",
                    response.status_code, error.get("message", ""),
                )
                return None

    except Exception as e:
        logger.error("Failed to sync WP user for %s: %s", articulate_user_email, e)
        return None


async def update_wp_user_role_for_tenant(
    wp_url: str,
    wp_admin_user: str,
    wp_admin_password: str,
    wp_user_id: int,
    new_articulate_role: str,
) -> bool:
    """Update a WordPress user's role when their Articulate tenant role changes."""
    wp_role = ROLE_MAP.get(new_articulate_role, "subscriber")

    try:
        async with httpx.AsyncClient(
            base_url=f"{wp_url}/wp-json/wp/v2",
            auth=(wp_admin_user, wp_admin_password),
            timeout=30.0,
        ) as client:
            response = await client.post(
                f"/users/{wp_user_id}",
                json={"roles": [wp_role]},
            )
            if response.status_code == 200:
                logger.info("Updated WP user %d role to %s", wp_user_id, wp_role)
                return True
            else:
                logger.error(
                    "Failed to update WP user role: %s", response.status_code,
                )
                return False
    except Exception as e:
        logger.error("Failed to update WP user role: %s", e)
        return False

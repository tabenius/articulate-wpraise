"""MCP tools for WordPress user management via REST API."""

import logging
import httpx
from mcp.server.fastmcp import FastMCP

from articulate_mcp.connection_manager import connection_manager
from articulate_mcp.context_helper import get_connection_info

logger = logging.getLogger("articulate-mcp")


async def _get_wp_rest_client(connection_id: int, user_id: int):
    """Get an httpx client configured for WordPress REST API."""
    connection = await connection_manager.get_connection(connection_id, user_id)
    if not connection:
        raise ValueError("Connection not found")

    wp_url = connection["wp_url"].rstrip("/")
    wp_user = connection["wp_user"]
    wp_pass = connection["wp_app_password"]

    return httpx.AsyncClient(
        base_url=f"{wp_url}/wp-json/wp/v2",
        auth=(wp_user, wp_pass),
        timeout=30.0,
    )


def register(mcp: FastMCP) -> None:
    """Register WordPress user management tools."""

    @mcp.tool()
    async def get_wp_users(
        role: str = "",
        search: str = "",
        per_page: int = 20,
        context=None,
    ) -> str:
        """List WordPress users on the connected site.

        Args:
            role: Filter by role (administrator, editor, author, contributor, subscriber)
            search: Search by username, email, or display name
            per_page: Number of results (max 100)
        """
        connection_id, user_id = get_connection_info(context)

        async with await _get_wp_rest_client(connection_id, user_id) as client:
            params = {"per_page": min(per_page, 100), "context": "edit"}
            if role:
                params["roles"] = role
            if search:
                params["search"] = search

            response = await client.get("/users", params=params)

            if response.status_code == 403:
                return "Error: Your WordPress user lacks the 'list_users' capability."
            response.raise_for_status()

            users = response.json()
            if not users:
                return "No WordPress users found."

            lines = [f"WordPress Users ({len(users)}):"]
            for u in users:
                roles = ", ".join(u.get("roles", []))
                lines.append(
                    f"  - {u['name']} ({u['username']}) "
                    f"| Email: {u['email']} "
                    f"| Roles: {roles} "
                    f"| ID: {u['id']}"
                )
            return "\n".join(lines)

    @mcp.tool()
    async def create_wp_user(
        username: str,
        email: str,
        password: str,
        role: str = "subscriber",
        first_name: str = "",
        last_name: str = "",
        context=None,
    ) -> str:
        """Create a new WordPress user on the connected site.

        Args:
            username: Login username
            email: Email address
            password: User password
            role: WordPress role (administrator, editor, author, contributor, subscriber)
            first_name: Optional first name
            last_name: Optional last name
        """
        connection_id, user_id = get_connection_info(context)

        valid_roles = {"administrator", "editor", "author", "contributor", "subscriber"}
        if role not in valid_roles:
            return f"Error: Invalid role '{role}'. Must be one of: {', '.join(sorted(valid_roles))}"

        async with await _get_wp_rest_client(connection_id, user_id) as client:
            payload = {
                "username": username,
                "email": email,
                "password": password,
                "roles": [role],
            }
            if first_name:
                payload["first_name"] = first_name
            if last_name:
                payload["last_name"] = last_name

            response = await client.post("/users", json=payload)

            if response.status_code == 403:
                return "Error: Your WordPress user lacks the 'create_users' capability."
            if response.status_code == 400:
                error = response.json()
                return f"Error: {error.get('message', 'Bad request')}"
            response.raise_for_status()

            user = response.json()
            return (
                f"Created WordPress user:\n"
                f"  Username: {user['username']}\n"
                f"  Email: {user['email']}\n"
                f"  Role: {role}\n"
                f"  ID: {user['id']}"
            )

    @mcp.tool()
    async def update_wp_user_role(
        wp_user_id: int,
        role: str,
        context=None,
    ) -> str:
        """Change a WordPress user's role.

        Args:
            wp_user_id: WordPress user ID
            role: New role (administrator, editor, author, contributor, subscriber)
        """
        connection_id, user_id = get_connection_info(context)

        valid_roles = {"administrator", "editor", "author", "contributor", "subscriber"}
        if role not in valid_roles:
            return f"Error: Invalid role '{role}'. Must be one of: {', '.join(sorted(valid_roles))}"

        async with await _get_wp_rest_client(connection_id, user_id) as client:
            response = await client.post(
                f"/users/{wp_user_id}",
                json={"roles": [role]},
            )

            if response.status_code == 403:
                return "Error: Your WordPress user lacks the 'promote_users' capability."
            if response.status_code == 404:
                return f"Error: WordPress user ID {wp_user_id} not found."
            response.raise_for_status()

            user = response.json()
            return (
                f"Updated WordPress user role:\n"
                f"  User: {user['username']} (ID: {user['id']})\n"
                f"  New role: {role}"
            )

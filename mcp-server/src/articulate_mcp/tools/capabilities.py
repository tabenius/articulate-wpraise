"""MCP tools for WordPress user capabilities and role management."""

import logging
from mcp.server.fastmcp import FastMCP

from articulate_mcp.graphql.client import get_graphql_client
from articulate_mcp.graphql.queries import GET_VIEWER_CAPABILITIES
from articulate_mcp.capability_checker import capability_checker, OPERATION_CAPABILITIES
from articulate_mcp.context_helper import get_connection_info

logger = logging.getLogger("articulate-mcp")


def register(mcp: FastMCP) -> None:
    """Register capability-related MCP tools."""

    @mcp.tool()
    async def get_wp_capabilities(context=None) -> str:
        """Get the current WordPress user's roles and capabilities.

        Returns the authenticated WordPress user's roles, capabilities,
        and what operations they can perform. Use this to understand
        what the current user is allowed to do on the WordPress site.
        """
        connection_id, user_id = get_connection_info(context)
        client = await get_graphql_client(connection_id, user_id)

        result = await client.query(
            GET_VIEWER_CAPABILITIES,
            use_cache=True,
            user_id=user_id,
        )

        viewer = result.get("viewer")
        if not viewer:
            return "Error: Could not fetch WordPress user info. Check connection credentials."

        roles = [node["name"] for node in viewer.get("roles", {}).get("nodes", [])]
        capabilities = sorted(capability_checker.get_capabilities_for_roles(roles))

        lines = [
            f"WordPress User: {viewer.get('username')} (ID: {viewer.get('databaseId')})",
            f"Email: {viewer.get('email')}",
            f"Roles: {', '.join(roles)}",
            "",
            f"Capabilities ({len(capabilities)}):",
        ]
        for cap in capabilities:
            lines.append(f"  - {cap}")

        lines.append("")
        lines.append("Available Operations:")
        for op, required_caps in sorted(OPERATION_CAPABILITIES.items()):
            allowed, missing = capability_checker.check(roles, required_caps)
            status = "+" if allowed else "-"
            lines.append(f"  {status} {op}")
            if not allowed:
                lines.append(f"    Missing: {', '.join(missing)}")

        return "\n".join(lines)

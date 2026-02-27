"""REST endpoints for WordPress capabilities."""

import logging
from starlette.responses import JSONResponse

from articulate_mcp.decorators import require_auth
from articulate_mcp.connection_manager import connection_manager
from articulate_mcp.graphql.client import get_graphql_client
from articulate_mcp.graphql.queries import GET_VIEWER_CAPABILITIES
from articulate_mcp.capability_checker import capability_checker

logger = logging.getLogger("articulate-mcp")


@require_auth
async def get_capabilities_endpoint(request):
    """Get WordPress capabilities for the user's active connection."""
    user = request.state.user

    connection = await connection_manager.get_active_connection(user["id"])
    if not connection:
        return JSONResponse(
            {"error": "No active WordPress connection"},
            status_code=400,
        )

    try:
        client = await get_graphql_client(connection["id"], user["id"])
        result = await client.query(
            GET_VIEWER_CAPABILITIES,
            use_cache=True,
            user_id=user["id"],
        )

        viewer = result.get("viewer")
        if not viewer:
            return JSONResponse(
                {"error": "Could not fetch WordPress user info"},
                status_code=502,
            )

        roles = [node["name"] for node in viewer.get("roles", {}).get("nodes", [])]
        capabilities = sorted(capability_checker.get_capabilities_for_roles(roles))

        return JSONResponse({
            "wp_user_id": viewer.get("databaseId"),
            "wp_username": viewer.get("username"),
            "wp_email": viewer.get("email"),
            "roles": roles,
            "capabilities": capabilities,
            "is_administrator": "administrator" in roles,
            "connection_id": connection["id"],
            "connection_name": connection["name"],
        })

    except Exception as e:
        logger.error("Failed to fetch capabilities: %s", e)
        return JSONResponse(
            {"error": f"Failed to fetch WordPress capabilities: {str(e)}"},
            status_code=502,
        )

"""Helper functions for extracting context from MCP tool calls."""

from typing import Any


def get_connection_info(context: Any | None) -> tuple[int, int]:
    """Extract connection_id and user_id from MCP context.

    Args:
        context: FastMCP context object or dict

    Returns:
        Tuple of (connection_id, user_id)

    Raises:
        ValueError: If connection info is missing from context
    """
    if context is None:
        raise ValueError("Context is required but not provided")

    # Handle both dict and object context
    if isinstance(context, dict):
        connection_id = context.get("connection_id")
        user_id = context.get("user_id")
    else:
        connection_id = getattr(context, "connection_id", None)
        user_id = getattr(context, "user_id", None)

    if connection_id is None or user_id is None:
        raise ValueError(
            f"Missing connection info in context: connection_id={connection_id}, user_id={user_id}"
        )

    return int(connection_id), int(user_id)


from articulate_mcp.capability_checker import capability_checker


def check_wp_capability(context, operation: str) -> tuple[bool, str]:
    """Check if the current user has WordPress capabilities for an operation.

    Returns (allowed, error_message). If allowed, error_message is empty.
    Does NOT block - returns a warning message that tools can include in output.
    """
    try:
        if isinstance(context, dict):
            wp_roles = context.get("wp_roles") or []
        else:
            wp_roles = getattr(context, "wp_roles", []) or []

        if not wp_roles:
            return True, ""  # No role info available, let WordPress handle it

        allowed, missing = capability_checker.check_operation(wp_roles, operation)
        if not allowed:
            role_str = ", ".join(wp_roles)
            missing_str = ", ".join(missing)
            return False, (
                f"Warning: Your WordPress role ({role_str}) may lack "
                f"the capabilities needed for this operation: {missing_str}. "
                f"The operation may fail on the WordPress side."
            )
        return True, ""
    except Exception:
        return True, ""  # On error, let WordPress handle authorization

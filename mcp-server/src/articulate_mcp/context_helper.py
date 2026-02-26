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

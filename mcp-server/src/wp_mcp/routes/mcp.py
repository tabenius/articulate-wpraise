"""MCP JSON-RPC endpoint for tool calls."""

from __future__ import annotations

import json as json_lib
import logging

from starlette.responses import JSONResponse as StarletteJSONResponse

logger = logging.getLogger(__name__)


async def mcp_jsonrpc_endpoint(request, mcp):
    """Handle JSON-RPC requests for MCP tools.

    Args:
        request: Starlette request object
        mcp: FastMCP instance
    """
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
                        data = json_lib.loads(text_content.text)
                        return StarletteJSONResponse({
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": {
                                "content": [{"type": "text", "text": text_content.text}]
                            }
                        })
                    except json_lib.JSONDecodeError:
                        # Not valid JSON, return as plain text
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

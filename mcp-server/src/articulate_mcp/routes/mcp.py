"""MCP JSON-RPC endpoint for tool calls."""

from __future__ import annotations

import json as json_lib
import logging

from starlette.responses import JSONResponse as StarletteJSONResponse

from articulate_mcp.connection_manager import connection_manager

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

        if method == "initialize":
            # Accept initialize handshake from clients like Cloudflare Playground
            logger.info("MCP initialize handshake from client: %s", body.get("clientInfo"))
            return StarletteJSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": params.get("protocolVersion", "2025-11-25"),
                    "capabilities": {"tools": True},
                    "serverInfo": {"name": "Articulate MCP Server"},
                }
            })

        if method == "tools/list":
            # List available tools
            tools = await mcp.list_tools()
            # Convert Tool objects to dicts for JSON serialization
            tools_list = []
            for tool in tools:
                if hasattr(tool, 'model_dump'):
                    tools_list.append(tool.model_dump())
                elif hasattr(tool, '__dict__'):
                    tools_list.append(tool.__dict__)
                else:
                    tools_list.append(tool)
            return StarletteJSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"tools": tools_list}
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

            # FastMCP returns a tuple: (content_list, parsed_data)
            # We need to extract the content from the first element
            if isinstance(result, tuple) and len(result) >= 1:
                content_list = result[0]
                # Check if content_list is a list with TextContent objects
                if isinstance(content_list, list) and len(content_list) > 0:
                    # Return ALL text content items
                    contents = []
                    for item in content_list:
                        if hasattr(item, 'text'):
                            contents.append({"type": "text", "text": item.text})
                    if contents:
                        return StarletteJSONResponse({
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": {
                                "content": contents
                            }
                        })

            # Handle ToolCallResult object with content attribute
            if hasattr(result, 'content') and result.content:
                text_content = result.content[0]
                if hasattr(text_content, 'text'):
                    return StarletteJSONResponse({
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "content": [{"type": "text", "text": text_content.text}]
                        }
                    })

            # Handle case where result is already a dict
            if isinstance(result, dict):
                result_json = json_lib.dumps(result)
                return StarletteJSONResponse({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": result_json}]
                    }
                })

            # Fallback: log error and return empty result
            logger.error(f"Unexpected result format from tool {tool_name}: {type(result)}, value: {result}")
            return StarletteJSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"content": [{"type": "text", "text": "{}"}]}
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


async def mcp_apikey_endpoint(request, mcp):
    """Handle MCP JSON-RPC requests authenticated via API key in URL path.

    Args:
        request: Starlette request object (with path param `api_key`)
        mcp: FastMCP instance
    """
    api_key = request.path_params.get("api_key")
    if not api_key:
        return StarletteJSONResponse(
            {"error": "API key required"}, status_code=401
        )

    # Look up connection by API key
    connection = await connection_manager.get_connection_by_api_key(api_key)
    if not connection:
        return StarletteJSONResponse(
            {"error": "Invalid API key"}, status_code=401
        )

    # Inject connection context into request scope (same as auth middleware does)
    request.scope["state"] = {
        "user": {"id": connection["user_id"]},
        "connection": connection,
    }

    logger.info(
        "MCP API key request: connection=%s, user_id=%s",
        connection["name"],
        connection["user_id"],
    )

    return await mcp_jsonrpc_endpoint(request, mcp)

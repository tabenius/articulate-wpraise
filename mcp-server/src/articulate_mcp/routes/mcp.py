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
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "Articulate MCP Server", "version": "0.0.1"},
                }
            })

        # Accept notifications (JSON-RPC notifications have no id and do not require a response)
        if method and method.startswith("notifications/"):
            logger.info("MCP notification received: %s", method)
            # Acknowledge notification with 200 OK and empty body
            return StarletteJSONResponse({}, status_code=200)

        if method == "tools/list":
            # List available tools
            tools = await mcp.list_tools()
            # Convert Tool objects to normalized dicts for JSON serialization and client schema
            tools_list = []
            for tool in tools:
                # Get raw dict representation
                if hasattr(tool, 'model_dump'):
                    raw = tool.model_dump()
                elif hasattr(tool, '__dict__'):
                    raw = dict(tool.__dict__)
                elif isinstance(tool, dict):
                    raw = dict(tool)
                else:
                    raw = {"name": str(tool)}

                # Normalize fields to types expected by clients (avoid nulls/None)
                name = raw.get("name") or raw.get("id") or raw.get("title") or "unnamed_tool"
                title = raw.get("title") if isinstance(raw.get("title"), str) else name
                description = raw.get("description") if isinstance(raw.get("description"), str) else ""
                input_schema = raw.get("inputSchema") if isinstance(raw.get("inputSchema"), dict) else {}
                output_schema = raw.get("outputSchema") if isinstance(raw.get("outputSchema"), dict) else {}
                icons = raw.get("icons") if isinstance(raw.get("icons"), list) else []
                annotations = raw.get("annotations") if isinstance(raw.get("annotations"), dict) else {}
                meta = raw.get("meta") if isinstance(raw.get("meta"), dict) else {}
                execution = raw.get("execution") if isinstance(raw.get("execution"), dict) else {"type": "jsonrpc", "method": "tools/call", "name": name}

                tool_dict = {
                    "name": name,
                    "title": title,
                    "description": description,
                    "inputSchema": input_schema,
                    "outputSchema": output_schema,
                    "icons": icons,
                    "annotations": annotations,
                    "meta": meta,
                    "execution": execution,
                }
                tools_list.append(tool_dict)

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
    # Support basic GET for health/status checks to avoid 405 from some clients
    if request.method == "GET":
        api_key = request.path_params.get("api_key")
        if not api_key:
            return StarletteJSONResponse({"error": "API key required"}, status_code=401)
        connection = await connection_manager.get_connection_by_api_key(api_key)
        if not connection:
            return StarletteJSONResponse({"error": "Invalid API key"}, status_code=401)
        return StarletteJSONResponse({"status": "ok", "connection": {"id": connection.get("id"), "name": connection.get("name")}}, status_code=200)

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

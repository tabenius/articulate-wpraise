#!/usr/bin/env python3
"""Generate JSON schemas for all MCP tools."""

import json
import sys
from pathlib import Path

# Add parent directory to path to import wp_mcp
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp.server.fastmcp import FastMCP


def generate_schemas():
    """Generate JSON schemas for all registered MCP tools."""
    # Create a temporary FastMCP instance to extract tool schemas
    mcp = FastMCP("schema-generator")

    # Import and register all tools
    from wp_mcp.tools import (
        posts,
        blocks,
        media,
        taxonomies,
        menus,
        settings,
    )

    posts.register(mcp)
    blocks.register(mcp)
    media.register(mcp)
    taxonomies.register(mcp)
    menus.register(mcp)
    settings.register(mcp)

    # Extract tool schemas
    tools_schema = {
        "version": "1.0.0",
        "tools": {}
    }

    # Get all registered tools
    for tool in mcp._tool_manager._tools.values():
        tool_name = tool.name

        # Get the input schema
        input_schema = tool.inputSchema if hasattr(tool, 'inputSchema') else {}

        # Create a response schema based on the tool's description
        # We'll need to manually define these based on what each tool returns
        response_schema = get_response_schema(tool_name)

        tools_schema["tools"][tool_name] = {
            "description": tool.description if hasattr(tool, 'description') else "",
            "input": input_schema,
            "output": response_schema
        }

    return tools_schema


def get_response_schema(tool_name: str) -> dict:
    """Get the response schema for a tool based on its implementation."""

    # Define response schemas for all tools
    schemas = {
        "get_posts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "title": {"type": "string"},
                    "slug": {"type": ["string", "null"]},
                    "status": {"type": "string"},
                    "type": {"type": "string"},
                    "date": {"type": "string"},
                    "modified": {"type": "string"},
                    "excerpt": {"type": "string"},
                    "author": {"type": "string"},
                    "featuredImage": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "url": {"type": "string"},
                            "altText": {"type": "string"},
                            "width": {"type": ["integer", "null"]},
                            "height": {"type": ["integer", "null"]}
                        }
                    }
                },
                "required": ["id", "title", "slug", "status", "type", "date"]
            }
        },
        "get_post": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "title": {"type": "string"},
                "slug": {"type": ["string", "null"]},
                "status": {"type": "string"},
                "content": {"type": ["string", "null"]},
                "date": {"type": "string"},
                "modified": {"type": "string"},
                "author": {"type": "string"},
                "featuredImage": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "url": {"type": "string"},
                        "altText": {"type": "string"},
                        "width": {"type": ["integer", "null"]},
                        "height": {"type": ["integer", "null"]}
                    }
                },
                "categories": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "name": {"type": "string"},
                            "slug": {"type": "string"}
                        }
                    }
                },
                "tags": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "name": {"type": "string"},
                            "slug": {"type": "string"}
                        }
                    }
                }
            },
            "required": ["id", "title", "slug", "status"]
        },
        "create_post": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "title": {"type": "string"},
                "slug": {"type": ["string", "null"]},
                "status": {"type": "string"},
                "content": {"type": ["string", "null"]},
                "date": {"type": "string"},
                "modified": {"type": "string"},
                "author": {"type": "string"}
            },
            "required": ["id", "title", "slug", "status"]
        },
        "update_post": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "title": {"type": "string"},
                "slug": {"type": ["string", "null"]},
                "status": {"type": "string"},
                "content": {"type": ["string", "null"]},
                "date": {"type": "string"},
                "modified": {"type": "string"},
                "author": {"type": "string"}
            },
            "required": ["id", "title", "slug", "status"]
        },
        "delete_post": {
            "type": "object",
            "properties": {
                "deleted": {"type": "boolean"},
                "id": {"type": ["integer", "null"]},
                "title": {"type": ["string", "null"]}
            },
            "required": ["deleted"]
        }
    }

    return schemas.get(tool_name, {"type": "object"})


if __name__ == "__main__":
    schemas = generate_schemas()
    print(json.dumps(schemas, indent=2))

"""WordPress MCP Server entry point.

Exposes WordPress content management tools via the Model Context Protocol.
Supports HTTP/SSE transport for Docker deployment.
"""

from __future__ import annotations

import logging
import sys

from mcp.server.fastmcp import FastMCP

from wp_mcp.config import config
from wp_mcp.tools import posts, pages, blocks, media, search

# Configure logging to stderr (required for MCP servers)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("wp-mcp")

# Initialize MCP server
mcp = FastMCP(
    "WordPress MCP Server",
    instructions=(
        "This server provides tools for managing WordPress content via WPGraphQL. "
        "You can create, read, update, and delete posts and pages. "
        "You can also manipulate individual blocks within posts, including "
        "inserting, removing, moving, and updating blocks. "
        "Block types include: core/paragraph, core/heading, core/image, "
        "core/list, core/quote, core/code, core/columns, core/group, "
        "core/buttons, core/spacer, core/separator, and more."
    ),
)

# Register all tool modules
posts.register(mcp)
pages.register(mcp)
blocks.register(mcp)
media.register(mcp)
search.register(mcp)

logger.info("WordPress MCP Server initialized")
logger.info("Transport: %s", config.mcp_transport)
logger.info("WordPress URL: %s", config.wp_url)


def main() -> None:
    """Run the MCP server."""
    transport = config.mcp_transport

    if transport == "streamable-http":
        mcp.run(
            transport="streamable-http",
            host=config.mcp_host,
            port=config.mcp_port,
        )
    elif transport == "sse":
        mcp.run(
            transport="sse",
            host=config.mcp_host,
            port=config.mcp_port,
        )
    else:
        # Default to stdio for local development
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

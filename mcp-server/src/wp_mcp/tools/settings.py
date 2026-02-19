"""WordPress settings management tools."""

from typing import Any
from mcp.server.fastmcp import FastMCP
from wp_mcp.config import config


async def get_front_page_settings() -> dict[str, Any]:
    """Get current front page settings."""
    from wp_mcp.graphql.client import GraphQLClient

    query = """
    query GetFrontPageSettings {
      generalSettings {
        url
      }
      allSettings {
        readingSettingsShowOnFront
        readingSettingsPageOnFront
        readingSettingsPageForPosts
      }
    }
    """

    client = GraphQLClient(
        endpoint=config.wp_graphql_endpoint,
        auth=config.wp_auth,
    )

    try:
        result = await client.execute(query)
        settings = result.get("allSettings", {})

        return {
            "show_on_front": settings.get("readingSettingsShowOnFront", "posts"),
            "page_on_front": settings.get("readingSettingsPageOnFront"),
            "page_for_posts": settings.get("readingSettingsPageForPosts"),
        }
    except Exception as e:
        return {"error": str(e)}


async def set_front_page(page_id: int) -> dict[str, Any]:
    """Set a page as the site's front page.

    Args:
        page_id: The ID of the page to set as front page

    Returns:
        Dictionary with success status and updated settings
    """
    from wp_mcp.graphql.client import GraphQLClient

    # First, we need to update WordPress options via REST API
    # since WPGraphQL doesn't support updating general settings
    import httpx

    try:
        # Use WordPress REST API to update options
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Update show_on_front to 'page'
            response1 = await client.post(
                f"{config.wp_url}/wp-json/wp/v2/settings",
                auth=config.wp_auth,
                json={"show_on_front": "page", "page_on_front": page_id},
            )
            response1.raise_for_status()

            return {
                "success": True,
                "page_id": page_id,
                "message": f"Page {page_id} set as front page",
            }
    except Exception as e:
        return {"error": str(e), "success": False}


async def unset_front_page() -> dict[str, Any]:
    """Unset the front page (show posts on front page instead)."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{config.wp_url}/wp-json/wp/v2/settings",
                auth=config.wp_auth,
                json={"show_on_front": "posts", "page_on_front": 0},
            )
            response.raise_for_status()

            return {
                "success": True,
                "message": "Front page unset, showing posts on homepage",
            }
    except Exception as e:
        return {"error": str(e), "success": False}


def register(mcp: FastMCP) -> None:
    """Register settings-related tools with the MCP server."""
    mcp.tool()(get_front_page_settings)
    mcp.tool()(set_front_page)
    mcp.tool()(unset_front_page)

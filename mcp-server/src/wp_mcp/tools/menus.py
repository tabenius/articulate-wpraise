"""WordPress menu management tools."""

from typing import Any
from mcp.server.fastmcp import FastMCP
from wp_mcp.config import config


async def list_menus() -> dict[str, Any]:
    """List all WordPress menus."""
    from wp_mcp.graphql.client import GraphQLClient

    query = """
    query GetMenus {
      menus {
        nodes {
          id
          databaseId
          name
          slug
          locations
          count
        }
      }
    }
    """

    client = GraphQLClient(
        endpoint=config.wp_graphql_endpoint,
        auth=config.wp_auth,
    )

    try:
        result = await client.execute(query)
        menus = result.get("menus", {}).get("nodes", [])

        return {"success": True, "menus": menus, "count": len(menus)}
    except Exception as e:
        return {"error": str(e), "success": False}


async def get_menu_items(menu_id: int) -> dict[str, Any]:
    """Get items in a specific menu.

    Args:
        menu_id: Database ID of the menu

    Returns:
        Dictionary with menu items
    """
    from wp_mcp.graphql.client import GraphQLClient

    query = """
    query GetMenuItems($id: ID!) {
      menu(id: $id, idType: DATABASE_ID) {
        id
        name
        menuItems {
          nodes {
            id
            databaseId
            label
            url
            parentId
            order
            connectedNode {
              node {
                ... on Page {
                  id
                  databaseId
                  title
                }
                ... on Post {
                  id
                  databaseId
                  title
                }
              }
            }
          }
        }
      }
    }
    """

    client = GraphQLClient(
        endpoint=config.wp_graphql_endpoint,
        auth=config.wp_auth,
    )

    try:
        result = await client.execute(query, {"id": menu_id})
        menu = result.get("menu")

        if not menu:
            return {"error": "Menu not found", "success": False}

        return {
            "success": True,
            "menu": {
                "id": menu.get("id"),
                "name": menu.get("name"),
                "items": menu.get("menuItems", {}).get("nodes", []),
            },
        }
    except Exception as e:
        return {"error": str(e), "success": False}


async def add_page_to_menu(page_id: int, menu_id: int, label: str | None = None) -> dict[str, Any]:
    """Add a page to a WordPress menu.

    Args:
        page_id: Database ID of the page to add
        menu_id: Database ID of the menu
        label: Optional custom label (defaults to page title)

    Returns:
        Dictionary with success status
    """
    import httpx

    try:
        # Use WordPress REST API for menu management
        # First, get the page title if no label provided
        if not label:
            async with httpx.AsyncClient(timeout=30.0) as client:
                page_response = await client.get(
                    f"{config.wp_url}/wp-json/wp/v2/pages/{page_id}",
                    auth=config.wp_auth,
                )
                page_response.raise_for_status()
                page_data = page_response.json()
                label = page_data.get("title", {}).get("rendered", f"Page {page_id}")

        # Add menu item via REST API
        async with httpx.AsyncClient(timeout=30.0) as client:
            # WordPress doesn't have a direct REST endpoint for menus in core
            # We'll use the legacy wp-json endpoint or WP-REST-API v2 plugin
            # For now, we'll create the menu item directly
            menu_item_data = {
                "title": label,
                "object": "page",
                "object_id": page_id,
                "menu_order": 0,
                "type": "post_type",
                "status": "publish",
                "menus": menu_id,
            }

            response = await client.post(
                f"{config.wp_url}/wp-json/wp/v2/menu-items",
                auth=config.wp_auth,
                json=menu_item_data,
            )

            if response.status_code == 201:
                result = response.json()
                return {
                    "success": True,
                    "menu_item_id": result.get("id"),
                    "message": f"Page '{label}' added to menu",
                }
            else:
                # Try alternative approach using direct database
                return {
                    "success": False,
                    "error": "WordPress REST API does not support menu items by default. Please install WP REST API Menus plugin.",
                    "note": "Alternative: Use WordPress admin to add page to menu manually",
                }
    except Exception as e:
        return {"error": str(e), "success": False}


async def remove_page_from_menu(page_id: int, menu_id: int) -> dict[str, Any]:
    """Remove a page from a WordPress menu.

    Args:
        page_id: Database ID of the page
        menu_id: Database ID of the menu

    Returns:
        Dictionary with success status
    """
    import httpx

    try:
        # First, find the menu item for this page
        menu_items = await get_menu_items(menu_id)
        if not menu_items.get("success"):
            return menu_items

        # Find the menu item ID for this page
        menu_item_id = None
        for item in menu_items.get("menu", {}).get("items", []):
            connected = item.get("connectedNode", {}).get("node", {})
            if connected.get("databaseId") == page_id:
                menu_item_id = item.get("databaseId")
                break

        if not menu_item_id:
            return {
                "success": False,
                "error": f"Page {page_id} not found in menu {menu_id}",
            }

        # Delete the menu item
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{config.wp_url}/wp-json/wp/v2/menu-items/{menu_item_id}",
                auth=config.wp_auth,
            )

            if response.status_code in [200, 204]:
                return {
                    "success": True,
                    "message": f"Page removed from menu",
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to remove menu item. Ensure WP REST API Menus plugin is installed.",
                }
    except Exception as e:
        return {"error": str(e), "success": False}


def register(mcp: FastMCP) -> None:
    """Register menu-related tools with the MCP server."""
    mcp.tool()(list_menus)
    mcp.tool()(get_menu_items)
    mcp.tool()(add_page_to_menu)
    mcp.tool()(remove_page_from_menu)

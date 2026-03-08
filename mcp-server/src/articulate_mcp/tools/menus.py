"""WordPress menu management tools."""

from __future__ import annotations

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from articulate_mcp.context_helper import get_connection_info, check_wp_capability
from articulate_mcp.graphql.client import get_graphql_client

logger = logging.getLogger(__name__)


def register(mcp: FastMCP) -> None:
    """Register menu-related tools with the MCP server."""

    @mcp.tool()
    async def list_menus(context: dict | None = None) -> dict[str, Any]:
        """List all WordPress menus.

        Returns:
            Dictionary with menus list and count.
        """
        connection_id, user_id = get_connection_info(context)
        client = await get_graphql_client(connection_id, user_id)

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

        try:
            result = await client.query(query, user_id=user_id)
            menus = result.get("menus", {}).get("nodes", [])
            return {"success": True, "menus": menus, "count": len(menus)}
        except Exception as e:
            logger.error("list_menus failed: %s", e)
            return {"error": str(e), "success": False}

    @mcp.tool()
    async def get_menu_items(menu_id: int, context: dict | None = None) -> dict[str, Any]:
        """Get items in a specific menu.

        Args:
            menu_id: Database ID of the menu

        Returns:
            Dictionary with menu items.
        """
        connection_id, user_id = get_connection_info(context)
        client = await get_graphql_client(connection_id, user_id)

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

        try:
            result = await client.query(query, variables={"id": menu_id}, user_id=user_id)
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
            logger.error("get_menu_items failed: %s", e)
            return {"error": str(e), "success": False}

    @mcp.tool()
    async def add_page_to_menu(
        page_id: int,
        menu_id: int,
        label: str | None = None,
        context: dict | None = None,
    ) -> dict[str, Any]:
        """Add a page to a WordPress menu.

        Args:
            page_id: Database ID of the page to add
            menu_id: Database ID of the menu
            label: Optional custom label (defaults to page title)

        Returns:
            Dictionary with success status.
        """
        allowed, warning = check_wp_capability(context, "manage_menus")
        if not allowed:
            return {"error": warning, "success": False}

        connection_id, user_id = get_connection_info(context)
        client = await get_graphql_client(connection_id, user_id)

        import httpx

        try:
            # Get the page title if no label provided
            if not label:
                page_query = """
                query GetPageTitle($id: ID!) {
                  page(id: $id, idType: DATABASE_ID) {
                    title
                  }
                }
                """
                page_result = await client.query(
                    page_query, variables={"id": page_id}, user_id=user_id
                )
                page = page_result.get("page")
                label = page.get("title", f"Page {page_id}") if page else f"Page {page_id}"

            # Get connection details for REST API call
            from articulate_mcp.connection_manager import connection_manager
            conn = await connection_manager.get_connection(connection_id, user_id)
            if not conn:
                return {"error": "Connection not found", "success": False}

            wp_url = conn["wp_url"]
            wp_auth = (conn["wp_user"], conn["wp_app_password"])

            menu_item_data = {
                "title": label,
                "object": "page",
                "object_id": page_id,
                "menu_order": 0,
                "type": "post_type",
                "status": "publish",
                "menus": menu_id,
            }

            async with httpx.AsyncClient(timeout=30.0) as http:
                response = await http.post(
                    f"{wp_url}/wp-json/wp/v2/menu-items",
                    auth=wp_auth,
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
                    return {
                        "success": False,
                        "error": "WordPress REST API does not support menu items by default. Please install WP REST API Menus plugin.",
                    }
        except Exception as e:
            logger.error("add_page_to_menu failed: %s", e)
            return {"error": str(e), "success": False}

    @mcp.tool()
    async def remove_page_from_menu(
        page_id: int,
        menu_id: int,
        context: dict | None = None,
    ) -> dict[str, Any]:
        """Remove a page from a WordPress menu.

        Args:
            page_id: Database ID of the page
            menu_id: Database ID of the menu

        Returns:
            Dictionary with success status.
        """
        allowed, warning = check_wp_capability(context, "manage_menus")
        if not allowed:
            return {"error": warning, "success": False}

        connection_id, user_id = get_connection_info(context)

        try:
            # Find the menu item for this page
            menu_items = await get_menu_items(menu_id, context=context)
            if not menu_items.get("success"):
                return menu_items

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

            # Get connection details for REST API call
            from articulate_mcp.connection_manager import connection_manager
            conn = await connection_manager.get_connection(connection_id, user_id)
            if not conn:
                return {"error": "Connection not found", "success": False}

            wp_url = conn["wp_url"]
            wp_auth = (conn["wp_user"], conn["wp_app_password"])

            import httpx

            async with httpx.AsyncClient(timeout=30.0) as http:
                response = await http.delete(
                    f"{wp_url}/wp-json/wp/v2/menu-items/{menu_item_id}",
                    auth=wp_auth,
                )

                if response.status_code in [200, 204]:
                    return {
                        "success": True,
                        "message": "Page removed from menu",
                    }
                else:
                    return {
                        "success": False,
                        "error": "Failed to remove menu item. Ensure WP REST API Menus plugin is installed.",
                    }
        except Exception as e:
            logger.error("remove_page_from_menu failed: %s", e)
            return {"error": str(e), "success": False}

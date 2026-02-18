"""MCP tools for WordPress page operations."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from wp_mcp.graphql.client import get_graphql_client
from wp_mcp.graphql.queries import GET_PAGE, GET_PAGES
from wp_mcp.graphql.mutations import CREATE_PAGE, UPDATE_PAGE
from wp_mcp.context_helper import get_connection_info


def register(mcp: FastMCP) -> None:
    """Register page-related tools with the MCP server."""

    @mcp.tool()
    async def get_pages(per_page: int = 10, context: dict | None = None) -> list[dict[str, Any]]:
        """List WordPress pages.

        Args:
            per_page: Number of pages to return (max 100).

        Returns:
            List of page objects with id, title, slug, status, date.
        """
        connection_id, user_id = get_connection_info(context)
        client = await get_graphql_client(connection_id, user_id)

        data = await client.query(
            GET_PAGES,
            variables={"first": min(per_page, 100)},
            user_id=user_id,
        )
        pages = data.get("pages", {}).get("nodes", [])
        return [_format_page(p) for p in pages]

    @mcp.tool()
    async def get_page(page_id: int, context: dict | None = None) -> dict[str, Any]:
        """Get a WordPress page by database ID.

        Args:
            page_id: The WordPress database ID of the page.

        Returns:
            Page object with id, title, slug, status, content, date.
        """
        connection_id, user_id = get_connection_info(context)
        client = await get_graphql_client(connection_id, user_id)

        data = await client.query(
            GET_PAGE,
            variables={"id": str(page_id)},
            user_id=user_id,
        )
        page = data.get("page")
        if not page:
            return {"error": f"Page {page_id} not found"}
        return _format_page(page)

    @mcp.tool()
    async def create_page(
        title: str,
        content: str = "",
        status: str = "draft",
        context: dict | None = None,
    ) -> dict[str, Any]:
        """Create a new WordPress page.

        Args:
            title: The page title.
            content: The page content in WordPress block format.
            status: Page status (draft, publish). Default: draft.

        Returns:
            The created page object.
        """
        connection_id, user_id = get_connection_info(context)
        client = await get_graphql_client(connection_id, user_id)

        input_data: dict[str, Any] = {
            "title": title,
            "content": content,
            "status": status.upper(),
        }
        data = await client.mutate(
            CREATE_PAGE,
            variables={"input": input_data},
        )
        page = data.get("createPage", {}).get("page")
        if not page:
            return {"error": "Failed to create page"}
        return _format_page(page)

    @mcp.tool()
    async def update_page(
        page_id: int,
        title: str | None = None,
        content: str | None = None,
        status: str | None = None,
        context: dict | None = None,
    ) -> dict[str, Any]:
        """Update an existing WordPress page.

        Args:
            page_id: The WordPress database ID of the page.
            title: New title (optional).
            content: New content in WordPress block format (optional).
            status: New status (optional).

        Returns:
            The updated page object.
        """
        connection_id, user_id = get_connection_info(context)
        client = await get_graphql_client(connection_id, user_id)

        input_data: dict[str, Any] = {"id": str(page_id)}
        if title is not None:
            input_data["title"] = title
        if content is not None:
            input_data["content"] = content
        if status is not None:
            input_data["status"] = status.upper()

        data = await client.mutate(
            UPDATE_PAGE,
            variables={"input": input_data},
        )
        page = data.get("updatePage", {}).get("page")
        if not page:
            return {"error": f"Failed to update page {page_id}"}
        return _format_page(page)


def _format_page(page: dict[str, Any]) -> dict[str, Any]:
    """Format a page object for consistent output."""
    return {
        "id": page.get("databaseId"),
        "title": page.get("title", ""),
        "slug": page.get("slug", ""),
        "status": page.get("status", "").lower(),
        "content": page.get("content", ""),
        "date": page.get("date", ""),
        "modified": page.get("modified", ""),
    }

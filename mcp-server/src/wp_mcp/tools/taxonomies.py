"""MCP tools for WordPress taxonomy operations (categories, tags)."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from wp_mcp.graphql.client import gql_client
from wp_mcp.graphql.queries import GET_CATEGORIES, GET_TAGS
from wp_mcp.graphql.mutations import CREATE_CATEGORY, CREATE_TAG


def register(mcp: FastMCP) -> None:
    """Register taxonomy-related tools with the MCP server."""

    @mcp.tool()
    async def get_categories(per_page: int = 100) -> list[dict[str, Any]]:
        """List WordPress categories.

        Args:
            per_page: Number of categories to return (max 100).

        Returns:
            List of category objects with id, name, slug, description, count.
        """
        data = await gql_client.query(
            GET_CATEGORIES,
            variables={"first": min(per_page, 100)},
        )
        categories = data.get("categories", {}).get("nodes", [])
        return [_format_term(c) for c in categories]

    @mcp.tool()
    async def get_tags(per_page: int = 100) -> list[dict[str, Any]]:
        """List WordPress tags.

        Args:
            per_page: Number of tags to return (max 100).

        Returns:
            List of tag objects with id, name, slug, description, count.
        """
        data = await gql_client.query(
            GET_TAGS,
            variables={"first": min(per_page, 100)},
        )
        tags = data.get("tags", {}).get("nodes", [])
        return [_format_term(t) for t in tags]

    @mcp.tool()
    async def create_category(
        name: str,
        description: str = "",
    ) -> dict[str, Any]:
        """Create a new WordPress category.

        Args:
            name: The category name.
            description: Optional description for the category.

        Returns:
            The created category object with id, name, slug.
        """
        input_data: dict[str, Any] = {"name": name}
        if description:
            input_data["description"] = description

        data = await gql_client.mutate(
            CREATE_CATEGORY,
            variables={"input": input_data},
        )
        category = data.get("createCategory", {}).get("category")
        if not category:
            return {"error": "Failed to create category"}
        return _format_term(category)

    @mcp.tool()
    async def create_tag(
        name: str,
        description: str = "",
    ) -> dict[str, Any]:
        """Create a new WordPress tag.

        Args:
            name: The tag name.
            description: Optional description for the tag.

        Returns:
            The created tag object with id, name, slug.
        """
        input_data: dict[str, Any] = {"name": name}
        if description:
            input_data["description"] = description

        data = await gql_client.mutate(
            CREATE_TAG,
            variables={"input": input_data},
        )
        tag = data.get("createTag", {}).get("tag")
        if not tag:
            return {"error": "Failed to create tag"}
        return _format_term(tag)


def _format_term(term: dict[str, Any]) -> dict[str, Any]:
    """Format a taxonomy term for consistent output."""
    return {
        "id": term.get("databaseId"),
        "name": term.get("name", ""),
        "slug": term.get("slug", ""),
        "description": term.get("description", ""),
        "count": term.get("count", 0),
    }

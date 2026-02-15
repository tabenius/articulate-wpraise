"""MCP tools for WordPress content search."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from wp_mcp.graphql.client import gql_client
from wp_mcp.graphql.queries import SEARCH_CONTENT


def register(mcp: FastMCP) -> None:
    """Register search-related tools with the MCP server."""

    @mcp.tool()
    async def search_content(
        query: str,
        content_type: str = "all",
        per_page: int = 10,
    ) -> dict[str, Any]:
        """Search WordPress content (posts and pages) by keyword.

        Args:
            query: Search term to look for in titles and content.
            content_type: Type to search: "post", "page", or "all". Default: all.
            per_page: Number of results per type (max 100).

        Returns:
            Search results grouped by type, each with id, title, excerpt.
        """
        data = await gql_client.query(
            SEARCH_CONTENT,
            variables={"search": query, "first": min(per_page, 100)},
        )

        results: dict[str, Any] = {"query": query, "results": []}

        if content_type in ("post", "all"):
            posts = data.get("posts", {}).get("nodes", [])
            for p in posts:
                results["results"].append({
                    "type": "post",
                    "id": p.get("databaseId"),
                    "title": p.get("title", ""),
                    "excerpt": p.get("excerpt", ""),
                    "status": p.get("status", "").lower(),
                })

        if content_type in ("page", "all"):
            pages = data.get("pages", {}).get("nodes", [])
            for p in pages:
                results["results"].append({
                    "type": "page",
                    "id": p.get("databaseId"),
                    "title": p.get("title", ""),
                    "excerpt": p.get("excerpt", ""),
                    "status": p.get("status", "").lower(),
                })

        results["totalResults"] = len(results["results"])
        return results

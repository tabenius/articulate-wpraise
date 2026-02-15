"""MCP tools for WordPress media library operations."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from wp_mcp.graphql.client import gql_client
from wp_mcp.graphql.queries import GET_MEDIA, GET_MEDIA_ITEM


def register(mcp: FastMCP) -> None:
    """Register media-related tools with the MCP server."""

    @mcp.tool()
    async def get_media(per_page: int = 10) -> list[dict[str, Any]]:
        """List media items from the WordPress media library.

        Args:
            per_page: Number of media items to return (max 100).

        Returns:
            List of media objects with id, title, url, alt text, dimensions.
        """
        data = await gql_client.query(
            GET_MEDIA,
            variables={"first": min(per_page, 100)},
        )
        items = data.get("mediaItems", {}).get("nodes", [])
        return [_format_media(m) for m in items]

    @mcp.tool()
    async def get_media_item(media_id: int) -> dict[str, Any]:
        """Get a single media item with URL, alt text, and dimensions.

        Args:
            media_id: The WordPress database ID of the media item.

        Returns:
            Media object with id, title, url, alt, dimensions, mime type.
        """
        data = await gql_client.query(
            GET_MEDIA_ITEM,
            variables={"id": str(media_id)},
        )
        item = data.get("mediaItem")
        if not item:
            return {"error": f"Media item {media_id} not found"}
        return _format_media(item)


def _format_media(media: dict[str, Any]) -> dict[str, Any]:
    """Format a media item for consistent output."""
    details = media.get("mediaDetails", {}) or {}
    return {
        "id": media.get("databaseId"),
        "title": media.get("title", ""),
        "url": media.get("sourceUrl", ""),
        "alt": media.get("altText", ""),
        "caption": media.get("caption", ""),
        "mimeType": media.get("mimeType", ""),
        "width": details.get("width"),
        "height": details.get("height"),
        "file": details.get("file", ""),
        "date": media.get("date", ""),
    }

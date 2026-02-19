"""MCP tools for WordPress media library operations."""

from __future__ import annotations

from typing import Any
import httpx
import base64
import re

from mcp.server.fastmcp import FastMCP

from wp_mcp.graphql.client import gql_client
from wp_mcp.graphql.queries import GET_MEDIA, GET_MEDIA_ITEM
from wp_mcp.config import config


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

    @mcp.tool()
    async def upload_media(
        file_url: str,
        title: str = "",
        alt_text: str = "",
    ) -> dict[str, Any]:
        """Upload a media file to WordPress from a URL or data URI.

        Args:
            file_url: URL of the file to download and upload, or data URI (base64).
            title: Title for the media item (optional).
            alt_text: Alt text for the image (optional).

        Returns:
            Uploaded media object with id, url, and dimensions.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Check if this is a data URL (base64 encoded)
            data_url_match = re.match(r"data:([^;]+);base64,(.+)", file_url)

            if data_url_match:
                # Handle data URL (direct file upload)
                try:
                    content_type = data_url_match.group(1)
                    base64_data = data_url_match.group(2)
                    file_content = base64.b64decode(base64_data)

                    # Determine filename from content type
                    ext_map = {
                        "image/jpeg": ".jpg",
                        "image/png": ".png",
                        "image/gif": ".gif",
                        "image/webp": ".webp",
                        "image/svg+xml": ".svg",
                    }
                    ext = ext_map.get(content_type, ".jpg")
                    filename = f"upload{ext}"

                except Exception as e:
                    return {"error": f"Failed to decode base64 data: {str(e)}"}
            else:
                # Download the file from the URL
                try:
                    response = await client.get(file_url)
                    response.raise_for_status()
                    file_content = response.content

                    # Determine filename and content type
                    filename = file_url.split("/")[-1].split("?")[0] or "upload.jpg"
                    content_type = response.headers.get("content-type", "image/jpeg")

                except Exception as e:
                    return {"error": f"Failed to download file: {str(e)}"}

            # Upload to WordPress REST API
            try:
                files = {"file": (filename, file_content, content_type)}
                headers: dict[str, str] = {}
                data: dict[str, str] = {}

                if title:
                    data["title"] = title
                if alt_text:
                    data["alt_text"] = alt_text

                wp_auth = config.wp_auth
                if not wp_auth:
                    return {"error": "WordPress authentication not configured"}

                upload_url = f"{config.wp_url}/wp-json/wp/v2/media"
                upload_response = await client.post(
                    upload_url,
                    files=files,
                    data=data,
                    headers=headers,
                    auth=wp_auth,
                )
                upload_response.raise_for_status()

                result = upload_response.json()

                # Format response to match our media format
                return {
                    "id": result.get("id"),
                    "title": result.get("title", {}).get("rendered", ""),
                    "url": result.get("source_url", ""),
                    "alt": result.get("alt_text", ""),
                    "width": result.get("media_details", {}).get("width"),
                    "height": result.get("media_details", {}).get("height"),
                    "mimeType": result.get("mime_type", ""),
                }

            except httpx.HTTPStatusError as e:
                return {"error": f"Upload failed: {e.response.status_code} - {e.response.text}"}
            except Exception as e:
                return {"error": f"Upload failed: {str(e)}"}


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

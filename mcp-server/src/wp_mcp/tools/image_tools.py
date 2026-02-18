"""MCP tools for image compression and optimization."""

from __future__ import annotations

from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from wp_mcp.graphql.client import get_graphql_client
from wp_mcp.context_helper import get_connection_info
from wp_mcp.image_compressor import ImageCompressor
import httpx
import logging

logger = logging.getLogger(__name__)


def register(mcp: FastMCP) -> None:
    """Register image-related tools with the MCP server."""

    @mcp.tool()
    async def compress_wordpress_image(
        image_url: str,
        output_format: str = "webp",
        quality: int = 85,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None,
        context: dict | None = None,
    ) -> dict[str, Any]:
        """Compress a WordPress media library image.

        Args:
            image_url: URL of the WordPress image to compress
            output_format: Target format (webp, avif, jpeg, png)
            quality: Quality setting (1-100)
            max_width: Maximum width (optional)
            max_height: Maximum height (optional)

        Returns:
            Compression result with metadata and download URL
        """
        if not ImageCompressor.is_available():
            return {"error": "Image compression not available (Pillow not installed)"}

        try:
            # Download the image
            async with httpx.AsyncClient() as client:
                response = await client.get(image_url, timeout=30.0)
                response.raise_for_status()
                image_data = response.content

            # Compress
            compressed_data, metadata = ImageCompressor.compress_image(
                image_data,
                output_format=output_format,
                quality=quality,
                max_width=max_width,
                max_height=max_height,
            )

            return {
                "success": True,
                "metadata": metadata,
                "compressed_size": len(compressed_data),
                "message": f"Image compressed: {metadata['compression_ratio']}% smaller",
            }

        except Exception as e:
            logger.error(f"Image compression failed: {e}")
            return {"error": f"Compression failed: {str(e)}"}

    @mcp.tool()
    async def get_image_info(
        image_url: str,
        context: dict | None = None,
    ) -> dict[str, Any]:
        """Get information about an image.

        Args:
            image_url: URL of the image

        Returns:
            Image metadata
        """
        if not ImageCompressor.is_available():
            return {"error": "Image tools not available (Pillow not installed)"}

        try:
            # Download the image
            async with httpx.AsyncClient() as client:
                response = await client.get(image_url, timeout=30.0)
                response.raise_for_status()
                image_data = response.content

            info = ImageCompressor.get_image_info(image_data)
            return {"success": True, **info}

        except Exception as e:
            logger.error(f"Get image info failed: {e}")
            return {"error": f"Failed to get image info: {str(e)}"}

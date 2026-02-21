"""MCP tools for image compression and optimization."""

from __future__ import annotations

from typing import Any, Optional
import base64

from mcp.server.fastmcp import FastMCP

from wp_mcp.graphql.client import get_graphql_client
from wp_mcp.context_helper import get_connection_info
from wp_mcp.image_compressor import ImageCompressor
from wp_mcp.profiling import profile_mcp_function
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

    @mcp.tool()
    async def upload_image_to_wordpress(
        image_data_base64: str,
        filename: str,
        title: Optional[str] = None,
        alt_text: Optional[str] = None,
        caption: Optional[str] = None,
        context: dict | None = None,
    ) -> dict[str, Any]:
        """Upload an image to WordPress media library.

        Args:
            image_data_base64: Base64-encoded image data
            filename: Filename for the uploaded image
            title: Optional title for the media item
            alt_text: Optional alt text for accessibility
            caption: Optional caption

        Returns:
            Uploaded media information including ID and URL
        """
        try:
            conn_info = get_connection_info(context)

            # Decode base64 image data
            image_data = base64.b64decode(image_data_base64)

            # Upload via WordPress REST API
            upload_url = f"{conn_info['wp_url'].rstrip('/')}/wp-json/wp/v2/media"

            async with httpx.AsyncClient() as client:
                files = {"file": (filename, image_data)}
                data = {}

                if title:
                    data["title"] = title
                if alt_text:
                    data["alt_text"] = alt_text
                if caption:
                    data["caption"] = caption

                response = await client.post(
                    upload_url,
                    files=files,
                    data=data,
                    auth=(conn_info["username"], conn_info["app_password"]),
                    timeout=60.0,
                )

                if response.status_code not in [200, 201]:
                    return {"error": f"Upload failed: {response.status_code} {response.text}"}

                result = response.json()

                return {
                    "success": True,
                    "media_id": result.get("id"),
                    "url": result.get("source_url"),
                    "title": result.get("title", {}).get("rendered"),
                    "size": len(image_data),
                }

        except Exception as e:
            logger.error(f"Image upload failed: {e}")
            return {"error": f"Upload failed: {str(e)}"}

    @mcp.tool()
    async def get_media_library_images(
        per_page: int = 20,
        page: int = 1,
        context: dict | None = None,
    ) -> dict[str, Any]:
        """Get images from WordPress media library.

        Args:
            per_page: Number of images per page (max 100)
            page: Page number

        Returns:
            List of media items with URLs and metadata
        """
        try:
            conn_info = get_connection_info(context)
            client = get_graphql_client(
                conn_info["graphql_endpoint"],
                conn_info["username"],
                conn_info["app_password"]
            )

            query = """
            query GetMediaItems($first: Int!, $after: String) {
              mediaItems(first: $first, after: $after, where: {mimeType: IMAGE}) {
                nodes {
                  id
                  databaseId
                  title
                  sourceUrl
                  altText
                  mediaDetails {
                    width
                    height
                    fileSize
                  }
                }
                pageInfo {
                  hasNextPage
                  endCursor
                }
              }
            }
            """

            # Calculate cursor from page number
            cursor = None if page == 1 else str((page - 1) * per_page)

            result = await client.execute(query, {
                "first": min(per_page, 100),
                "after": cursor
            })

            if not result.get("mediaItems"):
                return {"error": "Failed to fetch media items"}

            media_items = result["mediaItems"]["nodes"]
            page_info = result["mediaItems"]["pageInfo"]

            return {
                "success": True,
                "images": [
                    {
                        "id": item["databaseId"],
                        "title": item["title"],
                        "url": item["sourceUrl"],
                        "alt_text": item.get("altText", ""),
                        "width": item.get("mediaDetails", {}).get("width"),
                        "height": item.get("mediaDetails", {}).get("height"),
                        "file_size": item.get("mediaDetails", {}).get("fileSize"),
                    }
                    for item in media_items
                ],
                "has_more": page_info["hasNextPage"],
                "total": len(media_items),
            }

        except Exception as e:
            logger.error(f"Failed to get media library: {e}")
            return {"error": f"Failed to fetch media: {str(e)}"}

    @mcp.tool()
    @profile_mcp_function(enabled=True, track_memory=True)
    async def bulk_optimize_media_library(
        quality_preset: str = "high",
        output_format: str = "webp",
        max_images: int = 10,
        replace_originals: bool = False,
        context: dict | None = None,
    ) -> dict[str, Any]:
        """Optimize multiple images from WordPress media library.

        Args:
            quality_preset: Quality preset (low, medium, high, max)
            output_format: Target format (webp, jpeg, png)
            max_images: Maximum number of images to process
            replace_originals: Whether to upload optimized versions back to WordPress

        Returns:
            Optimization results for all processed images
        """
        if not ImageCompressor.is_available():
            return {"error": "Image compression not available"}

        try:
            # Get media library images
            media_result = await get_media_library_images(
                per_page=max_images,
                page=1,
                context=context
            )

            if not media_result.get("success"):
                return media_result

            images = media_result["images"]

            if not images:
                return {"success": True, "message": "No images to optimize", "results": []}

            # Get quality from preset
            quality = ImageCompressor.get_quality_from_preset(quality_preset)

            # Download and compress images
            results = []
            async with httpx.AsyncClient() as client:
                for idx, image in enumerate(images):
                    try:
                        logger.info(f"Processing {idx + 1}/{len(images)}: {image['title']}")

                        # Download original
                        response = await client.get(image["url"], timeout=30.0)
                        response.raise_for_status()
                        original_data = response.content

                        # Compress
                        compressed_data, metadata = ImageCompressor.compress_image(
                            original_data,
                            output_format=output_format,
                            quality=quality,
                        )

                        result = {
                            "image_id": image["id"],
                            "title": image["title"],
                            "original_url": image["url"],
                            "original_size": len(original_data),
                            "compressed_size": len(compressed_data),
                            "savings": metadata["compression_ratio"],
                            "format": metadata["format"],
                            "success": True,
                        }

                        # Upload optimized version if requested
                        if replace_originals and metadata["compression_ratio"] > 0:
                            upload_result = await upload_image_to_wordpress(
                                image_data_base64=base64.b64encode(compressed_data).decode(),
                                filename=f"optimized-{image['id']}.{output_format}",
                                title=f"{image['title']} (Optimized)",
                                alt_text=image.get("alt_text", ""),
                                context=context,
                            )

                            if upload_result.get("success"):
                                result["new_url"] = upload_result["url"]
                                result["new_media_id"] = upload_result["media_id"]
                                result["replaced"] = True
                            else:
                                result["upload_error"] = upload_result.get("error")
                                result["replaced"] = False

                        results.append(result)

                    except Exception as e:
                        logger.error(f"Failed to process {image['title']}: {e}")
                        results.append({
                            "image_id": image["id"],
                            "title": image["title"],
                            "success": False,
                            "error": str(e),
                        })

            # Calculate totals
            successful = [r for r in results if r.get("success")]
            total_original = sum(r.get("original_size", 0) for r in successful)
            total_compressed = sum(r.get("compressed_size", 0) for r in successful)
            total_savings = ((total_original - total_compressed) / total_original * 100) if total_original > 0 else 0

            return {
                "success": True,
                "processed": len(images),
                "successful": len(successful),
                "failed": len(results) - len(successful),
                "total_original_size": total_original,
                "total_compressed_size": total_compressed,
                "total_savings_percent": round(total_savings, 2),
                "results": results,
            }

        except Exception as e:
            logger.error(f"Bulk optimization failed: {e}")
            return {"error": f"Bulk optimization failed: {str(e)}"}

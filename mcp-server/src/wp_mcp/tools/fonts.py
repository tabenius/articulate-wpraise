"""MCP tools for WordPress font management operations."""

from __future__ import annotations

from typing import Any
import httpx

from mcp.server.fastmcp import FastMCP

from wp_mcp.config import config


def register(mcp: FastMCP) -> None:
    """Register font-related tools with the MCP server."""

    @mcp.tool()
    async def upload_font(
        file_url: str,
        font_family: str = "",
        font_weight: str = "400",
        font_style: str = "normal",
    ) -> dict[str, Any]:
        """Upload a font file to WordPress and automatically register it with @font-face.

        The font will be immediately available for use in the theme after upload.
        Supports WOFF2, WOFF, TTF, OTF, and EOT formats.

        Args:
            file_url: URL of the font file to download and upload.
            font_family: Font family name (auto-detected from filename if not provided).
            font_weight: Font weight (100-900, default: "400").
            font_style: Font style ("normal", "italic", or "oblique", default: "normal").

        Returns:
            Font registration data with id, family, weight, style, url, and generated CSS.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Download the font file from the URL
            try:
                response = await client.get(file_url)
                response.raise_for_status()
                file_content = response.content

                # Determine filename and content type
                filename = file_url.split("/")[-1].split("?")[0] or "font.woff2"

                # Validate font file extension
                valid_extensions = [".woff2", ".woff", ".ttf", ".otf", ".eot"]
                if not any(filename.lower().endswith(ext) for ext in valid_extensions):
                    return {
                        "error": f"Invalid font file type. Must be one of: {', '.join(valid_extensions)}"
                    }

                # Determine content type based on file extension
                content_type_map = {
                    ".woff2": "font/woff2",
                    ".woff": "font/woff",
                    ".ttf": "font/ttf",
                    ".otf": "font/otf",
                    ".eot": "application/vnd.ms-fontobject",
                }
                content_type = next(
                    (ct for ext, ct in content_type_map.items() if filename.lower().endswith(ext)),
                    "application/octet-stream"
                )

            except Exception as e:
                return {"error": f"Failed to download font file: {str(e)}"}

            # Upload to WordPress custom REST API endpoint
            try:
                files = {"file": (filename, file_content, content_type)}
                data: dict[str, str] = {}

                if font_family:
                    data["font_family"] = font_family
                if font_weight:
                    data["font_weight"] = str(font_weight)
                if font_style:
                    data["font_style"] = font_style

                wp_auth = config.wp_auth
                if not wp_auth:
                    return {"error": "WordPress authentication not configured"}

                upload_url = f"{config.wp_url}/wp-json/articulate/v1/fonts/upload"
                upload_response = await client.post(
                    upload_url,
                    files=files,
                    data=data,
                    auth=wp_auth,
                )
                upload_response.raise_for_status()

                result = upload_response.json()

                if not result.get("success"):
                    return {"error": "Font upload failed"}

                return result.get("font", {})

            except httpx.HTTPStatusError as e:
                error_text = e.response.text
                try:
                    error_json = e.response.json()
                    if "message" in error_json:
                        error_text = error_json["message"]
                except Exception:
                    pass
                return {"error": f"Upload failed: {e.response.status_code} - {error_text}"}
            except Exception as e:
                return {"error": f"Upload failed: {str(e)}"}

    @mcp.tool()
    async def list_fonts() -> list[dict[str, Any]]:
        """List all registered fonts in WordPress.

        Returns:
            List of font objects with id, family, weight, style, url, format, and CSS.
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                wp_auth = config.wp_auth
                if not wp_auth:
                    return [{"error": "WordPress authentication not configured"}]

                list_url = f"{config.wp_url}/wp-json/articulate/v1/fonts"
                response = await client.get(list_url, auth=wp_auth)
                response.raise_for_status()

                result = response.json()
                if result.get("success"):
                    return result.get("fonts", [])
                return []

            except httpx.HTTPStatusError as e:
                return [{"error": f"Failed to list fonts: {e.response.status_code}"}]
            except Exception as e:
                return [{"error": f"Failed to list fonts: {str(e)}"}]

    @mcp.tool()
    async def delete_font(font_id: str) -> dict[str, Any]:
        """Delete a registered font from WordPress.

        Args:
            font_id: The font ID (format: family-weight-style, e.g., "roboto-400-normal").

        Returns:
            Success or error message.
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                wp_auth = config.wp_auth
                if not wp_auth:
                    return {"error": "WordPress authentication not configured"}

                delete_url = f"{config.wp_url}/wp-json/articulate/v1/fonts/{font_id}"
                response = await client.delete(delete_url, auth=wp_auth)
                response.raise_for_status()

                result = response.json()
                return result

            except httpx.HTTPStatusError as e:
                error_text = e.response.text
                try:
                    error_json = e.response.json()
                    if "message" in error_json:
                        error_text = error_json["message"]
                except Exception:
                    pass
                return {"error": f"Delete failed: {e.response.status_code} - {error_text}"}
            except Exception as e:
                return {"error": f"Delete failed: {str(e)}"}

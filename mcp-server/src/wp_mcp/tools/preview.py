"""MCP tool for WordPress preview rendering."""

from __future__ import annotations

from typing import Any
import httpx

from mcp.server.fastmcp import FastMCP

from wp_mcp.config import config


def register(mcp: FastMCP) -> None:
    """Register preview-related tools with the MCP server."""

    @mcp.tool()
    async def get_preview_html(post_id: int) -> dict[str, Any]:
        """Get rendered HTML preview of a post with active WordPress theme.

        This tool fetches the fully rendered HTML of a WordPress post as it would
        appear on the live site, including all theme styles, header, footer, and
        WordPress filters (shortcodes, embeds, etc.).

        Args:
            post_id: WordPress database ID of the post to preview.

        Returns:
            Dict with 'success', 'html', 'post_id', 'theme', 'post_type', and 'post_status' keys.
            The 'html' contains the complete rendered page with WordPress theme.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                wp_auth = config.wp_auth
                if not wp_auth:
                    return {"error": "WordPress authentication not configured"}

                preview_url = f"{config.wp_url}/wp-json/wp-ai/v1/preview/{post_id}"
                response = await client.get(preview_url, auth=wp_auth)
                response.raise_for_status()

                result = response.json()

                if not result.get("success"):
                    return {"error": "Preview generation failed"}

                return result

            except httpx.HTTPStatusError as e:
                error_text = e.response.text
                try:
                    error_json = e.response.json()
                    if "message" in error_json:
                        error_text = error_json["message"]
                except Exception:
                    pass
                return {"error": f"Preview failed: {e.response.status_code} - {error_text}"}
            except Exception as e:
                return {"error": f"Preview failed: {str(e)}"}

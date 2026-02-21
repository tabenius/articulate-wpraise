"""MCP tools for exporting WordPress sites to Next.js."""

from __future__ import annotations

from typing import Any, Optional, Literal
import logging
import tempfile
import shutil
import zipfile
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from wp_mcp.graphql.client import get_graphql_client
from wp_mcp.context_helper import get_connection_info
from wp_mcp.nextjs_generator import NextJSGenerator

logger = logging.getLogger(__name__)


def register(mcp: FastMCP) -> None:
    """Register export-related tools with the MCP server."""

    @mcp.tool()
    async def export_site_content(
        include_posts: bool = True,
        include_pages: bool = True,
        include_templates: bool = True,
        include_menus: bool = True,
        include_media: bool = True,
        context: dict | None = None,
    ) -> dict[str, Any]:
        """Export complete WordPress site content for Next.js migration.

        Args:
            include_posts: Export all published posts
            include_pages: Export all published pages
            include_templates: Export templates and template parts
            include_menus: Export navigation menus
            include_media: Export media library metadata

        Returns:
            Complete site export manifest with all requested content
        """
        try:
            conn_info = get_connection_info(context)
            client = get_graphql_client(
                conn_info["graphql_endpoint"],
                conn_info["username"],
                conn_info["app_password"]
            )

            export_data: dict[str, Any] = {
                "site_info": {},
                "posts": [],
                "pages": [],
                "templates": [],
                "template_parts": [],
                "menus": [],
                "media": [],
                "theme": {},
            }

            # Get site information
            site_info_query = """
            query GetSiteInfo {
              generalSettings {
                title
                description
                url
                language
                dateFormat
                timeFormat
              }
            }
            """
            site_result = await client.execute(site_info_query)
            if site_result.get("generalSettings"):
                export_data["site_info"] = site_result["generalSettings"]

            # Export posts
            if include_posts:
                posts_query = """
                query GetAllPosts($first: Int!, $after: String) {
                  posts(first: $first, after: $after, where: {status: PUBLISH}) {
                    nodes {
                      id
                      databaseId
                      title
                      content
                      excerpt
                      slug
                      date
                      modified
                      status
                      author {
                        node {
                          name
                          email
                        }
                      }
                      categories {
                        nodes {
                          name
                          slug
                        }
                      }
                      tags {
                        nodes {
                          name
                          slug
                        }
                      }
                      featuredImage {
                        node {
                          sourceUrl
                          altText
                          mediaDetails {
                            width
                            height
                          }
                        }
                      }
                    }
                    pageInfo {
                      hasNextPage
                      endCursor
                    }
                  }
                }
                """

                all_posts = []
                has_next = True
                cursor = None

                while has_next:
                    result = await client.execute(posts_query, {
                        "first": 100,
                        "after": cursor
                    })

                    if result.get("posts"):
                        all_posts.extend(result["posts"]["nodes"])
                        page_info = result["posts"]["pageInfo"]
                        has_next = page_info["hasNextPage"]
                        cursor = page_info["endCursor"]
                    else:
                        has_next = False

                export_data["posts"] = all_posts

            # Export pages
            if include_pages:
                pages_query = """
                query GetAllPages($first: Int!, $after: String) {
                  pages(first: $first, after: $after, where: {status: PUBLISH}) {
                    nodes {
                      id
                      databaseId
                      title
                      content
                      excerpt
                      slug
                      date
                      modified
                      status
                      parent {
                        node {
                          databaseId
                          slug
                        }
                      }
                      featuredImage {
                        node {
                          sourceUrl
                          altText
                          mediaDetails {
                            width
                            height
                          }
                        }
                      }
                    }
                    pageInfo {
                      hasNextPage
                      endCursor
                    }
                  }
                }
                """

                all_pages = []
                has_next = True
                cursor = None

                while has_next:
                    result = await client.execute(pages_query, {
                        "first": 100,
                        "after": cursor
                    })

                    if result.get("pages"):
                        all_pages.extend(result["pages"]["nodes"])
                        page_info = result["pages"]["pageInfo"]
                        has_next = page_info["hasNextPage"]
                        cursor = page_info["endCursor"]
                    else:
                        has_next = False

                export_data["pages"] = all_pages

            # Export templates
            if include_templates:
                templates_query = """
                query GetTemplates {
                  __type(name: "RootQuery") {
                    name
                  }
                }
                """
                # Note: Template export requires custom implementation
                # This is a placeholder - will be implemented based on WordPress version
                logger.warning("Template export requires custom implementation")

            # Export menus
            if include_menus:
                menus_query = """
                query GetMenus {
                  menus {
                    nodes {
                      id
                      databaseId
                      name
                      slug
                      menuItems {
                        nodes {
                          id
                          databaseId
                          label
                          url
                          target
                          cssClasses
                          parentId
                          order
                        }
                      }
                    }
                  }
                }
                """

                menus_result = await client.execute(menus_query)
                if menus_result.get("menus"):
                    export_data["menus"] = menus_result["menus"]["nodes"]

            # Export media metadata
            if include_media:
                media_query = """
                query GetAllMedia($first: Int!, $after: String) {
                  mediaItems(first: $first, after: $after) {
                    nodes {
                      id
                      databaseId
                      title
                      sourceUrl
                      altText
                      caption
                      description
                      mimeType
                      fileSize
                      mediaDetails {
                        width
                        height
                        file
                      }
                    }
                    pageInfo {
                      hasNextPage
                      endCursor
                    }
                  }
                }
                """

                all_media = []
                has_next = True
                cursor = None

                while has_next:
                    result = await client.execute(media_query, {
                        "first": 100,
                        "after": cursor
                    })

                    if result.get("mediaItems"):
                        all_media.extend(result["mediaItems"]["nodes"])
                        page_info = result["mediaItems"]["pageInfo"]
                        has_next = page_info["hasNextPage"]
                        cursor = page_info["endCursor"]
                    else:
                        has_next = False

                export_data["media"] = all_media

            # Get theme.json if available
            # This would require REST API access or custom endpoint
            logger.info("Theme data export requires REST API access")

            return {
                "success": True,
                "export_data": export_data,
                "stats": {
                    "posts_count": len(export_data["posts"]),
                    "pages_count": len(export_data["pages"]),
                    "menus_count": len(export_data["menus"]),
                    "media_count": len(export_data["media"]),
                },
                "message": f"Successfully exported site content",
            }

        except Exception as e:
            logger.error(f"Site export failed: {e}")
            return {"error": f"Export failed: {str(e)}"}

    @mcp.tool()
    async def export_theme_json(
        context: dict | None = None,
    ) -> dict[str, Any]:
        """Export WordPress theme.json for Next.js styling conversion.

        Returns:
            Theme configuration including colors, typography, spacing, etc.
        """
        try:
            conn_info = get_connection_info(context)

            # TODO: Fetch theme.json via REST API
            # GET /wp-json/wp/v2/themes/{theme}/theme.json

            import httpx

            async with httpx.AsyncClient() as http_client:
                # Get active theme first
                themes_url = f"{conn_info['wp_url'].rstrip('/')}/wp-json/wp/v2/themes"
                themes_response = await http_client.get(
                    themes_url,
                    auth=(conn_info["username"], conn_info["app_password"]),
                    timeout=30.0,
                )

                if themes_response.status_code != 200:
                    return {
                        "error": f"Failed to fetch themes: {themes_response.status_code}"
                    }

                themes = themes_response.json()
                active_theme = next(
                    (t for t in themes if t.get("status") == "active"),
                    None
                )

                if not active_theme:
                    return {"error": "No active theme found"}

                # Try to get theme.json
                theme_slug = active_theme.get("stylesheet")
                theme_json_url = f"{conn_info['wp_url'].rstrip('/')}/wp-json/wp/v2/themes/{theme_slug}"

                theme_response = await http_client.get(
                    theme_json_url,
                    auth=(conn_info["username"], conn_info["app_password"]),
                    timeout=30.0,
                )

                if theme_response.status_code == 200:
                    theme_data = theme_response.json()

                    return {
                        "success": True,
                        "theme": {
                            "name": active_theme.get("name"),
                            "slug": theme_slug,
                            "version": active_theme.get("version"),
                            "config": theme_data,
                        },
                    }
                else:
                    return {
                        "success": False,
                        "error": "theme.json not available for this theme",
                        "theme_name": active_theme.get("name"),
                    }

        except Exception as e:
            logger.error(f"Theme export failed: {e}")
            return {"error": f"Theme export failed: {str(e)}"}

    @mcp.tool()
    async def get_export_manifest(
        context: dict | None = None,
    ) -> dict[str, Any]:
        """Generate a complete export manifest for Next.js migration.

        Returns:
            Comprehensive manifest with all export data and metadata
        """
        try:
            # This combines all export functions into one manifest
            content_export = await export_site_content(
                include_posts=True,
                include_pages=True,
                include_templates=True,
                include_menus=True,
                include_media=True,
                context=context,
            )

            theme_export = await export_theme_json(context=context)

            if not content_export.get("success"):
                return content_export

            manifest = {
                "success": True,
                "version": "1.0.0",
                "export_date": "",  # Will be set by generator
                "wordpress_version": "",  # TODO: fetch from site
                "site": content_export["export_data"]["site_info"],
                "content": {
                    "posts": content_export["export_data"]["posts"],
                    "pages": content_export["export_data"]["pages"],
                    "menus": content_export["export_data"]["menus"],
                },
                "media": content_export["export_data"]["media"],
                "theme": theme_export.get("theme", {}),
                "stats": content_export["stats"],
            }

            return manifest

        except Exception as e:
            logger.error(f"Manifest generation failed: {e}")
            return {"error": f"Manifest generation failed: {str(e)}"}

    @mcp.tool()
    async def generate_nextjs_site(
        content_format: Literal["react", "blocks", "mdx", "html"] = "react",
        render_strategy: Literal["ssg", "ssr", "isr", "headless"] = "ssg",
        media_strategy: Literal["download", "keep_urls", "cdn", "next_image"] = "download",
        context: dict | None = None,
    ) -> dict[str, Any]:
        """Generate a complete Next.js project from WordPress content.

        Args:
            content_format: How to render WordPress blocks (react/blocks/mdx/html)
            render_strategy: Next.js rendering strategy (ssg/ssr/isr/headless)
            media_strategy: How to handle media files (download/keep_urls/cdn/next_image)

        Returns:
            Generated project location and file manifest
        """
        try:
            # Get export manifest
            manifest_result = await get_export_manifest(context=context)

            if not manifest_result.get("success"):
                return manifest_result

            # Create temporary directory for output
            temp_dir = tempfile.mkdtemp(prefix="nextjs_export_")

            # Generate Next.js project
            generator = NextJSGenerator(
                export_data=manifest_result,
                output_dir=temp_dir,
                content_format=content_format,
                render_strategy=render_strategy,
                media_strategy=media_strategy,
            )

            result = generator.generate()

            if result.get("success"):
                # Create zip archive
                zip_path = f"{temp_dir}.zip"
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in Path(temp_dir).walk():
                        for file in files:
                            file_path = Path(root) / file
                            arcname = file_path.relative_to(temp_dir)
                            zipf.write(file_path, arcname)

                return {
                    "success": True,
                    "output_dir": temp_dir,
                    "zip_file": zip_path,
                    "files_created": result["files_created"],
                    "content_format": content_format,
                    "render_strategy": render_strategy,
                    "media_strategy": media_strategy,
                    "message": f"Next.js project generated successfully at {temp_dir}",
                }
            else:
                return result

        except Exception as e:
            logger.error(f"Next.js generation failed: {e}")
            return {"error": f"Next.js generation failed: {str(e)}"}

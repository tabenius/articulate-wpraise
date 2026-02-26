"""MCP tools for WordPress SEO metadata management."""

from __future__ import annotations

from typing import Any, Optional
import logging

from mcp.server.fastmcp import FastMCP
from articulate_mcp.graphql.client import get_graphql_client
from articulate_mcp.context_helper import get_connection_info

logger = logging.getLogger(__name__)


def register(mcp: FastMCP) -> None:
    """Register SEO-related tools with the MCP server."""

    @mcp.tool()
    async def get_post_seo(
        post_id: int,
        context: dict | None = None,
    ) -> dict[str, Any]:
        """Get SEO metadata for a WordPress post or page.

        Retrieves all SEO fields including general meta, Open Graph, and Twitter Card data.

        Args:
            post_id: WordPress post/page ID

        Returns:
            SEO metadata including title, description, OG tags, Twitter cards, etc.
        """
        try:
            conn_info = get_connection_info(context)
            client = get_graphql_client(
                conn_info["graphql_endpoint"],
                conn_info["username"],
                conn_info["app_password"]
            )

            # GraphQL query to get post meta fields
            query = """
            query GetPostSEO($id: ID!) {
              post(id: $id, idType: DATABASE_ID) {
                id
                title
                excerpt
                metaFields: customFields {
                  key
                  value
                }
              }
            }
            """

            result = await client.execute(query, {"id": post_id})

            if not result.get("post"):
                return {"error": f"Post {post_id} not found"}

            post = result["post"]
            meta_fields = post.get("metaFields", []) or []

            # Parse meta fields into structured SEO data
            meta_dict = {field["key"]: field["value"] for field in meta_fields if field}

            seo_data = {
                "post_id": post_id,
                "post_title": post["title"],
                "post_excerpt": post["excerpt"],

                # General SEO
                "seo_title": meta_dict.get("_articulate_seo_title", ""),
                "meta_description": meta_dict.get("_articulate_seo_description", ""),
                "focus_keyword": meta_dict.get("_articulate_seo_focus_keyword", ""),
                "canonical_url": meta_dict.get("_articulate_seo_canonical", ""),
                "meta_robots": meta_dict.get("_articulate_seo_robots", ""),

                # Open Graph
                "og_title": meta_dict.get("_articulate_og_title", ""),
                "og_description": meta_dict.get("_articulate_og_description", ""),
                "og_image": meta_dict.get("_articulate_og_image", ""),
                "og_type": meta_dict.get("_articulate_og_type", "article"),

                # Twitter Cards
                "twitter_card": meta_dict.get("_articulate_twitter_card", "summary_large_image"),
                "twitter_title": meta_dict.get("_articulate_twitter_title", ""),
                "twitter_description": meta_dict.get("_articulate_twitter_description", ""),
                "twitter_image": meta_dict.get("_articulate_twitter_image", ""),

                # Advanced
                "breadcrumb_title": meta_dict.get("_articulate_seo_breadcrumb_title", ""),
                "schema_type": meta_dict.get("_articulate_schema_type", "Article"),
            }

            return {"success": True, "seo": seo_data}

        except Exception as e:
            logger.error(f"Failed to get post SEO: {e}")
            return {"error": f"Failed to retrieve SEO data: {str(e)}"}

    @mcp.tool()
    async def update_post_seo(
        post_id: int,
        seo_title: Optional[str] = None,
        meta_description: Optional[str] = None,
        focus_keyword: Optional[str] = None,
        canonical_url: Optional[str] = None,
        meta_robots: Optional[str] = None,
        og_title: Optional[str] = None,
        og_description: Optional[str] = None,
        og_image: Optional[str] = None,
        og_type: Optional[str] = None,
        twitter_card: Optional[str] = None,
        twitter_title: Optional[str] = None,
        twitter_description: Optional[str] = None,
        twitter_image: Optional[str] = None,
        breadcrumb_title: Optional[str] = None,
        schema_type: Optional[str] = None,
        context: dict | None = None,
    ) -> dict[str, Any]:
        """Update SEO metadata for a WordPress post or page.

        Updates SEO fields including general meta, Open Graph, and Twitter Card data.
        Only provided fields will be updated; others remain unchanged.

        Args:
            post_id: WordPress post/page ID
            seo_title: SEO title (recommended: 50-60 chars)
            meta_description: Meta description (recommended: 150-160 chars)
            focus_keyword: Primary keyword for the page
            canonical_url: Canonical URL to prevent duplicates
            meta_robots: Robots meta directives (JSON array)
            og_title: Open Graph title
            og_description: Open Graph description
            og_image: Open Graph image URL
            og_type: Open Graph type (article, website, etc.)
            twitter_card: Twitter card type (summary, summary_large_image)
            twitter_title: Twitter card title
            twitter_description: Twitter card description
            twitter_image: Twitter card image URL
            breadcrumb_title: Custom breadcrumb text
            schema_type: Schema.org type

        Returns:
            Success status and updated SEO data
        """
        try:
            conn_info = get_connection_info(context)
            client = get_graphql_client(
                conn_info["graphql_endpoint"],
                conn_info["username"],
                conn_info["app_password"]
            )

            # Build meta fields array for only provided values
            meta_updates = []

            if seo_title is not None:
                meta_updates.append({"key": "_articulate_seo_title", "value": seo_title})
            if meta_description is not None:
                meta_updates.append({"key": "_articulate_seo_description", "value": meta_description})
            if focus_keyword is not None:
                meta_updates.append({"key": "_articulate_seo_focus_keyword", "value": focus_keyword})
            if canonical_url is not None:
                meta_updates.append({"key": "_articulate_seo_canonical", "value": canonical_url})
            if meta_robots is not None:
                meta_updates.append({"key": "_articulate_seo_robots", "value": meta_robots})
            if og_title is not None:
                meta_updates.append({"key": "_articulate_og_title", "value": og_title})
            if og_description is not None:
                meta_updates.append({"key": "_articulate_og_description", "value": og_description})
            if og_image is not None:
                meta_updates.append({"key": "_articulate_og_image", "value": og_image})
            if og_type is not None:
                meta_updates.append({"key": "_articulate_og_type", "value": og_type})
            if twitter_card is not None:
                meta_updates.append({"key": "_articulate_twitter_card", "value": twitter_card})
            if twitter_title is not None:
                meta_updates.append({"key": "_articulate_twitter_title", "value": twitter_title})
            if twitter_description is not None:
                meta_updates.append({"key": "_articulate_twitter_description", "value": twitter_description})
            if twitter_image is not None:
                meta_updates.append({"key": "_articulate_twitter_image", "value": twitter_image})
            if breadcrumb_title is not None:
                meta_updates.append({"key": "_articulate_seo_breadcrumb_title", "value": breadcrumb_title})
            if schema_type is not None:
                meta_updates.append({"key": "_articulate_schema_type", "value": schema_type})

            if not meta_updates:
                return {"error": "No SEO fields provided to update"}

            # GraphQL mutation to update post meta
            mutation = """
            mutation UpdatePostMeta($id: ID!, $meta: [MetaInput!]!) {
              updatePost(input: {
                id: $id,
                metaData: $meta
              }) {
                post {
                  id
                  databaseId
                }
              }
            }
            """

            result = await client.execute(mutation, {
                "id": post_id,
                "meta": meta_updates
            })

            if not result.get("updatePost"):
                return {"error": "Failed to update post SEO metadata"}

            # Fetch updated SEO data
            updated_seo = await get_post_seo(post_id, context)

            return {
                "success": True,
                "message": f"Updated {len(meta_updates)} SEO field(s)",
                "seo": updated_seo.get("seo", {})
            }

        except Exception as e:
            logger.error(f"Failed to update post SEO: {e}")
            return {"error": f"Failed to update SEO data: {str(e)}"}

    @mcp.tool()
    async def validate_seo(
        seo_title: str,
        meta_description: str,
        focus_keyword: Optional[str] = None,
        context: dict | None = None,
    ) -> dict[str, Any]:
        """Validate SEO fields and provide recommendations.

        Checks character counts, keyword usage, and provides optimization tips.

        Args:
            seo_title: SEO title to validate
            meta_description: Meta description to validate
            focus_keyword: Optional focus keyword to check usage

        Returns:
            Validation results with warnings and recommendations
        """
        warnings = []
        recommendations = []
        scores = {}

        # Validate SEO title
        title_len = len(seo_title)
        if title_len == 0:
            warnings.append("SEO title is empty")
            scores["title"] = 0
        elif title_len < 30:
            warnings.append("SEO title is too short (< 30 chars)")
            scores["title"] = 50
        elif title_len > 60:
            warnings.append("SEO title may be truncated in search results (> 60 chars)")
            scores["title"] = 70
        else:
            scores["title"] = 100

        # Validate meta description
        desc_len = len(meta_description)
        if desc_len == 0:
            warnings.append("Meta description is empty")
            scores["description"] = 0
        elif desc_len < 120:
            warnings.append("Meta description is too short (< 120 chars)")
            scores["description"] = 50
        elif desc_len > 160:
            warnings.append("Meta description may be truncated in search results (> 160 chars)")
            scores["description"] = 70
        else:
            scores["description"] = 100

        # Check focus keyword usage
        if focus_keyword:
            keyword_lower = focus_keyword.lower()
            title_lower = seo_title.lower()
            desc_lower = meta_description.lower()

            if keyword_lower not in title_lower:
                recommendations.append(f"Consider including focus keyword '{focus_keyword}' in SEO title")
                scores["keyword_usage"] = 50
            elif keyword_lower not in desc_lower:
                recommendations.append(f"Consider including focus keyword '{focus_keyword}' in meta description")
                scores["keyword_usage"] = 75
            else:
                scores["keyword_usage"] = 100
        else:
            recommendations.append("Set a focus keyword to improve SEO targeting")
            scores["keyword_usage"] = 0

        # Calculate overall score
        overall_score = sum(scores.values()) // len(scores) if scores else 0

        return {
            "success": True,
            "score": overall_score,
            "scores": scores,
            "warnings": warnings,
            "recommendations": recommendations,
            "character_counts": {
                "title": title_len,
                "description": desc_len,
            }
        }

"""MCP tools for WordPress post operations."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from wp_mcp.graphql.client import gql_client
from wp_mcp.graphql.queries import GET_POST, GET_POSTS
from wp_mcp.graphql.mutations import CREATE_POST, UPDATE_POST, DELETE_POST


def register(mcp: FastMCP) -> None:
    """Register post-related tools with the MCP server."""

    @mcp.tool()
    async def get_posts(
        status: str = "publish",
        per_page: int = 10,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        """List WordPress posts with optional filtering.

        Args:
            status: Post status filter (publish, draft, pending, private).
            per_page: Number of posts to return (max 100).
            search: Optional search term to filter posts by title/content.

        Returns:
            List of post objects with id, title, slug, status, date, excerpt.
        """
        where: dict[str, Any] = {}
        if status:
            where["status"] = status.upper()
        if search:
            where["search"] = search

        data = await gql_client.query(
            GET_POSTS,
            variables={"first": min(per_page, 100), "where": where if where else None},
        )
        posts = data.get("posts", {}).get("nodes", [])
        return [_format_post_summary(p) for p in posts]

    @mcp.tool()
    async def get_post(post_id: int) -> dict[str, Any]:
        """Get a single WordPress post by its database ID.

        Args:
            post_id: The WordPress database ID of the post.

        Returns:
            Post object with id, title, slug, status, content, date.
        """
        data = await gql_client.query(
            GET_POST,
            variables={"id": str(post_id)},
        )
        post = data.get("post")
        if not post:
            return {"error": f"Post {post_id} not found"}
        return _format_post(post)

    @mcp.tool()
    async def create_post(
        title: str,
        content: str = "",
        status: str = "draft",
        featured_image_id: int | None = None,
        category_ids: list[int] | None = None,
        tag_ids: list[int] | None = None,
        date: str | None = None,
    ) -> dict[str, Any]:
        """Create a new WordPress post.

        Args:
            title: The post title.
            content: The post content in WordPress block format (serialized HTML comments).
            status: Post status (draft, publish, pending, private). Default: draft.
            featured_image_id: Database ID of the featured image (optional).
            category_ids: List of category database IDs to assign (optional).
            tag_ids: List of tag database IDs to assign (optional).
            date: ISO 8601 date string. Future dates schedule the post (optional).

        Returns:
            The created post object with id, title, slug, status.
        """
        input_data: dict[str, Any] = {
            "title": title,
            "content": content,
            "status": status.upper(),
        }
        if featured_image_id is not None:
            input_data["featuredImageId"] = str(featured_image_id)
        if category_ids is not None:
            input_data["categories"] = {
                "nodes": [{"id": f"databaseId:{cat_id}"} for cat_id in category_ids]
            }
        if tag_ids is not None:
            input_data["tags"] = {
                "nodes": [{"id": f"databaseId:{tag_id}"} for tag_id in tag_ids]
            }
        if date is not None:
            input_data["date"] = date

        data = await gql_client.mutate(
            CREATE_POST,
            variables={"input": input_data},
            invalidate_patterns=["gql:*post*"],
        )
        post = data.get("createPost", {}).get("post")
        if not post:
            return {"error": "Failed to create post"}
        return _format_post(post)

    @mcp.tool()
    async def update_post(
        post_id: int,
        title: str | None = None,
        content: str | None = None,
        status: str | None = None,
        featured_image_id: int | None = None,
        category_ids: list[int] | None = None,
        tag_ids: list[int] | None = None,
        date: str | None = None,
    ) -> dict[str, Any]:
        """Update an existing WordPress post.

        Args:
            post_id: The WordPress database ID of the post to update.
            title: New title (optional).
            content: New content in WordPress block format (optional).
            status: New status (optional).
            featured_image_id: Database ID of the featured image (optional, use 0 to remove).
            category_ids: List of category database IDs to assign (optional).
            tag_ids: List of tag database IDs to assign (optional).
            date: ISO 8601 date string. Future dates schedule the post (optional).

        Returns:
            The updated post object.
        """
        input_data: dict[str, Any] = {"id": str(post_id)}
        if title is not None:
            input_data["title"] = title
        if content is not None:
            input_data["content"] = content
        if status is not None:
            input_data["status"] = status.upper()
        if featured_image_id is not None:
            input_data["featuredImageId"] = str(featured_image_id) if featured_image_id > 0 else None
        if category_ids is not None:
            input_data["categories"] = {
                "nodes": [{"id": f"databaseId:{cat_id}"} for cat_id in category_ids]
            }
        if tag_ids is not None:
            input_data["tags"] = {
                "nodes": [{"id": f"databaseId:{tag_id}"} for tag_id in tag_ids]
            }
        if date is not None:
            input_data["date"] = date

        data = await gql_client.mutate(
            UPDATE_POST,
            variables={"input": input_data},
            invalidate_patterns=["gql:*post*"],
        )
        post = data.get("updatePost", {}).get("post")
        if not post:
            return {"error": f"Failed to update post {post_id}"}
        return _format_post(post)

    @mcp.tool()
    async def delete_post(post_id: int) -> dict[str, Any]:
        """Delete a WordPress post by its database ID.

        Args:
            post_id: The WordPress database ID of the post to delete.

        Returns:
            Confirmation with deleted post title and id.
        """
        data = await gql_client.mutate(
            DELETE_POST,
            variables={"input": {"id": str(post_id)}},
            invalidate_patterns=["gql:*post*"],
        )
        result = data.get("deletePost", {})
        post = result.get("post", {})
        return {
            "deleted": True,
            "id": post.get("databaseId"),
            "title": post.get("title"),
        }


def _format_post_summary(post: dict[str, Any]) -> dict[str, Any]:
    """Format a post for the summary list."""
    result = {
        "id": post.get("databaseId"),
        "title": post.get("title", ""),
        "slug": post.get("slug", ""),
        "status": post.get("status", "").lower(),
        "date": post.get("date", ""),
        "modified": post.get("modified", ""),
        "excerpt": post.get("excerpt", ""),
        "author": (post.get("author") or {}).get("node", {}).get("name", ""),
    }

    # Add featured image if present
    featured_image = post.get("featuredImage", {}).get("node")
    if featured_image:
        details = featured_image.get("mediaDetails", {}) or {}
        result["featuredImage"] = {
            "id": featured_image.get("databaseId"),
            "url": featured_image.get("sourceUrl", ""),
            "altText": featured_image.get("altText", ""),
            "width": details.get("width"),
            "height": details.get("height"),
        }

    return result


def _format_post(post: dict[str, Any]) -> dict[str, Any]:
    """Format a full post object."""
    result = {
        "id": post.get("databaseId"),
        "title": post.get("title", ""),
        "slug": post.get("slug", ""),
        "status": post.get("status", "").lower(),
        "content": post.get("content", ""),
        "date": post.get("date", ""),
        "modified": post.get("modified", ""),
        "author": (post.get("author") or {}).get("node", {}).get("name", ""),
    }

    # Add featured image if present
    featured_image = post.get("featuredImage", {}).get("node")
    if featured_image:
        details = featured_image.get("mediaDetails", {}) or {}
        result["featuredImage"] = {
            "id": featured_image.get("databaseId"),
            "url": featured_image.get("sourceUrl", ""),
            "altText": featured_image.get("altText", ""),
            "width": details.get("width"),
            "height": details.get("height"),
        }

    # Add categories if present
    categories = post.get("categories", {}).get("nodes", [])
    if categories:
        result["categories"] = [
            {
                "id": cat.get("databaseId"),
                "name": cat.get("name", ""),
                "slug": cat.get("slug", ""),
            }
            for cat in categories
        ]

    # Add tags if present
    tags = post.get("tags", {}).get("nodes", [])
    if tags:
        result["tags"] = [
            {
                "id": tag.get("databaseId"),
                "name": tag.get("name", ""),
                "slug": tag.get("slug", ""),
            }
            for tag in tags
        ]

    return result

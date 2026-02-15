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
    ) -> dict[str, Any]:
        """Create a new WordPress post.

        Args:
            title: The post title.
            content: The post content in WordPress block format (serialized HTML comments).
            status: Post status (draft, publish, pending, private). Default: draft.

        Returns:
            The created post object with id, title, slug, status.
        """
        input_data: dict[str, Any] = {
            "title": title,
            "content": content,
            "status": status.upper(),
        }
        data = await gql_client.mutate(
            CREATE_POST,
            variables={"input": input_data},
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
    ) -> dict[str, Any]:
        """Update an existing WordPress post.

        Args:
            post_id: The WordPress database ID of the post to update.
            title: New title (optional).
            content: New content in WordPress block format (optional).
            status: New status (optional).

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

        data = await gql_client.mutate(
            UPDATE_POST,
            variables={"input": input_data},
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
    return {
        "id": post.get("databaseId"),
        "title": post.get("title", ""),
        "slug": post.get("slug", ""),
        "status": post.get("status", "").lower(),
        "date": post.get("date", ""),
        "modified": post.get("modified", ""),
        "excerpt": post.get("excerpt", ""),
        "author": post.get("author", {}).get("node", {}).get("name", ""),
    }


def _format_post(post: dict[str, Any]) -> dict[str, Any]:
    """Format a full post object."""
    return {
        "id": post.get("databaseId"),
        "title": post.get("title", ""),
        "slug": post.get("slug", ""),
        "status": post.get("status", "").lower(),
        "content": post.get("content", ""),
        "date": post.get("date", ""),
        "modified": post.get("modified", ""),
        "author": post.get("author", {}).get("node", {}).get("name", ""),
    }

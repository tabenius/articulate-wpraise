"""MCP tools for WordPress post operations."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from wp_mcp.graphql.client import get_graphql_client
from wp_mcp.graphql.queries import GET_POST, GET_POSTS, GET_PAGES, GET_PAGE
from wp_mcp.graphql.mutations import (
    CREATE_POST,
    UPDATE_POST,
    DELETE_POST,
    CREATE_PAGE,
    UPDATE_PAGE,
)
from wp_mcp.context_helper import get_connection_info


def register(mcp: FastMCP) -> None:
    """Register post-related tools with the MCP server."""

    @mcp.tool()
    async def get_posts(
        status: str = "publish",
        per_page: int = 10,
        search: str | None = None,
        context: dict | None = None,
    ) -> list[dict[str, Any]]:
        """List WordPress posts and pages with optional filtering.

        Args:
            status: Post status filter (publish, draft, pending, private, any).
            per_page: Number of posts to return (max 100).
            search: Optional search term to filter posts by title/content.

        Returns:
            List of post/page objects with id, title, slug, status, date, excerpt.
        """
        connection_id, user_id = get_connection_info(context)
        client = await get_graphql_client(connection_id, user_id)

        # Fetch both posts and pages
        results: list[dict[str, Any]] = []

        # Fetch posts
        where: dict[str, Any] = {}
        if status and status.lower() != "any":
            where["status"] = status.upper()
        if search:
            where["search"] = search

        posts_data = await client.query(
            GET_POSTS,
            variables={"first": min(per_page, 100), "where": where if where else None},
            user_id=user_id,
        )
        posts = posts_data.get("posts", {}).get("nodes", [])
        results.extend([_format_post_summary(p, "post") for p in posts])

        # Fetch pages (pages don't support status/search filters in the same way)
        pages_data = await client.query(
            GET_PAGES,
            variables={"first": min(per_page, 100)},
            user_id=user_id,
        )
        pages = pages_data.get("pages", {}).get("nodes", [])

        # Filter pages by status if specified
        if status and status.lower() != "any":
            pages = [p for p in pages if p.get("status", "").upper() == status.upper()]

        results.extend([_format_post_summary(p, "page") for p in pages])

        # Sort by date descending
        results.sort(key=lambda x: x.get("date", ""), reverse=True)

        return results[: min(per_page, 100)]

    @mcp.tool()
    async def get_post(post_id: int, context: dict | None = None) -> dict[str, Any]:
        """Get a single WordPress post by its database ID.

        Args:
            post_id: The WordPress database ID of the post.

        Returns:
            Post object with id, title, slug, status, content, date.
        """
        connection_id, user_id = get_connection_info(context)
        client = await get_graphql_client(connection_id, user_id)

        data = await client.query(
            GET_POST,
            variables={"id": str(post_id)},
            user_id=user_id,
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
        post_type: str = "post",
        featured_image_id: int | None = None,
        category_ids: list[int] | None = None,
        tag_ids: list[int] | None = None,
        date: str | None = None,
        context: dict | None = None,
    ) -> dict[str, Any]:
        """Create a new WordPress post or page.

        Args:
            title: The post/page title.
            content: The content in WordPress block format (serialized HTML comments).
            status: Post status (draft, publish, pending, private). Default: draft.
            post_type: The post type ('post' or 'page'). Default: post.
            featured_image_id: Database ID of the featured image (optional).
            category_ids: List of category database IDs to assign (optional, posts only).
            tag_ids: List of tag database IDs to assign (optional, posts only).
            date: ISO 8601 date string. Future dates schedule the post (optional).

        Returns:
            The created post/page object with id, title, slug, status.
        """
        connection_id, user_id = get_connection_info(context)
        client = await get_graphql_client(connection_id, user_id)

        input_data: dict[str, Any] = {
            "title": title,
            "content": content,
            "status": status.upper(),
        }
        if featured_image_id is not None:
            input_data["featuredImageId"] = str(featured_image_id)

        # Categories and tags only apply to posts, not pages
        if post_type == "post":
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

        # Use different mutation based on post type
        mutation = CREATE_PAGE if post_type == "page" else CREATE_POST
        mutation_key = "createPage" if post_type == "page" else "createPost"
        result_key = "page" if post_type == "page" else "post"

        data = await client.mutate(
            mutation,
            variables={"input": input_data},
            invalidate_patterns=["gql:*post*", "gql:*page*"],
        )
        result = data.get(mutation_key, {}).get(result_key)
        if not result:
            return {"error": f"Failed to create {post_type}"}
        return _format_post(result)

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
        context: dict | None = None,
    ) -> dict[str, Any]:
        """Update an existing WordPress post or page.

        Args:
            post_id: The WordPress database ID of the post/page to update.
            title: New title (optional).
            content: New content in WordPress block format (optional).
            status: New status (optional).
            featured_image_id: Database ID of the featured image (optional, use 0 to remove).
            category_ids: List of category database IDs to assign (optional, posts only).
            tag_ids: List of tag database IDs to assign (optional, posts only).
            date: ISO 8601 date string. Future dates schedule the post (optional).

        Returns:
            The updated post/page object.
        """
        connection_id, user_id = get_connection_info(context)
        client = await get_graphql_client(connection_id, user_id)

        # First, determine if this is a post or page by trying to fetch it
        is_page = False
        try:
            page_data = await client.query(
                GET_PAGE,
                variables={"id": str(post_id)},
                user_id=user_id,
            )
            if page_data.get("page"):
                is_page = True
        except Exception:
            # If page query fails, assume it's a post
            pass

        input_data: dict[str, Any] = {"id": str(post_id)}
        if title is not None:
            input_data["title"] = title
        if content is not None:
            input_data["content"] = content
        if status is not None:
            input_data["status"] = status.upper()
        if featured_image_id is not None:
            input_data["featuredImageId"] = str(featured_image_id) if featured_image_id > 0 else None

        # Categories and tags only apply to posts, not pages
        if not is_page:
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

        # Use appropriate mutation based on type
        if is_page:
            mutation = UPDATE_PAGE
            mutation_key = "updatePage"
            result_key = "page"
        else:
            mutation = UPDATE_POST
            mutation_key = "updatePost"
            result_key = "post"

        data = await client.mutate(
            mutation,
            variables={"input": input_data},
            invalidate_patterns=["gql:*post*", "gql:*page*"],
        )
        result = data.get(mutation_key, {}).get(result_key)
        if not result:
            return {"error": f"Failed to update {'page' if is_page else 'post'} {post_id}"}
        return _format_post(result)

    @mcp.tool()
    async def delete_post(post_id: int, context: dict | None = None) -> dict[str, Any]:
        """Delete a WordPress post by its database ID.

        Args:
            post_id: The WordPress database ID of the post to delete.

        Returns:
            Confirmation with deleted post title and id.
        """
        connection_id, user_id = get_connection_info(context)
        client = await get_graphql_client(connection_id, user_id)

        data = await client.mutate(
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


def _format_post_summary(post: dict[str, Any], post_type: str = "post") -> dict[str, Any]:
    """Format a post for the summary list."""
    # Generate slug from title if WordPress doesn't provide one (drafts)
    slug = post.get("slug")
    if not slug:
        title = post.get("title", "")
        slug = title.lower().replace(" ", "-").replace("_", "-") if title else f"post-{post.get('databaseId', '')}"

    result = {
        "id": post.get("databaseId"),
        "title": post.get("title", ""),
        "slug": slug,
        "status": post.get("status", "").lower(),
        "date": post.get("date", ""),
        "modified": post.get("modified", ""),
        "excerpt": post.get("excerpt", ""),
        "author": (post.get("author") or {}).get("node", {}).get("name", ""),
        "type": post_type,
    }

    # Add featured image if present
    featured_image = (post.get("featuredImage") or {}).get("node")
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
    # Generate slug from title if WordPress doesn't provide one (drafts)
    slug = post.get("slug")
    if not slug:
        title = post.get("title", "")
        slug = title.lower().replace(" ", "-").replace("_", "-") if title else f"post-{post.get('databaseId', '')}"

    result = {
        "id": post.get("databaseId"),
        "title": post.get("title", ""),
        "slug": slug,
        "status": post.get("status", "").lower(),
        "content": post.get("content", ""),
        "date": post.get("date", ""),
        "modified": post.get("modified", ""),
        "author": (post.get("author") or {}).get("node", {}).get("name", ""),
    }

    # Add featured image if present
    featured_image = (post.get("featuredImage") or {}).get("node")
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
    categories = (post.get("categories") or {}).get("nodes", [])
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
    tags = (post.get("tags") or {}).get("nodes", [])
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

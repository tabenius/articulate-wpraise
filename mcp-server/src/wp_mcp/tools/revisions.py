"""WordPress revision operations."""

from __future__ import annotations

import subprocess
from typing import Any, cast

from mcp.server.fastmcp import FastMCP

from wp_mcp.graphql.client import gql_client
from wp_mcp.graphql.queries import GET_POST_REVISIONS, GET_REVISION_DETAILS, GET_POST


def register(mcp: FastMCP) -> None:
    """Register revision-related tools with the MCP server."""

    @mcp.tool()
    async def get_post_revisions(post_id: int, limit: int = 20) -> list[dict[str, Any]]:
        """Get revision history for a post.

        Args:
            post_id: WordPress post database ID
            limit: Maximum number of revisions to return (default 20)

        Returns:
            List of revisions with id, date, author, title preview
        """
        result = await gql_client.query(
            GET_POST_REVISIONS, variables={"id": str(post_id), "first": limit}
        )

        post = result.get("post")
        if not post:
            return []

        revisions = post.get("revisions", {}).get("nodes", [])

        return [
            {
                "id": rev["databaseId"],
                "date": rev["date"],
                "author": rev["author"]["node"]["name"],
                "title": rev["title"][:50] if rev["title"] else "",
                "contentPreview": rev["content"][:200] if rev["content"] else "",
            }
            for rev in revisions
        ]

    @mcp.tool()
    async def compare_revisions(
        post_id: int, revision_id_1: int, revision_id_2: int
    ) -> dict[str, Any]:
        """Compare two post revisions.

        Args:
            post_id: WordPress post database ID
            revision_id_1: First revision ID
            revision_id_2: Second revision ID

        Returns:
            Comparison data with both revision contents
        """
        result1 = await gql_client.query(
            GET_REVISION_DETAILS, variables={"id": str(revision_id_1)}
        )
        result2 = await gql_client.query(
            GET_REVISION_DETAILS, variables={"id": str(revision_id_2)}
        )

        return {
            "revision1": result1.get("post"),
            "revision2": result2.get("post"),
        }

    @mcp.tool()
    async def restore_revision(post_id: int, revision_id: int) -> dict[str, Any]:
        """Restore a post to a previous revision.

        Args:
            post_id: WordPress post database ID
            revision_id: Revision ID to restore

        Returns:
            Success message with restored post ID
        """
        # Use WP-CLI to restore revision (GraphQL doesn't support this directly)
        result = subprocess.run(
            [
                "wp",
                "post",
                "update",
                str(post_id),
                "--from-revision",
                str(revision_id),
                "--allow-root",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to restore revision: {result.stderr}")

        # Fetch updated post
        updated_result = await gql_client.query(GET_POST, variables={"id": str(post_id)})

        return cast(dict[str, Any], updated_result.get("post", {}))

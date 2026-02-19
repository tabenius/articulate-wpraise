"""MCP tools for WordPress block operations."""

from __future__ import annotations

from typing import Any, cast

from mcp.server.fastmcp import FastMCP

from wp_mcp.blocks.parser import flat_blocks_to_tree, parse_blocks
from wp_mcp.blocks.serializer import serialize_blocks
from wp_mcp.blocks.types import Block
from wp_mcp.graphql.client import gql_client
from wp_mcp.graphql.queries import GET_POST, GET_POST_WITH_BLOCKS
from wp_mcp.graphql.mutations import UPDATE_POST


def register(mcp: FastMCP) -> None:
    """Register block-related tools with the MCP server."""

    @mcp.tool()
    async def get_blocks(post_id: int) -> list[dict[str, Any]]:
        """Get the structured block tree for a WordPress post.

        Returns blocks with: name, clientId, attributes, innerBlocks.
        Block types include: core/paragraph, core/heading, core/image,
        core/list, core/quote, core/columns, core/group, etc.

        Args:
            post_id: The WordPress database ID of the post.

        Returns:
            List of block objects in tree structure.
        """
        # Try WPGraphQL Content Blocks first
        try:
            data = await gql_client.query(
                GET_POST_WITH_BLOCKS,
                variables={"id": str(post_id)},
            )
            post = data.get("post")
            if not post:
                return [{"error": f"Post {post_id} not found"}]

            editor_blocks = post.get("editorBlocks", [])
            if editor_blocks:
                return flat_blocks_to_tree(editor_blocks)
        except Exception:
            pass

        # Fallback: parse blocks from raw content
        data = await gql_client.query(
            GET_POST,
            variables={"id": str(post_id)},
        )
        post = data.get("post")
        if not post:
            return [{"error": f"Post {post_id} not found"}]

        content = post.get("content", "")
        blocks = parse_blocks(content)
        return [b.to_dict() for b in blocks]

    @mcp.tool()
    async def update_blocks(
        post_id: int,
        blocks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Update all blocks for a WordPress post.

        Replaces the entire block content of the post.

        Args:
            post_id: The WordPress database ID of the post.
            blocks: List of block dicts. Each should have:
                - name (str): Block type, e.g. "core/paragraph"
                - attributes (dict): Block attributes, e.g. {"content": "Hello"}
                - innerBlocks (list, optional): Nested blocks for containers

        Returns:
            Confirmation with the updated post id and block count.
        """
        serialized = serialize_blocks(cast(list[Block | dict[str, Any]], blocks))

        data = await gql_client.mutate(
            UPDATE_POST,
            variables={"input": {"id": str(post_id), "content": serialized}},
        )
        post = data.get("updatePost", {}).get("post")
        if not post:
            return {"error": f"Failed to update blocks for post {post_id}"}

        return {
            "success": True,
            "postId": post.get("databaseId"),
            "blockCount": len(blocks),
        }

    @mcp.tool()
    async def insert_block(
        post_id: int,
        block: dict[str, Any],
        position: int = -1,
    ) -> dict[str, Any]:
        """Insert a single block into a post at a given position.

        Args:
            post_id: The WordPress database ID of the post.
            block: Block dict with name and attributes.
                Example: {"name": "core/paragraph", "attributes": {"content": "Hello"}}
            position: Position to insert at (0-indexed). -1 means append to end.

        Returns:
            Updated block list with the new block inserted.
        """
        # Get current blocks
        current_blocks = await get_blocks(post_id)
        if current_blocks and isinstance(current_blocks[0], dict) and "error" in current_blocks[0]:
            return current_blocks[0]

        # Insert the new block
        new_block = Block.from_dict(block)
        block_dicts = current_blocks

        if position == -1 or position >= len(block_dicts):
            block_dicts.append(new_block.to_dict())
        else:
            block_dicts.insert(position, new_block.to_dict())

        # Save back
        result = await update_blocks(post_id, block_dicts)
        if "error" in result:
            return cast(dict[str, Any], result)

        return {
            "success": True,
            "postId": post_id,
            "insertedBlock": new_block.to_dict(),
            "position": position if position != -1 else len(block_dicts) - 1,
            "totalBlocks": len(block_dicts),
        }

    @mcp.tool()
    async def remove_block(
        post_id: int,
        client_id: str,
    ) -> dict[str, Any]:
        """Remove a block from a post by its clientId.

        Args:
            post_id: The WordPress database ID of the post.
            client_id: The clientId of the block to remove.

        Returns:
            Confirmation with updated block count.
        """
        current_blocks = await get_blocks(post_id)
        if current_blocks and isinstance(current_blocks[0], dict) and "error" in current_blocks[0]:
            return current_blocks[0]

        filtered = _remove_block_recursive(current_blocks, client_id)
        if len(filtered) == len(current_blocks):
            return {"error": f"Block with clientId '{client_id}' not found"}

        result = await update_blocks(post_id, filtered)
        if "error" in result:
            return cast(dict[str, Any], result)

        return {
            "success": True,
            "postId": post_id,
            "removedClientId": client_id,
            "totalBlocks": len(filtered),
        }

    @mcp.tool()
    async def move_block(
        post_id: int,
        client_id: str,
        new_position: int,
    ) -> dict[str, Any]:
        """Move a block to a new position within the post.

        Args:
            post_id: The WordPress database ID of the post.
            client_id: The clientId of the block to move.
            new_position: The target position (0-indexed).

        Returns:
            Confirmation with the block's new position.
        """
        current_blocks = await get_blocks(post_id)
        if current_blocks and isinstance(current_blocks[0], dict) and "error" in current_blocks[0]:
            return current_blocks[0]

        # Find and extract the block
        block_to_move = None
        remaining: list[dict[str, Any]] = []
        for block in current_blocks:
            if block.get("clientId") == client_id:
                block_to_move = block
            else:
                remaining.append(block)

        if block_to_move is None:
            return {"error": f"Block with clientId '{client_id}' not found"}

        # Insert at new position
        pos = max(0, min(new_position, len(remaining)))
        remaining.insert(pos, block_to_move)

        result = await update_blocks(post_id, remaining)
        if "error" in result:
            return cast(dict[str, Any], result)

        return {
            "success": True,
            "postId": post_id,
            "movedClientId": client_id,
            "newPosition": pos,
            "totalBlocks": len(remaining),
        }


def _remove_block_recursive(
    blocks: list[dict[str, Any]], client_id: str
) -> list[dict[str, Any]]:
    """Remove a block by clientId from a potentially nested block list."""
    result: list[dict[str, Any]] = []
    for block in blocks:
        if block.get("clientId") == client_id:
            continue
        inner = block.get("innerBlocks", [])
        if inner:
            block = {**block, "innerBlocks": _remove_block_recursive(inner, client_id)}
        result.append(block)
    return result

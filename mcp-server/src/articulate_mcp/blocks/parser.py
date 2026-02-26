"""Parser for WordPress block HTML format.

WordPress stores blocks as serialized HTML comments in post_content:
    <!-- wp:paragraph {"align":"center"} -->
    <p class="has-text-align-center">Hello World</p>
    <!-- /wp:paragraph -->

This module parses that format into structured Block objects.
"""

from __future__ import annotations

import json
import re
from typing import Any

from articulate_mcp.blocks.types import Block

# Match opening block comment: <!-- wp:namespace/block {"attrs":"here"} -->
# Or self-closing: <!-- wp:namespace/block {"attrs":"here"} /-->
BLOCK_OPEN_RE = re.compile(
    r"<!--\s+wp:([a-z][a-z0-9-]*/)?([a-z][a-z0-9-]*)\s*"
    r"(\{[^}]*\})?\s*"
    r"(/?)\s*-->"
)

# Match closing block comment: <!-- /wp:namespace/block -->
BLOCK_CLOSE_RE = re.compile(
    r"<!--\s+/wp:([a-z][a-z0-9-]*/)?([a-z][a-z0-9-]*)\s*-->"
)


def parse_blocks(content: str) -> list[Block]:
    """Parse WordPress block content into a list of Block objects.

    Args:
        content: The raw post_content from WordPress.

    Returns:
        A list of top-level Block objects (may contain inner_blocks).
    """
    if not content or not content.strip():
        return []

    blocks: list[Block] = []
    pos = 0

    while pos < len(content):
        # Try to match an opening block comment
        match = BLOCK_OPEN_RE.search(content, pos)
        if not match:
            # No more blocks found. Check for remaining non-block content.
            remaining = content[pos:].strip()
            if remaining:
                # Freeform content (not wrapped in block comments)
                blocks.append(Block(
                    name="core/freeform",
                    attributes={},
                    inner_html=remaining,
                ))
            break

        # If there's content before the block, capture it as freeform
        pre_content = content[pos:match.start()].strip()
        if pre_content:
            blocks.append(Block(
                name="core/freeform",
                attributes={},
                inner_html=pre_content,
            ))

        namespace = match.group(1) or "core/"
        block_name_short = match.group(2)
        block_name = f"{namespace}{block_name_short}"
        attrs_json = match.group(3)
        self_closing = match.group(4) == "/"

        # Parse attributes
        attributes: dict[str, Any] = {}
        if attrs_json:
            try:
                attributes = json.loads(attrs_json)
            except json.JSONDecodeError:
                pass

        if self_closing:
            # Self-closing block: <!-- wp:spacer /-->
            blocks.append(Block(
                name=block_name,
                attributes=attributes,
                inner_html="",
            ))
            pos = match.end()
        else:
            # Find matching closing tag
            close_pos = _find_closing_tag(content, block_name, match.end())
            if close_pos == -1:
                # No closing tag found, treat rest as this block's content
                inner = content[match.end():]
                blocks.append(Block(
                    name=block_name,
                    attributes=attributes,
                    inner_html=inner.strip(),
                ))
                break

            # Extract inner content
            close_match = BLOCK_CLOSE_RE.search(content, close_pos)
            inner = content[match.end():close_pos].strip()

            # Recursively parse inner blocks
            inner_blocks = parse_blocks(inner) if _has_block_comments(inner) else []

            block = Block(
                name=block_name,
                attributes=attributes,
                inner_blocks=inner_blocks,
                inner_html=inner if not inner_blocks else "",
            )
            blocks.append(block)

            pos = close_match.end() if close_match else close_pos

    return blocks


def _find_closing_tag(content: str, block_name: str, start: int) -> int:
    """Find the position of the matching closing tag, handling nesting.

    Args:
        content: The full content string.
        block_name: The block name to match (e.g., "core/columns").
        start: Position to start searching from.

    Returns:
        Position of the closing comment start, or -1 if not found.
    """
    # Build patterns for this specific block
    namespace, name = block_name.rsplit("/", 1) if "/" in block_name else ("core", block_name)
    ns_pattern = f"{namespace}/" if namespace != "core" else f"(?:{namespace}/)?"

    open_pattern = re.compile(
        rf"<!--\s+wp:{ns_pattern}{re.escape(name)}\s*(?:\{{[^}}]*\}})?\s*-->"
    )
    close_pattern = re.compile(
        rf"<!--\s+/wp:{ns_pattern}{re.escape(name)}\s*-->"
    )

    depth = 1
    pos = start

    while pos < len(content) and depth > 0:
        next_open = open_pattern.search(content, pos)
        next_close = close_pattern.search(content, pos)

        if next_close is None:
            return -1

        if next_open and next_open.start() < next_close.start():
            # Found a nested opening tag
            # But skip self-closing blocks
            full_match = content[next_open.start():next_open.end()]
            if not full_match.rstrip().endswith("/-->"):
                depth += 1
            pos = next_open.end()
        else:
            depth -= 1
            if depth == 0:
                return next_close.start()
            pos = next_close.end()

    return -1


def _has_block_comments(content: str) -> bool:
    """Check if content contains block comments."""
    return "<!-- wp:" in content


def flat_blocks_to_tree(flat_blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert WPGraphQL flat block list to a tree structure.

    WPGraphQL's editorBlocks(flat: true) returns blocks with clientId
    and parentClientId. This reconstructs the tree.

    Args:
        flat_blocks: List of block dicts with clientId and parentClientId.

    Returns:
        List of top-level block dicts with nested innerBlocks.
    """
    blocks_by_id: dict[str, dict[str, Any]] = {}
    roots: list[dict[str, Any]] = []

    # Index all blocks
    for block in flat_blocks:
        block_copy = {**block, "innerBlocks": []}
        blocks_by_id[block["clientId"]] = block_copy

    # Build tree
    for block in flat_blocks:
        parent_id = block.get("parentClientId")
        block_copy = blocks_by_id[block["clientId"]]

        if parent_id and parent_id in blocks_by_id:
            blocks_by_id[parent_id]["innerBlocks"].append(block_copy)
        else:
            roots.append(block_copy)

    return roots

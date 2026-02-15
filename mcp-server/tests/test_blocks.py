"""Tests for block parser and serializer."""

from wp_mcp.blocks.parser import parse_blocks
from wp_mcp.blocks.serializer import serialize_blocks
from wp_mcp.blocks.types import Block


def test_parse_empty_content():
    """Empty content should return no blocks."""
    assert parse_blocks("") == []
    assert parse_blocks("   ") == []


def test_parse_single_paragraph():
    """Parse a single paragraph block."""
    content = """<!-- wp:paragraph -->
<p>Hello World</p>
<!-- /wp:paragraph -->"""
    blocks = parse_blocks(content)
    assert len(blocks) == 1
    assert blocks[0].name == "core/paragraph"


def test_parse_heading_with_attributes():
    """Parse a heading block with JSON attributes."""
    content = """<!-- wp:heading {"level":1} -->
<h1 class="wp-block-heading">Title</h1>
<!-- /wp:heading -->"""
    blocks = parse_blocks(content)
    assert len(blocks) == 1
    assert blocks[0].name == "core/heading"
    assert blocks[0].attributes.get("level") == 1


def test_parse_self_closing_block():
    """Parse a self-closing block like separator."""
    content = """<!-- wp:separator /-->"""
    blocks = parse_blocks(content)
    assert len(blocks) == 1
    assert blocks[0].name == "core/separator"


def test_parse_multiple_blocks(sample_block_content):
    """Parse multiple blocks including nested ones."""
    blocks = parse_blocks(sample_block_content)
    # Should find heading, paragraph, list, quote, separator, columns
    assert len(blocks) >= 5
    names = [b.name for b in blocks]
    assert "core/heading" in names
    assert "core/paragraph" in names
    assert "core/list" in names


def test_parse_nested_blocks():
    """Parse blocks with inner blocks (columns)."""
    content = """<!-- wp:columns -->
<div class="wp-block-columns">
<!-- wp:column -->
<div class="wp-block-column">
<!-- wp:paragraph -->
<p>Inner paragraph</p>
<!-- /wp:paragraph -->
</div>
<!-- /wp:column -->
</div>
<!-- /wp:columns -->"""
    blocks = parse_blocks(content)
    assert len(blocks) == 1
    assert blocks[0].name == "core/columns"
    assert len(blocks[0].inner_blocks) >= 1


def test_serialize_paragraph():
    """Serialize a paragraph block."""
    blocks = [
        {"name": "core/paragraph", "attributes": {"content": "Hello"}, "innerBlocks": []}
    ]
    result = serialize_blocks(blocks)
    assert "<!-- wp:paragraph" in result
    assert "Hello" in result
    assert "<!-- /wp:paragraph -->" in result


def test_serialize_heading():
    """Serialize a heading block with level."""
    blocks = [
        {"name": "core/heading", "attributes": {"content": "Title", "level": 1}, "innerBlocks": []}
    ]
    result = serialize_blocks(blocks)
    assert "<!-- wp:heading" in result
    assert "<h1" in result
    assert "Title" in result


def test_serialize_self_closing():
    """Serialize a self-closing block (spacer)."""
    blocks = [
        {"name": "core/spacer", "attributes": {"height": "50px"}, "innerBlocks": []}
    ]
    result = serialize_blocks(blocks)
    assert "<!-- wp:spacer" in result
    assert "/-->" in result


def test_block_to_dict():
    """Block.to_dict should produce a serializable dict."""
    block = Block(
        name="core/paragraph",
        attributes={"content": "test"},
        client_id="abc-123",
    )
    d = block.to_dict()
    assert d["name"] == "core/paragraph"
    assert d["clientId"] == "abc-123"
    assert d["attributes"]["content"] == "test"
    assert d["innerBlocks"] == []


def test_block_from_dict():
    """Block.from_dict should reconstruct a block."""
    data = {
        "name": "core/heading",
        "clientId": "xyz-789",
        "attributes": {"content": "Test", "level": 3},
        "innerBlocks": [],
    }
    block = Block.from_dict(data)
    assert block.name == "core/heading"
    assert block.client_id == "xyz-789"
    assert block.attributes["level"] == 3


def test_roundtrip_simple(sample_blocks):
    """Blocks should survive a serialize -> parse roundtrip."""
    serialized = serialize_blocks(sample_blocks)
    parsed = parse_blocks(serialized)
    assert len(parsed) == len(sample_blocks)
    for original, parsed_block in zip(sample_blocks, parsed):
        assert parsed_block.name == original["name"]

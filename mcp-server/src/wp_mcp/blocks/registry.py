"""Registry of known WordPress block types and their default attributes."""

from typing import Any

# Maps block name to default attribute schema
BLOCK_REGISTRY: dict[str, dict[str, Any]] = {
    "core/paragraph": {
        "content": "",
        "align": None,
        "className": None,
        "dropCap": False,
    },
    "core/heading": {
        "content": "",
        "level": 2,
        "textAlign": None,
        "className": None,
    },
    "core/image": {
        "url": "",
        "alt": "",
        "caption": "",
        "width": None,
        "height": None,
        "className": None,
        "sizeSlug": "large",
    },
    "core/list": {
        "ordered": False,
        "values": "",
        "className": None,
    },
    "core/list-item": {
        "content": "",
        "className": None,
    },
    "core/quote": {
        "value": "",
        "citation": "",
        "className": None,
    },
    "core/code": {
        "content": "",
        "className": None,
    },
    "core/columns": {
        "verticalAlignment": None,
        "className": None,
    },
    "core/column": {
        "width": None,
        "verticalAlignment": None,
        "className": None,
    },
    "core/group": {
        "tagName": "div",
        "className": None,
    },
    "core/buttons": {
        "className": None,
    },
    "core/button": {
        "text": "",
        "url": "",
        "className": None,
    },
    "core/spacer": {
        "height": "100px",
        "className": None,
    },
    "core/separator": {
        "className": None,
        "opacity": "alpha-channel",
    },
    "core/table": {
        "hasFixedLayout": False,
        "className": None,
    },
    "core/embed": {
        "url": "",
        "type": None,
        "providerNameSlug": None,
        "className": None,
    },
    "core/html": {
        "content": "",
    },
    "core/preformatted": {
        "content": "",
        "className": None,
    },
    "core/pullquote": {
        "value": "",
        "citation": "",
        "className": None,
    },
    "core/verse": {
        "content": "",
        "className": None,
    },
    "core/cover": {
        "url": "",
        "alt": "",
        "dimRatio": 50,
        "className": None,
    },
    "core/media-text": {
        "mediaAlt": "",
        "mediaUrl": "",
        "mediaType": "image",
        "className": None,
    },
}

# Blocks that can contain inner blocks
CONTAINER_BLOCKS = {
    "core/columns",
    "core/column",
    "core/group",
    "core/buttons",
    "core/cover",
    "core/media-text",
    "core/quote",
    "core/list",
}


def get_default_attributes(block_name: str) -> dict[str, Any]:
    """Get default attributes for a block type."""
    defaults = BLOCK_REGISTRY.get(block_name, {})
    return {k: v for k, v in defaults.items() if v is not None}


def is_container_block(block_name: str) -> bool:
    """Check if a block type can contain inner blocks."""
    return block_name in CONTAINER_BLOCKS

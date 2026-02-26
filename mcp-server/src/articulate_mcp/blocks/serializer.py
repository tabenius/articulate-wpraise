"""Serializer for converting structured blocks back to WordPress block HTML format.

Converts Block objects or dicts to the WordPress block comment format:
    <!-- wp:paragraph {"align":"center"} -->
    <p class="has-text-align-center">Hello World</p>
    <!-- /wp:paragraph -->
"""

from __future__ import annotations

import json
from typing import Any, cast

from articulate_mcp.blocks.registry import is_container_block
from articulate_mcp.blocks.types import Block


def serialize_blocks(blocks: list[Block | dict[str, Any]]) -> str:
    """Serialize a list of blocks to WordPress block HTML format.

    Args:
        blocks: List of Block objects or block dicts.

    Returns:
        WordPress block HTML string ready for post_content.
    """
    parts: list[str] = []
    for block in blocks:
        if isinstance(block, dict):
            block = Block.from_dict(block)
        parts.append(serialize_block(block))
    return "\n\n".join(parts)


def serialize_block(block: Block) -> str:
    """Serialize a single block to WordPress block HTML format.

    Args:
        block: A Block object.

    Returns:
        The serialized block HTML string.
    """
    name = block.name
    attrs = _clean_attributes(block.attributes)

    # Build the opening comment
    attrs_str = ""
    if attrs:
        attrs_str = " " + json.dumps(attrs, separators=(",", ":"))

    # Self-closing blocks (no content, no inner blocks)
    if not block.inner_blocks and not block.inner_html and _is_void_block(name):
        return f"<!-- wp:{name}{attrs_str} /-->"

    # Build inner content
    if block.inner_blocks:
        inner_parts = [serialize_block(b) for b in block.inner_blocks]
        inner_content = "\n".join(inner_parts)
    elif block.inner_html:
        inner_content = block.inner_html
    else:
        inner_content = _generate_html(name, block.attributes)

    return f"<!-- wp:{name}{attrs_str} -->\n{inner_content}\n<!-- /wp:{name} -->"


def _clean_attributes(attrs: dict[str, Any]) -> dict[str, Any]:
    """Remove None values and defaults from attributes for cleaner output."""
    return {k: v for k, v in attrs.items() if v is not None}


def _is_void_block(name: str) -> bool:
    """Check if a block type is typically self-closing."""
    return name in {
        "core/spacer",
        "core/separator",
        "core/nextpage",
        "core/more",
    }


def _generate_html(name: str, attributes: dict[str, Any]) -> str:
    """Generate the inner HTML markup for a block based on its type and attributes.

    Args:
        name: Block name (e.g., "core/paragraph").
        attributes: Block attributes.

    Returns:
        HTML markup string.
    """
    generators = {
        "core/paragraph": _gen_paragraph,
        "core/heading": _gen_heading,
        "core/image": _gen_image,
        "core/list": _gen_list,
        "core/quote": _gen_quote,
        "core/code": _gen_code,
        "core/button": _gen_button,
        "core/buttons": _gen_buttons,
        "core/columns": _gen_columns,
        "core/column": _gen_column,
        "core/group": _gen_group,
        "core/html": _gen_html,
        "core/preformatted": _gen_preformatted,
        "core/verse": _gen_verse,
        "core/table": _gen_table,
    }

    generator = generators.get(name)
    if generator:
        return generator(attributes)

    # Default: empty div
    content = attributes.get("content", "")
    return f"<div>{content}</div>" if content else "<div></div>"


def _gen_paragraph(attrs: dict[str, Any]) -> str:
    content = attrs.get("content", "")
    classes = [""]
    if attrs.get("align"):
        classes.append(f"has-text-align-{attrs['align']}")
    if attrs.get("className"):
        classes.append(attrs["className"])
    class_attr = f' class="{" ".join(c for c in classes if c)}"' if any(classes[1:]) else ""
    return f"<p{class_attr}>{content}</p>"


def _gen_heading(attrs: dict[str, Any]) -> str:
    content = attrs.get("content", "")
    level = attrs.get("level", 2)
    classes = []
    if attrs.get("textAlign"):
        classes.append(f"has-text-align-{attrs['textAlign']}")
    if attrs.get("className"):
        classes.append(attrs["className"])
    class_attr = f' class="wp-block-heading {" ".join(classes)}"' if classes else ' class="wp-block-heading"'
    return f"<h{level}{class_attr}>{content}</h{level}>"


def _gen_image(attrs: dict[str, Any]) -> str:
    url = attrs.get("url", "")
    alt = attrs.get("alt", "")
    caption = attrs.get("caption", "")
    width = attrs.get("width")
    height = attrs.get("height")

    size_attrs = ""
    if width:
        size_attrs += f' width="{width}"'
    if height:
        size_attrs += f' height="{height}"'

    img = f'<img src="{url}" alt="{alt}"{size_attrs}/>'
    caption_html = f"\n<figcaption class=\"wp-element-caption\">{caption}</figcaption>" if caption else ""
    return f'<figure class="wp-block-image">{img}{caption_html}</figure>'


def _gen_list(attrs: dict[str, Any]) -> str:
    values = attrs.get("values", "")
    ordered = attrs.get("ordered", False)
    tag = "ol" if ordered else "ul"
    class_name = attrs.get("className", "")
    class_attr = f' class="wp-block-list {class_name}"' if class_name else ' class="wp-block-list"'
    if values:
        return f"<{tag}{class_attr}>{values}</{tag}>"
    return f"<{tag}{class_attr}></{tag}>"


def _gen_quote(attrs: dict[str, Any]) -> str:
    value = attrs.get("value", "")
    citation = attrs.get("citation", "")
    cite_html = f"<cite>{citation}</cite>" if citation else ""
    return f'<blockquote class="wp-block-quote">{value}{cite_html}</blockquote>'


def _gen_code(attrs: dict[str, Any]) -> str:
    content = attrs.get("content", "")
    return f'<pre class="wp-block-code"><code>{content}</code></pre>'


def _gen_button(attrs: dict[str, Any]) -> str:
    text = attrs.get("text", "")
    url = attrs.get("url", "")
    if url:
        return f'<div class="wp-block-button"><a class="wp-block-button__link" href="{url}">{text}</a></div>'
    return f'<div class="wp-block-button"><span class="wp-block-button__link">{text}</span></div>'


def _gen_buttons(attrs: dict[str, Any]) -> str:
    return '<div class="wp-block-buttons"></div>'


def _gen_columns(attrs: dict[str, Any]) -> str:
    return '<div class="wp-block-columns"></div>'


def _gen_column(attrs: dict[str, Any]) -> str:
    width = attrs.get("width")
    style = f' style="flex-basis:{width}"' if width else ""
    return f'<div class="wp-block-column"{style}></div>'


def _gen_group(attrs: dict[str, Any]) -> str:
    tag = attrs.get("tagName", "div")
    return f'<{tag} class="wp-block-group"></{tag}>'


def _gen_html(attrs: dict[str, Any]) -> str:
    return cast(str, attrs.get("content", ""))


def _gen_preformatted(attrs: dict[str, Any]) -> str:
    content = attrs.get("content", "")
    return f'<pre class="wp-block-preformatted">{content}</pre>'


def _gen_verse(attrs: dict[str, Any]) -> str:
    content = attrs.get("content", "")
    return f'<pre class="wp-block-verse">{content}</pre>'


def _gen_table(attrs: dict[str, Any]) -> str:
    return '<figure class="wp-block-table"><table><tbody></tbody></table></figure>'

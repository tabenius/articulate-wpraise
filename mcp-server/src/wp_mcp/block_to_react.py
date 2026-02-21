"""Convert WordPress blocks to React components."""

from __future__ import annotations

import json
import re
from typing import Any


class BlockToReactConverter:
    """Convert WordPress block structure to React components."""

    @staticmethod
    def convert_blocks(content: str) -> str:
        """Convert WordPress block HTML to React components.

        Args:
            content: WordPress post/page content with block comments

        Returns:
            React JSX code as string
        """
        blocks = BlockToReactConverter._parse_blocks(content)
        jsx_lines = []

        for block in blocks:
            jsx = BlockToReactConverter._block_to_jsx(block)
            if jsx:
                jsx_lines.append(jsx)

        return "\n\n".join(jsx_lines)

    @staticmethod
    def _parse_blocks(content: str) -> list[dict[str, Any]]:
        """Parse WordPress blocks from HTML content.

        Args:
            content: Raw HTML with WordPress block comments

        Returns:
            List of block dictionaries
        """
        blocks = []

        # Simple block comment pattern
        block_pattern = r"<!-- wp:(\S+)(?:\s+({.*?}))?\s*(?:/)?(-->)(.*?)(?:<!-- /wp:\1 -->|$)"

        matches = re.finditer(block_pattern, content, re.DOTALL)

        for match in matches:
            block_name = match.group(1)
            attrs_json = match.group(2)
            is_self_closing = match.group(3) == "/-->"
            inner_html = match.group(4).strip() if not is_self_closing else ""

            attributes = {}
            if attrs_json:
                try:
                    attributes = json.loads(attrs_json)
                except json.JSONDecodeError:
                    pass

            blocks.append({
                "blockName": block_name,
                "attrs": attributes,
                "innerHTML": inner_html,
                "innerBlocks": [],
            })

        return blocks

    @staticmethod
    def _block_to_jsx(block: dict[str, Any], indent: int = 0) -> str:
        """Convert a single block to JSX.

        Args:
            block: Block dictionary
            indent: Indentation level

        Returns:
            JSX code as string
        """
        block_name = block.get("blockName", "")
        attrs = block.get("attrs", {})
        inner_html = block.get("innerHTML", "")
        inner_blocks = block.get("innerBlocks", [])

        # Core block conversions
        if block_name == "core/paragraph":
            return BlockToReactConverter._convert_paragraph(attrs, inner_html, indent)
        elif block_name == "core/heading":
            return BlockToReactConverter._convert_heading(attrs, inner_html, indent)
        elif block_name == "core/image":
            return BlockToReactConverter._convert_image(attrs, inner_html, indent)
        elif block_name == "core/list":
            return BlockToReactConverter._convert_list(attrs, inner_html, indent)
        elif block_name == "core/quote":
            return BlockToReactConverter._convert_quote(attrs, inner_html, indent)
        elif block_name == "core/code":
            return BlockToReactConverter._convert_code(attrs, inner_html, indent)
        elif block_name == "core/button":
            return BlockToReactConverter._convert_button(attrs, inner_html, indent)
        elif block_name == "core/columns":
            return BlockToReactConverter._convert_columns(attrs, inner_blocks, indent)
        elif block_name == "core/group":
            return BlockToReactConverter._convert_group(attrs, inner_blocks, indent)
        else:
            # Fallback: render as HTML
            return BlockToReactConverter._convert_fallback(block_name, inner_html, indent)

    @staticmethod
    def _convert_paragraph(attrs: dict, inner_html: str, indent: int) -> str:
        """Convert paragraph block to JSX."""
        content = BlockToReactConverter._clean_html(inner_html)
        className = attrs.get("className", "")

        class_attr = f' className="{className}"' if className else ""

        if content:
            return f"<p{class_attr}>{content}</p>"
        return ""

    @staticmethod
    def _convert_heading(attrs: dict, inner_html: str, indent: int) -> str:
        """Convert heading block to JSX."""
        level = attrs.get("level", 2)
        content = BlockToReactConverter._clean_html(inner_html)
        className = attrs.get("className", "")

        class_attr = f' className="{className}"' if className else ""

        return f"<h{level}{class_attr}>{content}</h{level}>"

    @staticmethod
    def _convert_image(attrs: dict, inner_html: str, indent: int) -> str:
        """Convert image block to JSX using Next.js Image."""
        url = attrs.get("url", "")
        alt = attrs.get("alt", "")
        width = attrs.get("width", 800)
        height = attrs.get("height", 600)
        className = attrs.get("className", "")

        if not url:
            return ""

        return f"""<Image
  src="{url}"
  alt="{alt}"
  width={{{width}}}
  height={{{height}}}
  className="{className}"
/>"""

    @staticmethod
    def _convert_list(attrs: dict, inner_html: str, indent: int) -> str:
        """Convert list block to JSX."""
        ordered = attrs.get("ordered", False)
        tag = "ol" if ordered else "ul"
        className = attrs.get("className", "")

        content = BlockToReactConverter._clean_html(inner_html)
        class_attr = f' className="{className}"' if className else ""

        return f"<{tag}{class_attr}>{content}</{tag}>"

    @staticmethod
    def _convert_quote(attrs: dict, inner_html: str, indent: int) -> str:
        """Convert quote block to JSX."""
        content = BlockToReactConverter._clean_html(inner_html)
        className = attrs.get("className", "")

        class_attr = f' className="border-l-4 pl-4 italic {className}"'.strip()

        return f'<blockquote className="{class_attr}">{content}</blockquote>'

    @staticmethod
    def _convert_code(attrs: dict, inner_html: str, indent: int) -> str:
        """Convert code block to JSX."""
        content = BlockToReactConverter._clean_html(inner_html)

        return f"""<pre className="bg-gray-100 p-4 rounded overflow-x-auto">
  <code>{content}</code>
</pre>"""

    @staticmethod
    def _convert_button(attrs: dict, inner_html: str, indent: int) -> str:
        """Convert button block to JSX."""
        text = attrs.get("text", "")
        url = attrs.get("url", "#")
        className = attrs.get("className", "")

        return f"""<Link href="{url}" className="inline-block px-6 py-3 bg-blue-600 text-white rounded hover:bg-blue-700 {className}">
  {text}
</Link>"""

    @staticmethod
    def _convert_columns(attrs: dict, inner_blocks: list, indent: int) -> str:
        """Convert columns block to JSX."""
        columns_jsx = []
        for inner_block in inner_blocks:
            col_jsx = BlockToReactConverter._block_to_jsx(inner_block, indent + 1)
            if col_jsx:
                columns_jsx.append(f'  <div className="column">\n    {col_jsx}\n  </div>')

        columns_content = "\n".join(columns_jsx)

        return f"""<div className="grid grid-cols-1 md:grid-cols-{len(inner_blocks)} gap-4">
{columns_content}
</div>"""

    @staticmethod
    def _convert_group(attrs: dict, inner_blocks: list, indent: int) -> str:
        """Convert group block to JSX."""
        inner_jsx = []
        for inner_block in inner_blocks:
            jsx = BlockToReactConverter._block_to_jsx(inner_block, indent + 1)
            if jsx:
                inner_jsx.append(f"  {jsx}")

        content = "\n".join(inner_jsx)
        className = attrs.get("className", "")

        return f"""<div className="{className}">
{content}
</div>"""

    @staticmethod
    def _convert_fallback(block_name: str, inner_html: str, indent: int) -> str:
        """Fallback conversion for unsupported blocks."""
        content = BlockToReactConverter._clean_html(inner_html)

        if content:
            return f'<div data-block-type="{block_name}">{content}</div>'
        return ""

    @staticmethod
    def _clean_html(html: str) -> str:
        """Clean HTML content for JSX.

        Args:
            html: Raw HTML string

        Returns:
            Cleaned HTML suitable for JSX
        """
        # Remove WordPress block comments
        html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)

        # Strip excessive whitespace
        html = html.strip()

        # Replace class with className (this is basic, a proper parser would be better)
        html = re.sub(r'\bclass=', 'className=', html)

        return html

    @staticmethod
    def generate_component(
        block_content: str,
        component_name: str = "Content",
    ) -> str:
        """Generate a complete React component from WordPress content.

        Args:
            block_content: WordPress block content
            component_name: Name for the generated component

        Returns:
            Complete React component code
        """
        jsx_content = BlockToReactConverter.convert_blocks(block_content)

        # Check if we need Image import
        needs_image = "Image" in jsx_content
        # Check if we need Link import
        needs_link = "Link" in jsx_content

        imports = []
        if needs_image:
            imports.append("import Image from 'next/image'")
        if needs_link:
            imports.append("import Link from 'next/link'")

        import_section = "\n".join(imports) + "\n\n" if imports else ""

        component = f"""{import_section}export default function {component_name}() {{
  return (
    <div className="content">
      {jsx_content}
    </div>
  )
}}
"""

        return component

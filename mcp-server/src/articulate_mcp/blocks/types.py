"""Block type definitions for WordPress Gutenberg blocks."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Block:
    """Represents a single WordPress Gutenberg block."""

    name: str
    attributes: dict[str, Any] = field(default_factory=dict)
    inner_blocks: list[Block] = field(default_factory=list)
    client_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    inner_html: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-serializable dictionary."""
        return {
            "name": self.name,
            "clientId": self.client_id,
            "attributes": self.attributes,
            "innerBlocks": [b.to_dict() for b in self.inner_blocks],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Block:
        """Create a Block from a dictionary."""
        return cls(
            name=data.get("name", "core/paragraph"),
            attributes=data.get("attributes", {}),
            inner_blocks=[cls.from_dict(b) for b in data.get("innerBlocks", [])],
            client_id=data.get("clientId", str(uuid.uuid4())),
            inner_html=data.get("innerHtml", ""),
        )


@dataclass
class BlockTree:
    """Represents the full block tree of a post/page."""

    post_id: int
    blocks: list[Block] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-serializable dictionary."""
        return {
            "postId": self.post_id,
            "blocks": [b.to_dict() for b in self.blocks],
        }

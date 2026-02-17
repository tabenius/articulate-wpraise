"""MCP tools for WordPress operations."""

# Import all tools to register them with the MCP server
from . import posts
from . import media
from . import taxonomies
from . import blocks
from . import revisions
from . import tenants  # Multi-tenancy support

__all__ = ["posts", "media", "taxonomies", "blocks", "revisions", "tenants"]

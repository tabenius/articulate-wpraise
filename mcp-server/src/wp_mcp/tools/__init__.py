"""MCP tools for WordPress operations."""

# Import all tools to register them with the MCP server
from . import posts
from . import media
from . import fonts
from . import preview
from . import taxonomies
from . import blocks
from . import revisions
from . import tenants  # Multi-tenancy support
from . import settings
from . import menus

__all__ = ["posts", "media", "fonts", "preview", "taxonomies", "blocks", "revisions", "tenants", "settings", "menus"]

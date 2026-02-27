"""WordPress Capabilities Checker.

Maps WordPress roles to capabilities and provides pre-flight
permission checking for MCP tool operations.
"""

import logging
from typing import Union

logger = logging.getLogger("articulate-mcp")

# WordPress built-in role capability mappings
ROLE_CAPABILITIES: dict[str, set[str]] = {
    "administrator": {
        "read",
        "edit_posts", "edit_others_posts", "edit_published_posts", "edit_private_posts",
        "publish_posts", "delete_posts", "delete_others_posts", "delete_published_posts", "delete_private_posts",
        "read_private_posts",
        "edit_pages", "edit_others_pages", "edit_published_pages", "edit_private_pages",
        "publish_pages", "delete_pages", "delete_others_pages", "delete_published_pages", "delete_private_pages",
        "read_private_pages",
        "upload_files",
        "manage_categories",
        "manage_options",
        "edit_theme_options",
        "moderate_comments",
        "manage_links",
        "create_users", "edit_users", "delete_users", "list_users", "promote_users",
        "install_plugins", "activate_plugins", "edit_plugins", "delete_plugins",
        "install_themes", "edit_themes", "delete_themes", "switch_themes",
        "unfiltered_html", "unfiltered_upload",
        "export", "import",
    },
    "editor": {
        "read",
        "edit_posts", "edit_others_posts", "edit_published_posts", "edit_private_posts",
        "publish_posts", "delete_posts", "delete_others_posts", "delete_published_posts", "delete_private_posts",
        "read_private_posts",
        "edit_pages", "edit_others_pages", "edit_published_pages", "edit_private_pages",
        "publish_pages", "delete_pages", "delete_others_pages", "delete_published_pages", "delete_private_pages",
        "read_private_pages",
        "upload_files",
        "manage_categories",
        "manage_links",
        "moderate_comments",
        "unfiltered_html",
    },
    "author": {
        "read",
        "edit_posts", "edit_published_posts",
        "publish_posts", "delete_posts", "delete_published_posts",
        "upload_files",
    },
    "contributor": {
        "read",
        "edit_posts", "delete_posts",
    },
    "subscriber": {
        "read",
    },
}

# Map MCP tool operations to required WordPress capabilities
OPERATION_CAPABILITIES: dict[str, list[str]] = {
    "get_posts": ["read"],
    "get_post": ["read"],
    "create_post": ["edit_posts"],
    "update_post": ["edit_posts"],
    "delete_post": ["delete_posts"],
    "publish_post": ["publish_posts"],
    "get_pages": ["read"],
    "get_page": ["read"],
    "create_page": ["edit_pages"],
    "update_page": ["edit_pages"],
    "delete_page": ["delete_pages"],
    "publish_page": ["publish_pages"],
    "upload_media": ["upload_files"],
    "get_media": ["read"],
    "delete_media": ["upload_files"],
    "manage_categories": ["manage_categories"],
    "manage_tags": ["manage_categories"],
    "get_settings": ["manage_options"],
    "update_settings": ["manage_options"],
    "get_front_page_settings": ["manage_options"],
    "set_front_page": ["manage_options"],
    "manage_menus": ["edit_theme_options"],
    "manage_templates": ["edit_theme_options"],
    "list_users": ["list_users"],
    "create_user": ["create_users"],
    "update_user_role": ["promote_users"],
    "delete_user": ["delete_users"],
    "update_seo": ["edit_posts"],
}


class CapabilityChecker:
    """Checks WordPress capabilities for operations."""

    def get_capabilities_for_roles(self, roles: list[str]) -> set[str]:
        """Get the union of capabilities for a list of WordPress roles."""
        caps = set()
        for role in roles:
            role_lower = role.lower()
            if role_lower in ROLE_CAPABILITIES:
                caps |= ROLE_CAPABILITIES[role_lower]
            else:
                logger.warning("Unknown WordPress role: %s, defaulting to subscriber", role)
                caps |= ROLE_CAPABILITIES["subscriber"]
        if not caps:
            caps = {"read"}
        return caps

    def check(
        self,
        roles: list[str],
        required: Union[str, list[str]],
    ) -> tuple[bool, list[str]]:
        """Check if roles have the required capabilities.

        Args:
            roles: List of WordPress role names
            required: Single capability or list of capabilities

        Returns:
            Tuple of (has_all, missing_capabilities)
        """
        if isinstance(required, str):
            required = [required]

        user_caps = self.get_capabilities_for_roles(roles)
        missing = [cap for cap in required if cap not in user_caps]
        return len(missing) == 0, missing

    def get_required_capabilities(self, operation: str) -> list[str]:
        """Get the required WordPress capabilities for an MCP operation."""
        return OPERATION_CAPABILITIES.get(operation, [])

    def check_operation(
        self,
        roles: list[str],
        operation: str,
    ) -> tuple[bool, list[str]]:
        """Check if roles can perform a specific MCP operation.

        Args:
            roles: WordPress role names
            operation: MCP operation name (e.g., 'create_post')

        Returns:
            Tuple of (allowed, missing_capabilities)
        """
        required = self.get_required_capabilities(operation)
        if not required:
            return True, []
        return self.check(roles, required)


# Global instance
capability_checker = CapabilityChecker()

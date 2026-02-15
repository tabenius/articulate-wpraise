"""Configuration for the WordPress MCP server."""

import os
from dataclasses import dataclass, field


@dataclass
class Config:
    """Server configuration loaded from environment variables."""

    wp_url: str = field(default_factory=lambda: os.environ.get("WP_URL", "http://localhost:8080"))
    wp_graphql_endpoint: str = field(
        default_factory=lambda: os.environ.get("WP_GRAPHQL_ENDPOINT", "http://localhost:8080/graphql")
    )
    wp_user: str = field(default_factory=lambda: os.environ.get("WP_USER", "admin"))
    wp_app_password: str = field(default_factory=lambda: os.environ.get("WP_APP_PASSWORD", ""))
    mcp_transport: str = field(default_factory=lambda: os.environ.get("MCP_TRANSPORT", "streamable-http"))
    mcp_host: str = field(default_factory=lambda: os.environ.get("MCP_HOST", "0.0.0.0"))
    mcp_port: int = field(default_factory=lambda: int(os.environ.get("MCP_PORT", "8000")))

    @property
    def wp_auth(self) -> tuple[str, str] | None:
        """Return HTTP Basic Auth tuple for WordPress API."""
        if self.wp_user and self.wp_app_password:
            return (self.wp_user, self.wp_app_password)
        return None


config = Config()

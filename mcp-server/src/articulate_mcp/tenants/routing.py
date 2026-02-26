"""Route resolver for Caddy dynamic upstream resolution."""

import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

VIEW_PORTS = {
    "wordpress": 80,
    "faust": 3000,
    "astro": 4321,
}

VIEWS = set(VIEW_PORTS.keys())

# Control plane subdomains that should not be treated as tenants
RESERVED_SUBDOMAINS = {"app", "my", "www", "api", "docs", "mail", "smtp"}


class RouteResolver:
    """Resolves Host headers to Docker container upstreams."""

    def __init__(self, base_domain: str = "ragbaz.xyz"):
        self.base_domain = base_domain
        self.subdomain_re = re.compile(
            rf"^(?:(?P<view>[^.]+)\.)?(?P<tenant>[^.]+)\.{re.escape(base_domain)}$"
        )

    def parse_host(self, host: str) -> dict[str, Any] | None:
        """Parse a Host header into tenant/view info.

        Returns:
            - {"tenant_name": str, "view": str} for view.tenant.domain
            - {"tenant_name": str, "view": None} for tenant.domain (bare)
            - {"external_domain": str} for external domains
            - None for control plane subdomains
        """
        host = host.split(":")[0].lower()

        match = self.subdomain_re.match(host)
        if match:
            view = match.group("view")
            tenant = match.group("tenant")

            # Control plane subdomains (single level like app.ragbaz.xyz)
            if tenant in RESERVED_SUBDOMAINS and view is None:
                return None

            # view.tenant.ragbaz.xyz
            if view and view in VIEWS:
                return {"tenant_name": tenant, "view": view}

            # tenant.ragbaz.xyz (bare subdomain)
            if view is None:
                return {"tenant_name": tenant, "view": None}

            # Unknown view prefix - not a valid route
            return None

        # Not a subdomain of base_domain — external domain
        if not host.endswith(f".{self.base_domain}") and host != self.base_domain:
            return {"external_domain": host}

        return None

    def upstream_for(self, tenant_id: str, view: str) -> str:
        """Get the Docker upstream address for a tenant view."""
        port = VIEW_PORTS.get(view, 80)
        return f"tenant_{tenant_id}_{view}:{port}"

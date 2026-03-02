"""Route resolver for Caddy dynamic upstream resolution.

Subdomain scheme (flat, single-level for wildcard SSL compatibility):
  - {tenant}.ragbaz.xyz              → bare tenant (uses default view)
  - {view}-{tenant}.ragbaz.xyz       → specific view (wordpress, faust, astro)
  - External domains                  → looked up in tenant_domains table
"""

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

# Subdomains reserved for the control plane
RESERVED_SUBDOMAINS = {"app", "www", "api", "docs", "mail", "smtp"}

# Build regex prefix alternatives from known views: "wordpress-|faust-|astro-"
_VIEW_PREFIX_RE = "|".join(re.escape(v) for v in sorted(VIEWS))


class RouteResolver:
    """Resolves Host headers to Docker container upstreams."""

    def __init__(self, base_domain: str = "ragbaz.xyz"):
        self.base_domain = base_domain
        # Match a single subdomain level: {something}.ragbaz.xyz
        self.subdomain_re = re.compile(
            rf"^(?P<subdomain>[^.]+)\.{re.escape(base_domain)}$"
        )
        # Parse view-tenant from subdomain: {view}-{tenant}
        self.view_tenant_re = re.compile(
            rf"^(?P<view>{_VIEW_PREFIX_RE})-(?P<tenant>.+)$"
        )

    def parse_host(self, host: str) -> dict[str, Any] | None:
        """Parse a Host header into tenant/view info.

        Flat subdomain scheme (single-level, wildcard-cert compatible):
          - {view}-{tenant}.ragbaz.xyz → {"tenant_name": str, "view": str}
          - {tenant}.ragbaz.xyz        → {"tenant_name": str, "view": None}
          - external.example.com       → {"external_domain": str}
          - app.ragbaz.xyz (reserved)  → None

        Returns None for control plane subdomains and invalid hosts.
        """
        host = host.split(":")[0].lower()

        match = self.subdomain_re.match(host)
        if match:
            subdomain = match.group("subdomain")

            # Control plane subdomains
            if subdomain in RESERVED_SUBDOMAINS:
                return None

            # Check for {view}-{tenant} pattern
            vt_match = self.view_tenant_re.match(subdomain)
            if vt_match:
                return {
                    "tenant_name": vt_match.group("tenant"),
                    "view": vt_match.group("view"),
                }

            # Bare tenant subdomain
            return {"tenant_name": subdomain, "view": None}

        # Not a subdomain of base_domain — external domain
        if not host.endswith(f".{self.base_domain}") and host != self.base_domain:
            return {"external_domain": host}

        return None

    def upstream_for(self, tenant_id: str, view: str) -> str:
        """Get the Docker upstream address for a tenant view."""
        port = VIEW_PORTS.get(view, 80)
        return f"tenant_{tenant_id}_{view}:{port}"

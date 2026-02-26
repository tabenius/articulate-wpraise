"""HTTP endpoints for Caddy dynamic upstream resolution."""

import logging
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from articulate_mcp.database import db
from articulate_mcp.tenants.routing import RouteResolver

logger = logging.getLogger(__name__)

resolver = RouteResolver()


async def resolve_upstream(request: Request) -> Response:
    """Caddy calls this to resolve a Host header to an upstream.

    Caddy sends the original Host header. We look up the tenant
    and return the upstream address.

    Returns JSON: [{"dial": "container:port"}] for Caddy dynamic upstreams.
    Returns 404 if no match found.
    """
    host = request.headers.get("X-Forwarded-Host") or request.headers.get("Host", "")
    parsed = resolver.parse_host(host)

    if parsed is None:
        return Response(status_code=404)

    if "external_domain" in parsed:
        # Look up custom domain
        row = await db.fetchone(
            """SELECT t.id, td.target_view
               FROM tenant_domains td
               JOIN tenants t ON t.id = td.tenant_id
               WHERE td.external_domain = %s AND td.verified = TRUE AND t.status = 'running'""",
            (parsed["external_domain"],),
        )
        if not row:
            return Response(status_code=404)
        upstream = resolver.upstream_for(row["id"], row["target_view"])
        return JSONResponse([{"dial": upstream}])

    tenant_name = parsed["tenant_name"]
    view = parsed.get("view")

    # Look up tenant by name
    tenant = await db.fetchone(
        "SELECT id, default_view FROM tenants WHERE name = %s AND status = 'running'",
        (tenant_name,),
    )
    if not tenant:
        return Response(status_code=404)

    if view is None:
        view = tenant["default_view"]

    upstream = resolver.upstream_for(tenant["id"], view)
    return JSONResponse([{"dial": upstream}])


async def tls_check(request: Request) -> Response:
    """Caddy on-demand TLS check.

    Caddy calls GET /routing/tls-check?domain=X before fetching a cert.
    Return 200 to allow, 404 to deny.
    """
    domain = request.query_params.get("domain", "")
    if not domain:
        return Response(status_code=404)

    # Allow all *.ragbaz.xyz (covered by wildcard cert)
    if domain.endswith(".ragbaz.xyz"):
        return Response(status_code=200)

    # Check custom domains
    row = await db.fetchone(
        "SELECT id FROM tenant_domains WHERE external_domain = %s AND verified = TRUE",
        (domain,),
    )
    if row:
        return Response(status_code=200)

    return Response(status_code=404)

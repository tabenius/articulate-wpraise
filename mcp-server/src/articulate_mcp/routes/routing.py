"""Tenant routing: reverse proxy for tenant traffic from Caddy."""

import logging
import httpx
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response, StreamingResponse

from articulate_mcp.database import db
from articulate_mcp.tenants.routing import RouteResolver

logger = logging.getLogger(__name__)

resolver = RouteResolver()

# Hop-by-hop headers that must not be forwarded
_HOP_HEADERS = frozenset({
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade",
})


async def _resolve_upstream(host: str) -> str | None:
    """Resolve a Host header to an upstream address (container:port)."""
    parsed = resolver.parse_host(host)
    if parsed is None:
        return None

    if "external_domain" in parsed:
        row = await db.fetchone(
            """SELECT t.id, td.target_view
               FROM tenant_domains td
               JOIN tenants t ON t.id = td.tenant_id
               WHERE td.external_domain = %s AND td.verified = TRUE AND t.status = 'running'""",
            (parsed["external_domain"],),
        )
        if not row:
            return None
        return resolver.upstream_for(row["id"], row["target_view"])

    tenant_name = parsed["tenant_name"]
    view = parsed.get("view")

    tenant = await db.fetchone(
        "SELECT id, default_view FROM tenants WHERE name = %s AND status = 'running'",
        (tenant_name,),
    )
    if not tenant:
        return None

    if view is None:
        view = tenant["default_view"]

    return resolver.upstream_for(tenant["id"], view)


async def proxy_tenant_request(request: Request) -> Response:
    """Reverse proxy: resolve tenant upstream and forward the full request.

    Caddy sends the original request here. We determine the upstream
    container from the Host header, proxy the request, and stream
    the response back.
    """
    host = request.headers.get("X-Forwarded-Host") or request.headers.get("Host", "")
    upstream = await _resolve_upstream(host)

    if not upstream:
        return RedirectResponse("https://app.ragbaz.xyz", status_code=302)

    # Build upstream URL — strip /routing/proxy prefix added by Caddy
    path = request.path_params.get("path", "")
    if path and not path.startswith("/"):
        path = "/" + path
    if not path:
        path = "/"
    query = request.url.query
    upstream_url = f"http://{upstream}{path}"
    if query:
        upstream_url += f"?{query}"

    # Forward headers (strip hop-by-hop and host — we set Host explicitly)
    fwd_headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in _HOP_HEADERS and k.lower() != "host"
    }
    # Set Host to the upstream so WordPress doesn't redirect
    fwd_headers["Host"] = upstream.split(":")[0]

    body = await request.body()

    async with httpx.AsyncClient(timeout=60.0, follow_redirects=False) as client:
        upstream_resp = await client.request(
            method=request.method,
            url=upstream_url,
            headers=fwd_headers,
            content=body,
        )

    # Filter response hop-by-hop headers
    resp_headers = {
        k: v for k, v in upstream_resp.headers.items()
        if k.lower() not in _HOP_HEADERS
    }

    return Response(
        content=upstream_resp.content,
        status_code=upstream_resp.status_code,
        headers=resp_headers,
    )


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

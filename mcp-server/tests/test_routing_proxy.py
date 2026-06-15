import pytest
from starlette.requests import Request

from articulate_mcp.routes import routing as routing_routes


def _build_request(host: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/routing/proxy",
            "raw_path": b"/routing/proxy",
            "query_string": b"",
            "headers": [(b"host", host.encode("utf-8"))],
            "path_params": {},
        }
    )


@pytest.mark.asyncio
async def test_proxy_tenant_miss_returns_404(monkeypatch):
    request = _build_request("my.ragbaz.cc")

    monkeypatch.setattr(
        routing_routes.resolver,
        "parse_host",
        lambda _: {"tenant_name": "my", "view": None},
    )

    async def _fake_resolve(_host: str) -> str | None:
        return None

    monkeypatch.setattr(routing_routes, "_resolve_upstream", _fake_resolve)

    response = await routing_routes.proxy_tenant_request(request)
    assert response.status_code == 404
    assert response.headers.get("location") is None


@pytest.mark.asyncio
async def test_proxy_control_plane_miss_redirects_to_app(monkeypatch):
    request = _build_request("app.ragbaz.cc")

    monkeypatch.setattr(routing_routes.resolver, "parse_host", lambda _: None)

    async def _fake_resolve(_host: str) -> str | None:
        return None

    monkeypatch.setattr(routing_routes, "_resolve_upstream", _fake_resolve)

    response = await routing_routes.proxy_tenant_request(request)
    assert response.status_code == 302
    assert response.headers.get("location") == "https://app.ragbaz.cc"

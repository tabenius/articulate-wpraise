import pytest
from wp_mcp.tenants.routing import RouteResolver


@pytest.fixture
def resolver():
    return RouteResolver(base_domain="ragbaz.xyz")


def test_parse_view_subdomain(resolver):
    result = resolver.parse_host("faust.tenant1.ragbaz.xyz")
    assert result == {"tenant_name": "tenant1", "view": "faust"}


def test_parse_astro_subdomain(resolver):
    result = resolver.parse_host("astro.mysite.ragbaz.xyz")
    assert result == {"tenant_name": "mysite", "view": "astro"}


def test_parse_wordpress_subdomain(resolver):
    result = resolver.parse_host("wordpress.tenant1.ragbaz.xyz")
    assert result == {"tenant_name": "tenant1", "view": "wordpress"}


def test_parse_bare_subdomain(resolver):
    result = resolver.parse_host("tenant1.ragbaz.xyz")
    assert result == {"tenant_name": "tenant1", "view": None}


def test_parse_external_domain(resolver):
    result = resolver.parse_host("myblog.com")
    assert result == {"external_domain": "myblog.com"}


def test_parse_control_plane_returns_none(resolver):
    assert resolver.parse_host("app.ragbaz.xyz") is None
    assert resolver.parse_host("my.ragbaz.xyz") is None


def test_parse_reserved_subdomains(resolver):
    assert resolver.parse_host("www.ragbaz.xyz") is None
    assert resolver.parse_host("docs.ragbaz.xyz") is None
    assert resolver.parse_host("api.ragbaz.xyz") is None


def test_parse_host_strips_port(resolver):
    result = resolver.parse_host("faust.tenant1.ragbaz.xyz:443")
    assert result == {"tenant_name": "tenant1", "view": "faust"}


def test_parse_host_case_insensitive(resolver):
    result = resolver.parse_host("FAUST.Tenant1.Ragbaz.xyz")
    assert result == {"tenant_name": "tenant1", "view": "faust"}


def test_parse_unknown_view_returns_none(resolver):
    result = resolver.parse_host("unknown.tenant1.ragbaz.xyz")
    assert result is None


def test_upstream_for_wordpress(resolver):
    assert resolver.upstream_for("abc123", "wordpress") == "tenant_abc123_wordpress:80"


def test_upstream_for_faust(resolver):
    assert resolver.upstream_for("abc123", "faust") == "tenant_abc123_faust:3000"


def test_upstream_for_astro(resolver):
    assert resolver.upstream_for("abc123", "astro") == "tenant_abc123_astro:4321"


def test_parse_base_domain_itself(resolver):
    result = resolver.parse_host("ragbaz.xyz")
    assert result is None

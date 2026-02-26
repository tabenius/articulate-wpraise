import os
import yaml
import pytest


@pytest.fixture
def composer():
    from wp_mcp.tenants.composer import TenantComposer
    template_dir = os.path.join(os.path.dirname(__file__), "..", "..", "templates")
    return TenantComposer(template_dir=template_dir)


def test_render_returns_valid_yaml(composer):
    result = composer.render(
        tenant_id="abc123",
        tenant_name="testsite",
        db_password="secret1",
        db_root_password="secret2",
    )
    parsed = yaml.safe_load(result)
    assert parsed["name"] == "tenant_abc123"
    assert "wordpress" in parsed["services"]
    assert "mariadb" in parsed["services"]
    assert "faust" in parsed["services"]
    assert "astro" in parsed["services"]


def test_render_sets_container_names(composer):
    result = composer.render(
        tenant_id="abc123",
        tenant_name="testsite",
        db_password="s",
        db_root_password="s",
    )
    parsed = yaml.safe_load(result)
    assert parsed["services"]["wordpress"]["container_name"] == "tenant_abc123_wordpress"
    assert parsed["services"]["faust"]["container_name"] == "tenant_abc123_faust"
    assert parsed["services"]["astro"]["container_name"] == "tenant_abc123_astro"


def test_render_sets_tenant_network(composer):
    result = composer.render(
        tenant_id="abc123",
        tenant_name="testsite",
        db_password="s",
        db_root_password="s",
    )
    parsed = yaml.safe_load(result)
    assert "tenant_abc123_net" in parsed["networks"]
    assert parsed["networks"]["tenant_abc123_net"]["internal"] is True


def test_save_writes_file(composer, tmp_path):
    yml = composer.render(
        tenant_id="abc123",
        tenant_name="testsite",
        db_password="s",
        db_root_password="s",
    )
    path = composer.save(yml, tenant_name="testsite", output_dir=str(tmp_path))
    assert os.path.exists(path)
    assert "testsite" in path
    content = open(path).read()
    assert "tenant_abc123" in content

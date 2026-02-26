"""Tests for Docker operations module.

These tests mock the Docker client since we don't want to create
real containers during testing.
"""
from unittest.mock import MagicMock, patch
import pytest


@pytest.fixture
def docker_ops():
    with patch("wp_mcp.tenants.docker_ops.DockerClient") as mock_docker:
        from wp_mcp.tenants.docker_ops import TenantDockerOps
        ops = TenantDockerOps(compose_dir="/tmp/tenants")
        ops.docker = mock_docker.return_value
        yield ops


def test_project_name(docker_ops):
    assert docker_ops.project_name("abc123") == "tenant_abc123"


def test_container_name(docker_ops):
    assert docker_ops.container_name("abc123", "wordpress") == "tenant_abc123_wordpress"
    assert docker_ops.container_name("abc123", "faust") == "tenant_abc123_faust"
    assert docker_ops.container_name("abc123", "astro") == "tenant_abc123_astro"


def test_up_calls_compose(docker_ops):
    docker_ops.up("abc123", "/tmp/tenants/docker-compose-test.yml")
    docker_ops.docker.compose.up.assert_called_once()
    call_kwargs = docker_ops.docker.compose.up.call_args
    assert call_kwargs.kwargs["detach"] is True
    assert call_kwargs.kwargs["project_name"] == "tenant_abc123"


def test_down_calls_compose(docker_ops):
    docker_ops.down("abc123")
    docker_ops.docker.compose.down.assert_called_once()


def test_down_with_volumes(docker_ops):
    docker_ops.down("abc123", volumes=True)
    call_kwargs = docker_ops.docker.compose.down.call_args
    assert call_kwargs.kwargs["volumes"] is True


def test_status_returns_dict(docker_ops):
    mock_container = MagicMock()
    mock_container.name = "tenant_abc123_wordpress"
    mock_container.state.status = "running"
    docker_ops.docker.compose.ps.return_value = [mock_container]
    status = docker_ops.status("abc123")
    assert status == {"tenant_abc123_wordpress": "running"}


def test_is_healthy_true(docker_ops):
    mock_container = MagicMock()
    mock_container.name = "tenant_abc123_wordpress"
    mock_container.state.status = "running"
    docker_ops.docker.compose.ps.return_value = [mock_container]
    assert docker_ops.is_healthy("abc123") is True


def test_is_healthy_false_when_stopped(docker_ops):
    mock_container = MagicMock()
    mock_container.name = "tenant_abc123_wordpress"
    mock_container.state.status = "exited"
    docker_ops.docker.compose.ps.return_value = [mock_container]
    assert docker_ops.is_healthy("abc123") is False

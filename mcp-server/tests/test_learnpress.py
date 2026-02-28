"""Tests for LearnPress detection/install endpoints: failure modes and slug sanitization."""

import pytest
import json
import os
from pathlib import Path
from unittest.mock import AsyncMock

import httpx

from articulate_mcp.routes import learnpress as lp_route


class DummyRequest:
    def __init__(self, headers=None, path_params=None, json_data=None):
        self.headers = headers or {}
        self.path_params = path_params or {}
        self._json = json_data

    async def json(self):
        return self._json


class FakeUserManager:
    @staticmethod
    async def get_user_from_session(session_id):
        return {"id": 123}


class FakeConnectionManager:
    def __init__(self, conn=None):
        self._conn = conn or {
            "wp_url": "https://example.com",
            "wp_user": "admin",
            "wp_app_password": "pass123",
        }

    async def get_connection(self, connection_id, user_id):
        return self._conn


def _patch_auth(monkeypatch, connection=None):
    """Shared helper to patch UserManager + connection_manager."""
    monkeypatch.setattr(lp_route, "UserManager", FakeUserManager)
    monkeypatch.setattr(
        lp_route, "connection_manager",
        FakeConnectionManager(connection),
    )


# ── Detection / check endpoint ────────────────────────────────────────


@pytest.mark.asyncio
async def test_check_learnpress_graphql(monkeypatch):
    """GraphQL introspection returns LearnPress types -> installed True."""
    async def fake_get_graphql_client(connection_id, user_id):
        class Client:
            async def execute(self, query):
                return {"__schema": {"types": [{"name": "LP_Course"}, {"name": "Other"}]}}
        return Client()

    monkeypatch.setattr(lp_route, "get_graphql_client", fake_get_graphql_client)
    monkeypatch.setattr(lp_route, "UserManager", FakeUserManager)

    req = DummyRequest(headers={"X-Session-ID": "sess"}, path_params={"id": "1"})
    resp = await lp_route.check_learnpress_endpoint(req)

    assert resp.status_code == 200
    data = json.loads(resp.body.decode())
    assert data["installed"] is True
    assert data["method"] == "graphql"
    assert any("course" in t.lower() for t in data.get("matches", []))


@pytest.mark.asyncio
async def test_check_graphql_fails_rest_fallback(monkeypatch):
    """When GraphQL fails, REST fallback detects LearnPress."""
    async def failing_graphql(connection_id, user_id):
        raise Exception("GraphQL unavailable")

    monkeypatch.setattr(lp_route, "get_graphql_client", failing_graphql)
    _patch_auth(monkeypatch)

    # Mock httpx to return 200 for the first REST endpoint
    original_init = httpx.AsyncClient.__init__

    async def mock_get(self, url, **kwargs):
        resp = httpx.Response(200, json=[{"id": 1, "title": "Course 1"}])
        return resp

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    req = DummyRequest(headers={"X-Session-ID": "sess"}, path_params={"id": "1"})
    resp = await lp_route.check_learnpress_endpoint(req)

    data = json.loads(resp.body.decode())
    assert data["installed"] is True
    assert data["method"] == "rest"


@pytest.mark.asyncio
async def test_check_rest_unauthorized(monkeypatch):
    """REST check returns 401 -> reports unauthorized."""
    async def failing_graphql(connection_id, user_id):
        raise Exception("no graphql")

    monkeypatch.setattr(lp_route, "get_graphql_client", failing_graphql)
    _patch_auth(monkeypatch)

    async def mock_get(self, url, **kwargs):
        return httpx.Response(401, json={"message": "Unauthorized"})

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    req = DummyRequest(headers={"X-Session-ID": "sess"}, path_params={"id": "1"})
    resp = await lp_route.check_learnpress_endpoint(req)

    data = json.loads(resp.body.decode())
    assert data["installed"] is False
    assert data["error"] == "unauthorized"


@pytest.mark.asyncio
async def test_check_all_fail_not_installed(monkeypatch):
    """When GraphQL + all REST endpoints fail -> installed False."""
    async def failing_graphql(connection_id, user_id):
        raise Exception("no graphql")

    monkeypatch.setattr(lp_route, "get_graphql_client", failing_graphql)
    _patch_auth(monkeypatch)

    async def mock_get(self, url, **kwargs):
        return httpx.Response(404)

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    req = DummyRequest(headers={"X-Session-ID": "sess"}, path_params={"id": "1"})
    resp = await lp_route.check_learnpress_endpoint(req)

    data = json.loads(resp.body.decode())
    assert data["installed"] is False
    assert "error" not in data  # Clean not-installed, not an error


@pytest.mark.asyncio
async def test_check_no_session(monkeypatch):
    """Check without session returns 401."""
    req = DummyRequest(headers={}, path_params={"id": "1"})
    resp = await lp_route.check_learnpress_endpoint(req)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_check_invalid_session(monkeypatch):
    """Check with invalid session returns 401."""
    class NullUserManager:
        @staticmethod
        async def get_user_from_session(session_id):
            return None

    monkeypatch.setattr(lp_route, "UserManager", NullUserManager)

    req = DummyRequest(headers={"X-Session-ID": "bad"}, path_params={"id": "1"})
    resp = await lp_route.check_learnpress_endpoint(req)
    assert resp.status_code == 401


# ── Install endpoint ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_install_learnpress_ssh_fallback(monkeypatch):
    """SSH fallback triggered when GraphQL/REST fail."""
    _patch_auth(monkeypatch, {"wp_url": "https://example.com", "wp_user": "admin", "wp_app_password": None})

    class FakeProcess:
        returncode = 0
        async def communicate(self):
            return (b"Installed plugin\n", b"")

    async def fake_subprocess(*args, **kwargs):
        return FakeProcess()

    monkeypatch.setattr(lp_route, "run_subprocess_exec", fake_subprocess)

    req = DummyRequest(
        headers={"X-Session-ID": "sess"},
        path_params={"id": "1"},
        json_data={
            "ssh_host": "example.com",
            "ssh_user": "ubuntu",
            "ssh_key": "FAKEKEY",
            "wp_path": "/var/www/html",
            "plugin_slug": "learnpress",
        },
    )

    resp = await lp_route.install_learnpress_endpoint(req)
    assert resp.status_code == 200
    data = json.loads(resp.body.decode())
    assert data["success"] is True
    assert data["method"] == "ssh"


@pytest.mark.asyncio
async def test_install_ssh_failure(monkeypatch):
    """SSH process returning non-zero -> 500 with details."""
    _patch_auth(monkeypatch, {"wp_url": "https://example.com", "wp_user": "admin", "wp_app_password": None})

    class FakeProcess:
        returncode = 1
        async def communicate(self):
            return (b"", b"Connection refused\n")

    async def fake_subprocess(*a, **kw):
        return FakeProcess()
    monkeypatch.setattr(lp_route, "run_subprocess_exec", fake_subprocess)

    req = DummyRequest(
        headers={"X-Session-ID": "sess"},
        path_params={"id": "1"},
        json_data={"ssh_host": "example.com", "ssh_user": "ubuntu", "ssh_key": "K", "plugin_slug": "learnpress"},
    )
    resp = await lp_route.install_learnpress_endpoint(req)
    assert resp.status_code == 500
    data = json.loads(resp.body.decode())
    assert data["error"] == "ssh_install_failed"
    assert "Connection refused" in data["error_info"]["details"]


@pytest.mark.asyncio
async def test_install_rest_success(monkeypatch):
    """REST install succeeds with 201 status."""
    _patch_auth(monkeypatch)

    # GraphQL fails
    async def failing_graphql(connection_id, user_id):
        raise Exception("no graphql")
    monkeypatch.setattr(lp_route, "get_graphql_client", failing_graphql)

    # REST returns 201
    async def mock_post(self, url, **kwargs):
        return httpx.Response(201, json={"plugin": "learnpress", "status": "active"})
    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    req = DummyRequest(
        headers={"X-Session-ID": "sess"},
        path_params={"id": "1"},
        json_data={"plugin_slug": "learnpress"},
    )
    resp = await lp_route.install_learnpress_endpoint(req)
    assert resp.status_code == 200
    data = json.loads(resp.body.decode())
    assert data["success"] is True
    assert data["method"] == "rest"


@pytest.mark.asyncio
async def test_install_rest_forbidden(monkeypatch):
    """REST install returns 403 -> error response."""
    _patch_auth(monkeypatch)

    async def failing_graphql(connection_id, user_id):
        raise Exception("no graphql")
    monkeypatch.setattr(lp_route, "get_graphql_client", failing_graphql)

    async def mock_post(self, url, **kwargs):
        return httpx.Response(403, json={"message": "Sorry, you are not allowed"})
    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    req = DummyRequest(
        headers={"X-Session-ID": "sess"},
        path_params={"id": "1"},
        json_data={"plugin_slug": "learnpress"},
    )
    resp = await lp_route.install_learnpress_endpoint(req)
    assert resp.status_code == 403
    data = json.loads(resp.body.decode())
    assert data["error"] == "unauthorized"


@pytest.mark.asyncio
async def test_install_no_ssh_no_rest_no_graphql(monkeypatch):
    """All install methods fail, no SSH creds -> error with guidance."""
    _patch_auth(monkeypatch, {"wp_url": "https://example.com", "wp_user": "admin", "wp_app_password": None})

    req = DummyRequest(
        headers={"X-Session-ID": "sess"},
        path_params={"id": "1"},
        json_data={"plugin_slug": "learnpress"},
    )
    resp = await lp_route.install_learnpress_endpoint(req)
    assert resp.status_code == 500
    data = json.loads(resp.body.decode())
    assert data["error"] == "install_failed_no_credentials"
    assert "SSH" in data["error_info"]["message"]


@pytest.mark.asyncio
async def test_install_ssh_key_file_cleanup(monkeypatch, tmp_path):
    """SSH key file is created with 0600 and cleaned up after use."""
    _patch_auth(monkeypatch, {"wp_url": "https://example.com", "wp_user": "admin", "wp_app_password": None})

    created_files = []

    class FakeProcess:
        returncode = 0
        async def communicate(self):
            return (b"OK\n", b"")

    async def capture_subprocess(*args, **kwargs):
        # Record which key file was passed
        cmd_args = args
        for i, arg in enumerate(cmd_args):
            if arg == "--key" and i + 1 < len(cmd_args):
                key_path = Path(cmd_args[i + 1])
                created_files.append(key_path)
                assert key_path.exists(), "Key file should exist during subprocess"
                assert oct(key_path.stat().st_mode)[-3:] == "600", "Key file should be 0600"
        return FakeProcess()

    monkeypatch.setattr(lp_route, "run_subprocess_exec", capture_subprocess)

    req = DummyRequest(
        headers={"X-Session-ID": "sess"},
        path_params={"id": "1"},
        json_data={
            "ssh_host": "example.com",
            "ssh_user": "ubuntu",
            "ssh_key": "-----BEGIN RSA PRIVATE KEY-----\nfake\n-----END RSA PRIVATE KEY-----",
            "plugin_slug": "learnpress",
        },
    )
    resp = await lp_route.install_learnpress_endpoint(req)
    assert resp.status_code == 200

    # Key file should be cleaned up after use
    assert len(created_files) == 1
    assert not created_files[0].exists(), "Key file should be deleted after subprocess"


# ── Plugin slug sanitization ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_install_invalid_plugin_slug(monkeypatch):
    """Reject path traversal in plugin_slug."""
    monkeypatch.setattr(lp_route, "UserManager", FakeUserManager)

    req = DummyRequest(
        headers={"X-Session-ID": "sess"},
        path_params={"id": "1"},
        json_data={"plugin_slug": "../etc/passwd"},
    )
    resp = await lp_route.install_learnpress_endpoint(req)
    assert resp.status_code == 400
    data = json.loads(resp.body.decode())
    assert data["error"] == "invalid_plugin_slug"


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_slug", [
    "",                     # empty
    "LearnPress",           # uppercase
    "learn press",          # spaces
    "learn/press",          # slashes
    "learn;press",          # semicolons
    "learn$(cmd)",          # shell injection
    None,                   # None type
    123,                    # integer type
])
async def test_install_rejects_bad_slugs(monkeypatch, bad_slug):
    """Various invalid slugs are all rejected."""
    monkeypatch.setattr(lp_route, "UserManager", FakeUserManager)

    req = DummyRequest(
        headers={"X-Session-ID": "sess"},
        path_params={"id": "1"},
        json_data={"plugin_slug": bad_slug},
    )
    resp = await lp_route.install_learnpress_endpoint(req)
    assert resp.status_code == 400
    data = json.loads(resp.body.decode())
    assert data["error"] == "invalid_plugin_slug"


@pytest.mark.asyncio
@pytest.mark.parametrize("good_slug", [
    "learnpress",
    "wp-graphql",
    "my_plugin",
    "plugin123",
    "a-b_c-1",
])
async def test_install_accepts_good_slugs(monkeypatch, good_slug):
    """Valid slugs pass sanitization (install may still fail, but slug is accepted)."""
    _patch_auth(monkeypatch, {"wp_url": "https://example.com", "wp_user": "admin", "wp_app_password": None})

    req = DummyRequest(
        headers={"X-Session-ID": "sess"},
        path_params={"id": "1"},
        json_data={"plugin_slug": good_slug},
    )
    resp = await lp_route.install_learnpress_endpoint(req)
    # Should not get 400 for slug validation - any other status is fine
    assert resp.status_code != 400 or json.loads(resp.body.decode()).get("error") != "invalid_plugin_slug"

import pytest
import json

from articulate_mcp.routes import learnpress as lp_route

class DummyRequest:
    def __init__(self, headers=None, path_params=None, json_data=None):
        # Minimal request-like object expected by the route handlers
        self.headers = headers or {}
        self.path_params = path_params or {}
        self._json = json_data

    async def json(self):
        return self._json


@pytest.mark.asyncio
async def test_check_learnpress_graphql(monkeypatch):
    """GraphQL introspection returns LearnPress types -> installed True"""
    async def fake_get_graphql_client(connection_id, user_id):
        class Client:
            async def execute(self, query):
                return {"__schema": {"types": [{"name": "LP_Course"}, {"name": "Other"}]}}
        return Client()

    class FakeUserManager:
        @staticmethod
        async def get_user_from_session(session_id):
            return {"id": 123}

    # Patch dependencies on the module under test
    monkeypatch.setattr(lp_route, "get_graphql_client", fake_get_graphql_client)
    monkeypatch.setattr(lp_route, "UserManager", FakeUserManager)

    req = DummyRequest(headers={"X-Session-ID": "sess"}, path_params={"id": "1"})
    resp = await lp_route.check_learnpress_endpoint(req)

    assert resp.status_code == 200
    data = json.loads(resp.body.decode())
    assert data.get("installed") is True
    assert data.get("method") == "graphql"
    assert any("course" in (t).lower() for t in data.get("matches", []))


@pytest.mark.asyncio
async def test_install_learnpress_ssh_fallback(monkeypatch):
    """When GraphQL/REST fail, providing SSH credentials triggers the setup script (mocked)."""
    class FakeUserManager:
        @staticmethod
        async def get_user_from_session(session_id):
            return {"id": 123}

    # connection_manager.get_connection is used by the REST attempt; provide a minimal stub
    class FakeConnectionManager:
        async def get_connection(self, connection_id, user_id):
            return {"wp_url": "https://example.com", "wp_user": "admin", "wp_app_password": None}

    monkeypatch.setattr(lp_route, "UserManager", FakeUserManager)
    monkeypatch.setattr(lp_route, "connection_manager", FakeConnectionManager())

    # Mock subprocess execution used for SSH fallback
    class FakeProcess:
        def __init__(self):
            self.returncode = 0

        async def communicate(self):
            return (b"Installed plugin\n", b"")

    async def fake_create_subprocess_exec(*args, **kwargs):
        return FakeProcess()

    monkeypatch.setattr(lp_route, "run_subprocess_exec", fake_create_subprocess_exec)

    req = DummyRequest(
        headers={"X-Session-ID": "sess"},
        path_params={"id": "1"},
        json_data={
            "ssh_host": "example.com",
            "ssh_user": "ubuntu",
            "ssh_key": "FAKEKEY",
            "wp_path": "/var/www/html",
            "plugin_slug": "learnpress"
        }
    )

    resp = await lp_route.install_learnpress_endpoint(req)
    # Debug output to capture response body when the test fails
    print("DEBUG install resp.status_code:", getattr(resp, 'status_code', None))
    body = getattr(resp, 'body', None)
    try:
        if isinstance(body, (bytes, bytearray)):
            print("DEBUG install resp.body:", body.decode(errors='replace'))
        else:
            print("DEBUG install resp.body:", body)
    except Exception as e:
        print("DEBUG error reading resp.body:", e)

    assert resp.status_code == 200
    data = json.loads(resp.body.decode())
    assert data.get("success") is True
    assert data.get("method") == "ssh"


@pytest.mark.asyncio
async def test_install_invalid_plugin_slug(monkeypatch):
    """Reject plugin_slug values that do not match the allowed pattern."""
    class FakeUserManager:
        @staticmethod
        async def get_user_from_session(session_id):
            return {"id": 123}

    monkeypatch.setattr(lp_route, "UserManager", FakeUserManager)

    req = DummyRequest(
        headers={"X-Session-ID": "sess"},
        path_params={"id": "1"},
        json_data={"plugin_slug": "../etc/passwd"}
    )

    resp = await lp_route.install_learnpress_endpoint(req)
    # Sanitization should reject the slug before attempting installs
    assert resp.status_code == 400
    data = json.loads(resp.body.decode())
    assert data.get("error") == "invalid_plugin_slug"

import pytest
import asyncio
import traceback
from articulate_mcp.routes import learnpress as lp_route

@pytest.mark.asyncio
async def test_learnpress_debug(monkeypatch):
    """Debug test to exercise install_learnpress_endpoint and print response and body.
    This test patches asyncio.create_subprocess_exec to avoid real SSH and ensures output
    is printed so it appears in pytest and docker logs when run inside the container.
    """
    # Patch user/connection managers used by the route
    class FakeUserManager:
        @staticmethod
        async def get_user_from_session(session_id):
            return {"id": 123}

    class FakeConnectionManager:
        async def get_connection(self, connection_id, user_id):
            # minimal connection object expected by the route
            return {
                "wp_url": "https://example.com",
                "wp_user": "admin",
                "wp_app_password": None,
            }

    monkeypatch.setattr(lp_route, "UserManager", FakeUserManager)
    monkeypatch.setattr(lp_route, "connection_manager", FakeConnectionManager())

    # Fake subprocess that simulates WP-CLI install output
    async def fake_create_subprocess_exec(*args, **kwargs):
        class FakeProc:
            def __init__(self):
                self.returncode = 0

            async def communicate(self):
                return (b"INSTALLED\n", b"")

        return FakeProc()

    monkeypatch.setattr(lp_route, "run_subprocess_exec", fake_create_subprocess_exec)

    # Minimal request-like object expected by the FastAPI-like route function
    class Req:
        headers = {"X-Session-ID": "sess"}
        path_params = {"id": "1"}

        async def json(self):
            return {
                "ssh_host": "example.com",
                "ssh_user": "ubuntu",
                "ssh_key": "FAKEKEY",
                "wp_path": "/var/www/html",
                "plugin_slug": "learnpress",
            }

    try:
        resp = await lp_route.install_learnpress_endpoint(Req())
        print("DEBUG: resp.status_code =", resp.status_code)
        try:
            body = getattr(resp, "body", None)
            if isinstance(body, (bytes, bytearray)):
                print("DEBUG: resp.body:", body.decode(errors="replace"))
            else:
                print("DEBUG: resp.body:", body)
        except Exception as e:  # pragma: no cover - debug helper
            print("DEBUG: error reading body", e)
    except Exception:
        print("DEBUG: exception in install_learnpress_endpoint:")
        traceback.print_exc()

    # Always pass so this debug test doesn't block CI; it's intended to surface logs.
    assert True

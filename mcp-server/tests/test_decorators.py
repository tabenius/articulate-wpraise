"""Tests for endpoint decorators: require_auth, require_wp_capability, optional_auth."""

import pytest
import json
from unittest.mock import AsyncMock, patch

from articulate_mcp.decorators import require_auth, optional_auth, require_wp_capability


class FakeState:
    """Minimal request.state stand-in."""
    pass


class FakeRequest:
    """Minimal Starlette-like request for testing decorators."""
    def __init__(self, session_id=None, wp_roles=None, path_params=None):
        self.headers = {}
        if session_id:
            self.headers["X-Session-ID"] = session_id
        self.path_params = path_params or {}
        self.state = FakeState()
        if wp_roles is not None:
            self.state.wp_roles = wp_roles


# ── require_auth ─────────────────────────────────────────────────


class TestRequireAuth:

    @pytest.mark.asyncio
    async def test_missing_session_returns_401(self):
        @require_auth
        async def endpoint(request):
            return {"ok": True}

        req = FakeRequest()
        resp = await endpoint(req)
        assert resp.status_code == 401
        body = json.loads(resp.body.decode())
        assert body["error"] == "Session required"

    @pytest.mark.asyncio
    async def test_invalid_session_returns_401(self):
        with patch("articulate_mcp.user_manager.UserManager") as MockUM:
            MockUM.get_user_from_session = AsyncMock(return_value=None)

            @require_auth
            async def endpoint(request):
                return {"ok": True}

            req = FakeRequest(session_id="bad-session")
            resp = await endpoint(req)
            assert resp.status_code == 401
            body = json.loads(resp.body.decode())
            assert body["error"] == "Invalid session"

    @pytest.mark.asyncio
    async def test_valid_session_injects_user(self):
        fake_user = {"id": 42, "email": "test@example.com"}
        with patch("articulate_mcp.user_manager.UserManager") as MockUM:
            MockUM.get_user_from_session = AsyncMock(return_value=fake_user)

            @require_auth
            async def endpoint(request):
                return request.state.user

            req = FakeRequest(session_id="good-session")
            result = await endpoint(req)
            assert result == fake_user


# ── optional_auth ────────────────────────────────────────────────


class TestOptionalAuth:

    @pytest.mark.asyncio
    async def test_no_session_sets_user_none(self):
        @optional_auth
        async def endpoint(request):
            return request.state.user

        req = FakeRequest()
        result = await endpoint(req)
        assert result is None

    @pytest.mark.asyncio
    async def test_valid_session_sets_user(self):
        fake_user = {"id": 1, "email": "a@b.com"}
        with patch("articulate_mcp.user_manager.UserManager") as MockUM:
            MockUM.get_user_from_session = AsyncMock(return_value=fake_user)

            @optional_auth
            async def endpoint(request):
                return request.state.user

            req = FakeRequest(session_id="sess-123")
            result = await endpoint(req)
            assert result == fake_user

    @pytest.mark.asyncio
    async def test_invalid_session_sets_user_none(self):
        with patch("articulate_mcp.user_manager.UserManager") as MockUM:
            MockUM.get_user_from_session = AsyncMock(return_value=None)

            @optional_auth
            async def endpoint(request):
                return request.state.user

            req = FakeRequest(session_id="expired")
            result = await endpoint(req)
            assert result is None


# ── require_wp_capability ────────────────────────────────────────


class TestRequireWpCapability:

    @pytest.mark.asyncio
    async def test_no_wp_roles_returns_403(self):
        @require_wp_capability("edit_posts")
        async def endpoint(request):
            return {"ok": True}

        req = FakeRequest()  # no wp_roles on state
        resp = await endpoint(req)
        assert resp.status_code == 403
        body = json.loads(resp.body.decode())
        assert "WordPress role information not available" in body["error"]

    @pytest.mark.asyncio
    async def test_admin_has_capability(self):
        @require_wp_capability("edit_posts")
        async def endpoint(request):
            from starlette.responses import JSONResponse
            return JSONResponse({"ok": True})

        req = FakeRequest(wp_roles=["administrator"])
        resp = await endpoint(req)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_subscriber_lacks_capability(self):
        @require_wp_capability("edit_posts")
        async def endpoint(request):
            from starlette.responses import JSONResponse
            return JSONResponse({"ok": True})

        req = FakeRequest(wp_roles=["subscriber"])
        resp = await endpoint(req)
        assert resp.status_code == 403
        body = json.loads(resp.body.decode())
        assert "Insufficient WordPress capabilities" in body["error"]
        assert "subscriber" in body["detail"]

    @pytest.mark.asyncio
    async def test_string_capability_converted_to_list(self):
        """Passing a single string instead of a list should work."""
        @require_wp_capability("manage_options")
        async def endpoint(request):
            from starlette.responses import JSONResponse
            return JSONResponse({"ok": True})

        req = FakeRequest(wp_roles=["administrator"])
        resp = await endpoint(req)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_multiple_capabilities_all_required(self):
        @require_wp_capability(["edit_posts", "publish_posts"])
        async def endpoint(request):
            from starlette.responses import JSONResponse
            return JSONResponse({"ok": True})

        # Editor has both
        req = FakeRequest(wp_roles=["editor"])
        resp = await endpoint(req)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_contributor_cant_publish(self):
        @require_wp_capability(["edit_posts", "publish_posts"])
        async def endpoint(request):
            from starlette.responses import JSONResponse
            return JSONResponse({"ok": True})

        req = FakeRequest(wp_roles=["contributor"])
        resp = await endpoint(req)
        assert resp.status_code == 403
        body = json.loads(resp.body.decode())
        assert "publish_posts" in body["missing_capabilities"]

"""Tests for tenants/wp_user_sync.py: create and update WP users for tenants."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from articulate_mcp.tenants.wp_user_sync import (
    ROLE_MAP,
    create_wp_user_for_tenant,
    update_wp_user_role_for_tenant,
)


class TestRoleMap:

    def test_owner_maps_to_administrator(self):
        assert ROLE_MAP["owner"] == "administrator"

    def test_admin_maps_to_administrator(self):
        assert ROLE_MAP["admin"] == "administrator"

    def test_editor_maps_to_editor(self):
        assert ROLE_MAP["editor"] == "editor"

    def test_viewer_maps_to_subscriber(self):
        assert ROLE_MAP["viewer"] == "subscriber"


def _mock_response(status_code=200, json_data=None, content_type="application/json"):
    """Create a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.headers = {"content-type": content_type}
    return resp


class TestCreateWpUserForTenant:

    @pytest.mark.asyncio
    async def test_creates_new_user(self):
        """When user doesn't exist by email, create a new WP user."""
        search_resp = _mock_response(200, [])  # no existing users
        create_resp = _mock_response(201, {"id": 55, "username": "art_alice"})

        with patch("articulate_mcp.tenants.wp_user_sync.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.get = AsyncMock(return_value=search_resp)
            client_instance.post = AsyncMock(return_value=create_resp)
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            result = await create_wp_user_for_tenant(
                wp_url="http://wordpress:80",
                wp_admin_user="admin",
                wp_admin_password="pass",
                articulate_user_email="alice@example.com",
                articulate_user_name="Alice Smith",
                articulate_role="editor",
            )

            assert result is not None
            assert result["wp_user_id"] == 55
            assert result["wp_role"] == "editor"
            # Verify POST was called with correct payload
            client_instance.post.assert_called_once()
            call_args = client_instance.post.call_args
            assert call_args[0][0] == "/users"
            payload = call_args[1]["json"]
            assert payload["email"] == "alice@example.com"
            assert payload["roles"] == ["editor"]
            assert payload["first_name"] == "Alice"
            assert payload["last_name"] == "Smith"

    @pytest.mark.asyncio
    async def test_existing_user_returned(self):
        """When user exists by email, return existing user info."""
        existing_user = {
            "id": 10,
            "email": "bob@example.com",
            "username": "art_bob",
            "roles": ["administrator"],
        }
        search_resp = _mock_response(200, [existing_user])

        with patch("articulate_mcp.tenants.wp_user_sync.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.get = AsyncMock(return_value=search_resp)
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            result = await create_wp_user_for_tenant(
                wp_url="http://wordpress:80",
                wp_admin_user="admin",
                wp_admin_password="pass",
                articulate_user_email="bob@example.com",
                articulate_user_name="Bob",
                articulate_role="admin",  # maps to administrator
            )

            assert result is not None
            assert result["wp_user_id"] == 10
            assert result["wp_username"] == "art_bob"
            # Should not have called POST since user already has administrator role
            client_instance.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_existing_user_role_updated(self):
        """When user exists but has different role, update it."""
        existing_user = {
            "id": 10,
            "email": "carol@example.com",
            "username": "art_carol",
            "roles": ["subscriber"],
        }
        search_resp = _mock_response(200, [existing_user])
        update_resp = _mock_response(200, {"id": 10})

        with patch("articulate_mcp.tenants.wp_user_sync.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.get = AsyncMock(return_value=search_resp)
            client_instance.post = AsyncMock(return_value=update_resp)
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            result = await create_wp_user_for_tenant(
                wp_url="http://wordpress:80",
                wp_admin_user="admin",
                wp_admin_password="pass",
                articulate_user_email="carol@example.com",
                articulate_user_name="Carol",
                articulate_role="admin",  # maps to administrator, user has subscriber
            )

            assert result is not None
            assert result["wp_role"] == "administrator"
            # Should have called POST to update role
            client_instance.post.assert_called_once()
            call_args = client_instance.post.call_args
            assert "/users/10" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_create_fails_returns_none(self):
        """When WP returns non-success status, return None."""
        search_resp = _mock_response(200, [])
        create_resp = _mock_response(500, {"message": "Internal error"})

        with patch("articulate_mcp.tenants.wp_user_sync.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.get = AsyncMock(return_value=search_resp)
            client_instance.post = AsyncMock(return_value=create_resp)
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            result = await create_wp_user_for_tenant(
                wp_url="http://wordpress:80",
                wp_admin_user="admin",
                wp_admin_password="pass",
                articulate_user_email="fail@example.com",
                articulate_user_name="Fail",
                articulate_role="viewer",
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_network_error_returns_none(self):
        """When httpx raises an exception, return None."""
        with patch("articulate_mcp.tenants.wp_user_sync.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            result = await create_wp_user_for_tenant(
                wp_url="http://wordpress:80",
                wp_admin_user="admin",
                wp_admin_password="pass",
                articulate_user_email="net@example.com",
                articulate_user_name="Net",
                articulate_role="viewer",
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_unknown_role_defaults_to_subscriber(self):
        """Unknown Articulate roles should map to subscriber."""
        search_resp = _mock_response(200, [])
        create_resp = _mock_response(201, {"id": 99, "username": "art_unknown"})

        with patch("articulate_mcp.tenants.wp_user_sync.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.get = AsyncMock(return_value=search_resp)
            client_instance.post = AsyncMock(return_value=create_resp)
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            result = await create_wp_user_for_tenant(
                wp_url="http://wordpress:80",
                wp_admin_user="admin",
                wp_admin_password="pass",
                articulate_user_email="unknown@example.com",
                articulate_user_name="Unknown",
                articulate_role="nonexistent_role",
            )

            assert result is not None
            assert result["wp_role"] == "subscriber"
            payload = client_instance.post.call_args[1]["json"]
            assert payload["roles"] == ["subscriber"]


class TestUpdateWpUserRoleForTenant:

    @pytest.mark.asyncio
    async def test_successful_role_update(self):
        update_resp = _mock_response(200, {"id": 10})

        with patch("articulate_mcp.tenants.wp_user_sync.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post = AsyncMock(return_value=update_resp)
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            result = await update_wp_user_role_for_tenant(
                wp_url="http://wordpress:80",
                wp_admin_user="admin",
                wp_admin_password="pass",
                wp_user_id=10,
                new_articulate_role="editor",
            )

            assert result is True
            call_args = client_instance.post.call_args
            assert "/users/10" in call_args[0][0]
            assert call_args[1]["json"]["roles"] == ["editor"]

    @pytest.mark.asyncio
    async def test_failed_role_update(self):
        update_resp = _mock_response(500, {})

        with patch("articulate_mcp.tenants.wp_user_sync.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post = AsyncMock(return_value=update_resp)
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            result = await update_wp_user_role_for_tenant(
                wp_url="http://wordpress:80",
                wp_admin_user="admin",
                wp_admin_password="pass",
                wp_user_id=10,
                new_articulate_role="admin",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_network_error_returns_false(self):
        with patch("articulate_mcp.tenants.wp_user_sync.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post = AsyncMock(side_effect=httpx.ConnectError("Refused"))
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            result = await update_wp_user_role_for_tenant(
                wp_url="http://wordpress:80",
                wp_admin_user="admin",
                wp_admin_password="pass",
                wp_user_id=10,
                new_articulate_role="viewer",
            )

            assert result is False

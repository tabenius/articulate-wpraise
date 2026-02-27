"""Tests for context_helper: get_connection_info and check_wp_capability."""

import pytest
from articulate_mcp.context_helper import get_connection_info, check_wp_capability


class TestGetConnectionInfo:
    """Tests for get_connection_info()."""

    def test_dict_context(self):
        ctx = {"connection_id": 5, "user_id": 10}
        conn_id, uid = get_connection_info(ctx)
        assert conn_id == 5
        assert uid == 10

    def test_object_context(self):
        class Ctx:
            connection_id = 7
            user_id = 3

        conn_id, uid = get_connection_info(Ctx())
        assert conn_id == 7
        assert uid == 3

    def test_none_context_raises(self):
        with pytest.raises(ValueError, match="Context is required"):
            get_connection_info(None)

    def test_missing_connection_id_raises(self):
        with pytest.raises(ValueError, match="Missing connection info"):
            get_connection_info({"user_id": 1})

    def test_missing_user_id_raises(self):
        with pytest.raises(ValueError, match="Missing connection info"):
            get_connection_info({"connection_id": 1})

    def test_string_values_cast_to_int(self):
        ctx = {"connection_id": "42", "user_id": "99"}
        conn_id, uid = get_connection_info(ctx)
        assert conn_id == 42
        assert uid == 99
        assert isinstance(conn_id, int)
        assert isinstance(uid, int)

    def test_empty_dict_raises(self):
        with pytest.raises(ValueError, match="Missing connection info"):
            get_connection_info({})


class TestCheckWpCapability:
    """Tests for check_wp_capability()."""

    def test_admin_allowed_for_publish(self):
        ctx = {"wp_roles": ["administrator"]}
        allowed, msg = check_wp_capability(ctx, "publish_post")
        assert allowed is True
        assert msg == ""

    def test_subscriber_blocked_for_publish(self):
        ctx = {"wp_roles": ["subscriber"]}
        allowed, msg = check_wp_capability(ctx, "publish_post")
        assert allowed is False
        assert "subscriber" in msg
        assert "Warning" in msg

    def test_no_roles_returns_allowed(self):
        """No role info means let WordPress handle it."""
        ctx = {"wp_roles": []}
        allowed, msg = check_wp_capability(ctx, "publish_post")
        assert allowed is True
        assert msg == ""

    def test_none_roles_returns_allowed(self):
        ctx = {"wp_roles": None}
        allowed, msg = check_wp_capability(ctx, "publish_post")
        assert allowed is True

    def test_object_context_with_roles(self):
        class Ctx:
            wp_roles = ["editor"]

        allowed, msg = check_wp_capability(Ctx(), "publish_post")
        assert allowed is True

    def test_unknown_operation_returns_allowed(self):
        """Unknown operations have no required caps, so they pass."""
        ctx = {"wp_roles": ["subscriber"]}
        allowed, msg = check_wp_capability(ctx, "totally_made_up_op")
        assert allowed is True

    def test_context_without_wp_roles_attr(self):
        """Object without wp_roles attribute - let WordPress handle it."""
        class Ctx:
            pass

        allowed, msg = check_wp_capability(Ctx(), "publish_post")
        assert allowed is True

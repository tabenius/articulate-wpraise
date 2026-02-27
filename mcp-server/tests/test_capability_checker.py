"""Tests for CapabilityChecker service."""

import pytest
from articulate_mcp.capability_checker import CapabilityChecker, ROLE_CAPABILITIES


class TestRoleCapabilities:
    """Test the static role-to-capability mapping."""

    def test_administrator_has_all_capabilities(self):
        caps = ROLE_CAPABILITIES["administrator"]
        assert "manage_options" in caps
        assert "edit_others_posts" in caps
        assert "upload_files" in caps
        assert "create_users" in caps
        assert "edit_theme_options" in caps

    def test_editor_cannot_manage_options(self):
        caps = ROLE_CAPABILITIES["editor"]
        assert "edit_others_posts" in caps
        assert "manage_options" not in caps
        assert "create_users" not in caps

    def test_author_cannot_edit_others(self):
        caps = ROLE_CAPABILITIES["author"]
        assert "edit_posts" in caps
        assert "publish_posts" in caps
        assert "upload_files" in caps
        assert "edit_others_posts" not in caps

    def test_contributor_cannot_publish(self):
        caps = ROLE_CAPABILITIES["contributor"]
        assert "edit_posts" in caps
        assert "publish_posts" not in caps
        assert "upload_files" not in caps

    def test_subscriber_read_only(self):
        caps = ROLE_CAPABILITIES["subscriber"]
        assert "read" in caps
        assert len(caps) == 1


class TestCapabilityChecker:
    """Test CapabilityChecker methods."""

    def test_get_capabilities_for_roles(self):
        checker = CapabilityChecker()
        caps = checker.get_capabilities_for_roles(["editor"])
        assert "edit_others_posts" in caps
        assert "manage_options" not in caps

    def test_get_capabilities_for_multiple_roles(self):
        checker = CapabilityChecker()
        caps = checker.get_capabilities_for_roles(["author", "editor"])
        assert "edit_others_posts" in caps
        assert "upload_files" in caps

    def test_get_capabilities_for_unknown_role(self):
        checker = CapabilityChecker()
        caps = checker.get_capabilities_for_roles(["custom_role"])
        assert caps == {"read"}

    def test_check_capability_pass(self):
        checker = CapabilityChecker()
        has, missing = checker.check(["administrator"], "manage_options")
        assert has is True
        assert missing == []

    def test_check_capability_fail(self):
        checker = CapabilityChecker()
        has, missing = checker.check(["editor"], "manage_options")
        assert has is False
        assert "manage_options" in missing

    def test_check_multiple_required(self):
        checker = CapabilityChecker()
        has, missing = checker.check(["author"], ["edit_others_posts", "publish_posts"])
        assert has is False
        assert "edit_others_posts" in missing
        assert "publish_posts" not in missing

    def test_operation_mapping(self):
        checker = CapabilityChecker()
        required = checker.get_required_capabilities("create_post")
        assert "edit_posts" in required

    def test_unknown_operation_returns_empty(self):
        checker = CapabilityChecker()
        required = checker.get_required_capabilities("unknown_op")
        assert required == []

    def test_check_operation_pass(self):
        checker = CapabilityChecker()
        allowed, missing = checker.check_operation(["editor"], "create_post")
        assert allowed is True
        assert missing == []

    def test_check_operation_fail(self):
        checker = CapabilityChecker()
        allowed, missing = checker.check_operation(["contributor"], "upload_media")
        assert allowed is False
        assert "upload_files" in missing

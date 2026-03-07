"""Tests for MCP tool access classification and mutation guards."""

from __future__ import annotations

import pytest

from articulate_mcp.tool_access import (
    AccessPolicyViolation,
    AccessTag,
    ReadOnlyViolation,
    assert_graphql_allowed,
    assert_tool_allowed,
    assert_sql_allowed,
    infer_tool_access,
    parse_allowed_access,
    register_tool_access,
    register_tool_dependencies,
    reset_active_tool_policy,
    set_active_tool_policy,
)


def test_infer_name_based_tags() -> None:
    assert infer_tool_access("get_posts").tag is AccessTag.READ
    assert infer_tool_access("create_post").tag is AccessTag.CREATE
    assert infer_tool_access("update_post").tag is AccessTag.UPDATE
    assert infer_tool_access("delete_post").tag is AccessTag.DELETE


def test_infer_graphql_generated_mutation_name() -> None:
    policy = infer_tool_access("createPage", description="The createPage mutation")
    assert policy.tag is AccessTag.CREATE
    assert policy.read_only is False


def test_explicit_override_wins() -> None:
    register_tool_access("search", AccessTag.READ)
    policy = infer_tool_access("search", description="might mutate by description")
    assert policy.tag is AccessTag.READ
    assert policy.read_only is True
    assert policy.source == "explicit"


def test_dependency_closure_infers_read_only() -> None:
    register_tool_access("inner_read", AccessTag.READ)
    register_tool_dependencies("outer_read", ["inner_read"])
    policy = infer_tool_access("outer_read")
    assert policy.tag is AccessTag.READ
    assert policy.read_only is True
    assert policy.source == "dependency-closure"


def test_sql_guard_blocks_non_select_for_read_only_tool() -> None:
    token = set_active_tool_policy(infer_tool_access("get_posts"))
    try:
        assert_sql_allowed("SELECT * FROM posts")
        with pytest.raises(ReadOnlyViolation):
            assert_sql_allowed("UPDATE posts SET title = 'x'")
    finally:
        reset_active_tool_policy(token)


def test_graphql_guard_blocks_mutation_for_read_only_tool() -> None:
    token = set_active_tool_policy(infer_tool_access("get_posts"))
    try:
        assert_graphql_allowed("query Posts { posts { nodes { databaseId } } }")
        with pytest.raises(ReadOnlyViolation):
            assert_graphql_allowed("mutation UpdatePost { updatePost(input: {}) { post { databaseId } } }")
    finally:
        reset_active_tool_policy(token)


def test_parse_allowed_access_variants() -> None:
    assert parse_allowed_access("Read,Update") == {AccessTag.READ, AccessTag.UPDATE}
    assert parse_allowed_access(["Create", "Delete"]) == {AccessTag.CREATE, AccessTag.DELETE}
    assert parse_allowed_access(None) is None


def test_parse_allowed_access_rejects_invalid() -> None:
    with pytest.raises(ValueError):
        parse_allowed_access(["Read", "Unknown"])


def test_assert_tool_allowed_blocks_disallowed_tag() -> None:
    access = infer_tool_access("create_post")
    with pytest.raises(AccessPolicyViolation):
        assert_tool_allowed(access, {AccessTag.READ})


def test_prefixed_tool_names_classified_correctly() -> None:
    """Tools with namespace prefixes (e.g. lp_) must not default to Read."""
    assert infer_tool_access("lp_create_course").tag is AccessTag.CREATE
    assert infer_tool_access("lp_delete_course").tag is AccessTag.DELETE
    assert infer_tool_access("lp_update_course").tag is AccessTag.UPDATE
    assert infer_tool_access("lp_get_course").tag is AccessTag.READ
    assert infer_tool_access("lp_finish_course").tag is AccessTag.UPDATE
    assert infer_tool_access("lp_enroll_student").tag is AccessTag.CREATE


def test_all_mutating_tools_are_not_read_only() -> None:
    """Every mutating tool must be classified as non-read-only."""
    mutating = [
        "create_post", "update_post", "delete_post",
        "create_page", "update_page",
        "insert_block", "move_block", "remove_block", "update_blocks",
        "grant_access", "revoke_access",
        "compress_wordpress_image",
        "lp_create_course", "lp_delete_course", "lp_update_course",
        "lp_enroll_student", "lp_finish_course", "lp_submit_quiz",
        "restore_revision", "upload_media",
    ]
    for name in mutating:
        policy = infer_tool_access(name)
        assert not policy.read_only, f"{name} should not be read_only (got {policy})"


def test_no_tools_fall_through_to_default() -> None:
    """All known tool names must resolve via explicit or name-heuristic, never default."""
    all_tools = [
        "get_posts", "get_post", "create_post", "update_post", "delete_post",
        "posts", "post", "createPost", "updatePost", "deletePost",
        "get_pages", "get_page", "create_page", "update_page",
        "pages", "page", "createPage", "updatePage", "deletePage",
        "get_blocks", "update_blocks", "insert_block", "remove_block", "move_block",
        "get_media", "get_media_item", "upload_media", "upload_image_to_wordpress",
        "get_categories", "get_tags", "create_category", "create_tag",
        "get_post_revisions", "compare_revisions", "restore_revision",
        "search_content", "contentNode",
        "get_post_seo", "update_post_seo", "validate_seo",
        "get_templates", "get_template", "get_template_parts",
        "create_template", "update_template",
        "get_global_styles", "export_theme_json", "get_export_manifest",
        "list_fonts", "upload_font", "delete_font",
        "get_image_info", "compress_wordpress_image",
        "get_wp_capabilities", "get_wp_users", "create_wp_user", "update_wp_user_role",
        "list_products", "get_product", "create_product", "update_product",
        "list_access_grants", "grant_access", "revoke_access",
        "create_tenant", "list_my_tenants", "get_tenant_details",
        "update_tenant_status", "add_user_to_tenant", "remove_user_from_tenant",
        "lp_list_courses", "lp_get_course", "lp_create_course", "lp_update_course",
        "lp_delete_course", "lp_list_lessons", "lp_get_lesson", "lp_create_lesson",
        "lp_list_quizzes", "lp_get_quiz", "lp_create_quiz",
        "lp_enroll_student", "lp_list_enrolled_courses", "lp_get_student_progress",
        "lp_finish_course", "lp_finish_lesson", "lp_retake_course",
        "lp_start_quiz", "lp_submit_quiz",
        "get_media_library_images",
    ]
    for name in all_tools:
        policy = infer_tool_access(name)
        assert policy.source != "default", f"{name} fell through to default: {policy}"

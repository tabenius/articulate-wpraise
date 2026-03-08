"""Tool access classification and read-only mutation guards for MCP calls."""

from __future__ import annotations

import contextvars
import re
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Any, Callable, Iterable


class AccessTag(str, Enum):
    """High-level access classification for tools."""

    READ = "Read"
    CREATE = "Create"
    UPDATE = "Update"
    DELETE = "Delete"


@dataclass(frozen=True)
class ToolAccessPolicy:
    """Resolved access policy for a tool call."""

    tag: AccessTag
    read_only: bool
    source: str
    reason: str


class ReadOnlyViolation(PermissionError):
    """Raised when a read-only tool attempts a mutating operation."""


class AccessPolicyViolation(PermissionError):
    """Raised when a tool call violates a caller-selected access policy."""


_ACTIVE_TOOL_POLICY: contextvars.ContextVar[ToolAccessPolicy | None] = contextvars.ContextVar(
    "active_tool_policy",
    default=None,
)

_EXPLICIT_TOOL_TAGS: dict[str, AccessTag] = {}
_TOOL_DEPENDENCIES: dict[str, set[str]] = {}


_READ_VERBS = {
    "get",
    "list",
    "fetch",
    "read",
    "search",
    "find",
    "preview",
    "compare",
    "check",
    "query",
    "inspect",
}
_CREATE_VERBS = {"create", "add", "insert", "upload", "register", "enroll"}
_UPDATE_VERBS = {"update", "edit", "set", "publish", "activate", "install", "restore", "sync"}
_DELETE_VERBS = {"delete", "remove", "revoke", "cancel", "drop", "purge"}


def _tokenize_name(name: str) -> list[str]:
    snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name).lower()
    return [t for t in snake.split("_") if t]


def register_tool_access(name: str, tag: AccessTag) -> None:
    """Register explicit access mode for a tool name."""
    _EXPLICIT_TOOL_TAGS[name] = tag


def register_tool_dependencies(name: str, dependencies: list[str]) -> None:
    """Register a tool dependency graph edge set."""
    _TOOL_DEPENDENCIES[name] = set(dependencies)


def tool_access(tag: AccessTag) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for explicit tool access declaration."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        setattr(func, "__tool_access_tag__", tag)
        register_tool_access(func.__name__, tag)
        return func

    return decorator


def uses_tools(*tool_names: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for declaring intra-tool dependencies used for transitive inference."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        register_tool_dependencies(func.__name__, list(tool_names))

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def infer_tool_access(
    tool_name: str,
    description: str = "",
    annotations: dict[str, Any] | None = None,
) -> ToolAccessPolicy:
    """Infer tool access mode from explicit metadata, dependencies, and naming."""
    explicit = _EXPLICIT_TOOL_TAGS.get(tool_name)
    if explicit is not None:
        return ToolAccessPolicy(
            tag=explicit,
            read_only=explicit is AccessTag.READ,
            source="explicit",
            reason=f"explicit override for {tool_name}",
        )

    if annotations and annotations.get("readOnlyHint") is True:
        return ToolAccessPolicy(
            tag=AccessTag.READ,
            read_only=True,
            source="annotation",
            reason="readOnlyHint=true",
        )

    deps = _TOOL_DEPENDENCIES.get(tool_name)
    if deps:
        dep_policies = [infer_tool_access(dep) for dep in deps]
        if all(d.read_only for d in dep_policies):
            return ToolAccessPolicy(
                tag=AccessTag.READ,
                read_only=True,
                source="dependency-closure",
                reason=f"all dependencies read-only: {sorted(deps)}",
            )

    tokens = _tokenize_name(tool_name)
    lead = tokens[0] if tokens else tool_name.lower()
    if lead in _CREATE_VERBS:
        return ToolAccessPolicy(AccessTag.CREATE, False, "name-heuristic", f"verb={lead}")
    if lead in _UPDATE_VERBS:
        return ToolAccessPolicy(AccessTag.UPDATE, False, "name-heuristic", f"verb={lead}")
    if lead in _DELETE_VERBS:
        return ToolAccessPolicy(AccessTag.DELETE, False, "name-heuristic", f"verb={lead}")
    if lead in _READ_VERBS:
        return ToolAccessPolicy(AccessTag.READ, True, "name-heuristic", f"verb={lead}")

    # Scan all tokens for verb matches (handles prefixed names like lp_create_course)
    for token in tokens[1:]:
        if token in _CREATE_VERBS:
            return ToolAccessPolicy(AccessTag.CREATE, False, "name-heuristic", f"verb={token}")
        if token in _UPDATE_VERBS:
            return ToolAccessPolicy(AccessTag.UPDATE, False, "name-heuristic", f"verb={token}")
        if token in _DELETE_VERBS:
            return ToolAccessPolicy(AccessTag.DELETE, False, "name-heuristic", f"verb={token}")
        if token in _READ_VERBS:
            return ToolAccessPolicy(AccessTag.READ, True, "name-heuristic", f"verb={token}")

    desc_lower = description.lower()
    if "mutation" in desc_lower:
        return ToolAccessPolicy(
            tag=AccessTag.UPDATE,
            read_only=False,
            source="description-heuristic",
            reason="description references mutation",
        )

    return ToolAccessPolicy(
        tag=AccessTag.READ,
        read_only=True,
        source="default",
        reason="default conservative classification",
    )


def get_active_tool_policy() -> ToolAccessPolicy | None:
    """Get policy for the currently executing tool call."""
    return _ACTIVE_TOOL_POLICY.get()


def set_active_tool_policy(policy: ToolAccessPolicy):
    """Set active tool policy for the current async context."""
    return _ACTIVE_TOOL_POLICY.set(policy)


def reset_active_tool_policy(token: contextvars.Token[ToolAccessPolicy | None]) -> None:
    """Restore previous active tool policy."""
    _ACTIVE_TOOL_POLICY.reset(token)


def detect_graphql_operation(document: str) -> str:
    """Detect GraphQL operation type (query/mutation/subscription)."""
    stripped = re.sub(r"#[^\n]*", "", document).lstrip()
    lowered = stripped.lower()
    if lowered.startswith("mutation"):
        return "mutation"
    if lowered.startswith("subscription"):
        return "subscription"
    return "query"


def is_sql_read_only(sql: str) -> bool:
    """Return True only if the SQL operation starts with SELECT."""
    # Remove leading block comments and line comments.
    cleaned = re.sub(r"^\s*/\*.*?\*/", "", sql, flags=re.S).strip()
    cleaned = re.sub(r"^\s*--[^\n]*(\n|$)", "", cleaned, flags=re.M).strip()
    if not cleaned:
        return True
    first = cleaned.split(None, 1)[0].upper()
    return first == "SELECT"


def assert_graphql_allowed(document: str) -> None:
    """Guard GraphQL mutation execution in read-only tool contexts."""
    policy = get_active_tool_policy()
    if not policy or not policy.read_only:
        return
    op = detect_graphql_operation(document)
    if op == "mutation":
        raise ReadOnlyViolation(
            f"Tool is read-only ({policy.tag.value}) and cannot execute GraphQL mutation"
        )


def assert_sql_allowed(sql: str) -> None:
    """Guard SQL mutation execution in read-only tool contexts."""
    policy = get_active_tool_policy()
    if not policy or not policy.read_only:
        return
    if not is_sql_read_only(sql):
        raise ReadOnlyViolation(
            f"Tool is read-only ({policy.tag.value}) and cannot execute non-SELECT SQL"
        )


def parse_allowed_access(raw: Any) -> set[AccessTag] | None:
    """Parse client-selected access tags.

    Accepts:
    - None: no restriction
    - comma-separated string: "Read,Update"
    - iterable of strings/enums: ["Read", "Create"]
    """
    if raw is None:
        return None

    values: Iterable[Any]
    if isinstance(raw, str):
        values = [v.strip() for v in raw.split(",") if v.strip()]
    elif isinstance(raw, Iterable):
        values = raw
    else:
        raise ValueError("allowedAccess must be a string or array")

    resolved: set[AccessTag] = set()
    for value in values:
        if isinstance(value, AccessTag):
            resolved.add(value)
            continue
        if not isinstance(value, str):
            raise ValueError(f"Invalid access tag type: {type(value).__name__}")
        normalized = value.strip().lower()
        mapping = {
            "read": AccessTag.READ,
            "create": AccessTag.CREATE,
            "update": AccessTag.UPDATE,
            "delete": AccessTag.DELETE,
        }
        if normalized not in mapping:
            raise ValueError(f"Invalid access tag: {value}")
        resolved.add(mapping[normalized])

    if not resolved:
        raise ValueError("allowedAccess cannot be empty")

    return resolved


def assert_tool_allowed(access: ToolAccessPolicy, allowed: set[AccessTag] | None) -> None:
    """Validate that a tool's inferred access tag is permitted by client policy."""
    if allowed is None:
        return
    if access.tag not in allowed:
        allowed_names = ", ".join(sorted(t.value for t in allowed))
        raise AccessPolicyViolation(
            f"Tool requires '{access.tag.value}' access but caller allows only [{allowed_names}]"
        )


# ---------------------------------------------------------------------------
# Explicit access registrations for all MCP tools.
# These override heuristic inference and ensure every tool is classified.
# ---------------------------------------------------------------------------

def _register_all_tool_access() -> None:
    R, C, U, D = AccessTag.READ, AccessTag.CREATE, AccessTag.UPDATE, AccessTag.DELETE

    _all: dict[str, AccessTag] = {
        # -- Posts --
        "get_posts": R,
        "get_post": R,
        "create_post": C,
        "update_post": U,
        "delete_post": D,
        "posts": R,
        "post": R,
        "createPost": C,
        "updatePost": U,
        "deletePost": D,

        # -- Pages --
        "get_pages": R,
        "get_page": R,
        "create_page": C,
        "update_page": U,
        "pages": R,
        "page": R,
        "createPage": C,
        "updatePage": U,
        "deletePage": D,

        # -- Blocks --
        "get_blocks": R,
        "update_blocks": U,
        "insert_block": C,
        "remove_block": D,
        "move_block": U,

        # -- Media --
        "get_media": R,
        "get_media_item": R,
        "get_media_library_images": R,
        "upload_media": C,
        "upload_image_to_wordpress": C,

        # -- Taxonomies --
        "get_categories": R,
        "get_tags": R,
        "create_category": C,
        "create_tag": C,

        # -- Revisions --
        "get_post_revisions": R,
        "compare_revisions": R,
        "restore_revision": U,

        # -- Search --
        "search_content": R,
        "contentNode": R,

        # -- SEO --
        "get_post_seo": R,
        "update_post_seo": U,
        "validate_seo": R,

        # -- Templates --
        "get_templates": R,
        "get_template": R,
        "get_template_parts": R,
        "create_template": C,
        "update_template": U,

        # -- Settings & Styles --
        "get_global_styles": R,
        "export_theme_json": R,
        "get_export_manifest": R,

        # -- Fonts --
        "list_fonts": R,
        "upload_font": C,
        "delete_font": D,

        # -- Images --
        "get_image_info": R,
        "compress_wordpress_image": U,

        # -- Preview --
        "preview": R,

        # -- Menus --

        # -- Menus --
        "list_menus": R,
        "get_menu_items": R,
        "add_page_to_menu": C,
        "remove_page_from_menu": D,

        # -- Capabilities --
        "get_wp_capabilities": R,

        # -- Users --
        "get_wp_users": R,
        "create_wp_user": C,
        "update_wp_user_role": U,

        # -- Products & Access Grants --
        "list_products": R,
        "get_product": R,
        "create_product": C,
        "update_product": U,
        "list_access_grants": R,
        "grant_access": C,
        "revoke_access": D,

        # -- Tenants --
        "create_tenant": C,
        "list_my_tenants": R,
        "get_tenant_details": R,
        "update_tenant_status": U,
        "add_user_to_tenant": C,
        "remove_user_from_tenant": D,

        # -- LearnPress --
        "lp_list_courses": R,
        "lp_get_course": R,
        "lp_create_course": C,
        "lp_update_course": U,
        "lp_delete_course": D,
        "lp_list_lessons": R,
        "lp_get_lesson": R,
        "lp_create_lesson": C,
        "lp_list_quizzes": R,
        "lp_get_quiz": R,
        "lp_create_quiz": C,
        "lp_enroll_student": C,
        "lp_list_enrolled_courses": R,
        "lp_get_student_progress": R,
        "lp_finish_course": U,
        "lp_finish_lesson": U,
        "lp_retake_course": U,
        "lp_start_quiz": U,
        "lp_submit_quiz": U,
    }

    for name, tag in _all.items():
        register_tool_access(name, tag)


_register_all_tool_access()

# WordPress Capabilities Integration - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate the WordPress Capabilities/Roles API into Articulate so the MCP server checks capabilities before executing operations, the UI conditionally renders based on user permissions, and organization roles sync to WordPress roles.

**Architecture:** Add a `CapabilityChecker` service that fetches and caches WordPress user capabilities via GraphQL `viewer` query. Expose capabilities through a new REST endpoint and React context. Add pre-flight capability decorators on MCP tools. Sync Articulate org/tenant roles to WordPress user roles during provisioning and role changes.

**Tech Stack:** Python (aiomysql, httpx, Redis caching), Next.js/React (Context API, fetch), WordPress REST API and WPGraphQL `viewer` query, Docker compose templates.

---

## Phase 1: Visibility and Awareness

### Task 1: Add GraphQL `viewer` Capabilities Query

**Files:**
- Modify: `mcp-server/src/articulate_mcp/graphql/queries.py`

**Step 1: Add the query constant**

Append to the end of `mcp-server/src/articulate_mcp/graphql/queries.py`:

```python
GET_VIEWER_CAPABILITIES = """
query GetViewerCapabilities {
  viewer {
    databaseId
    username
    email
    roles {
      nodes {
        name
      }
    }
  }
}
"""
```

Note: WPGraphQL does not expose raw capabilities in the `viewer` query by default. We rely on `roles` and map them to known capability sets in Python code.

**Step 2: Commit**

```bash
git add mcp-server/src/articulate_mcp/graphql/queries.py
git commit -m "feat: add GraphQL viewer capabilities query"
```

---

### Task 2: Create CapabilityChecker Service

**Files:**
- Create: `mcp-server/src/articulate_mcp/capability_checker.py`
- Create: `mcp-server/tests/test_capability_checker.py`

**Step 1: Write the test**

Create `mcp-server/tests/test_capability_checker.py`:

```python
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
        # Should be union of both role capabilities
        assert "edit_others_posts" in caps  # from editor
        assert "upload_files" in caps  # from author

    def test_get_capabilities_for_unknown_role(self):
        checker = CapabilityChecker()
        caps = checker.get_capabilities_for_roles(["custom_role"])
        assert caps == {"read"}  # fallback to subscriber-level

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
        assert "publish_posts" not in missing  # author can publish

    def test_operation_mapping(self):
        checker = CapabilityChecker()
        required = checker.get_required_capabilities("create_post")
        assert "edit_posts" in required

    def test_unknown_operation_returns_empty(self):
        checker = CapabilityChecker()
        required = checker.get_required_capabilities("unknown_op")
        assert required == []
```

**Step 2: Run test to verify it fails**

```bash
cd /home/xyzzy/wp-ai && docker compose -f docker-compose.production.yml exec mcp-server python -m pytest mcp-server/tests/test_capability_checker.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'articulate_mcp.capability_checker'`

**Step 3: Write the implementation**

Create `mcp-server/src/articulate_mcp/capability_checker.py`:

```python
"""WordPress Capabilities Checker.

Maps WordPress roles to capabilities and provides pre-flight
permission checking for MCP tool operations.
"""

import logging
from typing import Union

logger = logging.getLogger("articulate-mcp")

# WordPress built-in role capability mappings
# Reference: https://wordpress.org/documentation/article/roles-and-capabilities/
ROLE_CAPABILITIES: dict[str, set[str]] = {
    "administrator": {
        "read",
        "edit_posts", "edit_others_posts", "edit_published_posts", "edit_private_posts",
        "publish_posts", "delete_posts", "delete_others_posts", "delete_published_posts", "delete_private_posts",
        "read_private_posts",
        "edit_pages", "edit_others_pages", "edit_published_pages", "edit_private_pages",
        "publish_pages", "delete_pages", "delete_others_pages", "delete_published_pages", "delete_private_pages",
        "read_private_pages",
        "upload_files",
        "manage_categories",
        "manage_options",
        "edit_theme_options",
        "moderate_comments",
        "manage_links",
        "create_users", "edit_users", "delete_users", "list_users", "promote_users",
        "install_plugins", "activate_plugins", "edit_plugins", "delete_plugins",
        "install_themes", "edit_themes", "delete_themes", "switch_themes",
        "unfiltered_html", "unfiltered_upload",
        "export", "import",
    },
    "editor": {
        "read",
        "edit_posts", "edit_others_posts", "edit_published_posts", "edit_private_posts",
        "publish_posts", "delete_posts", "delete_others_posts", "delete_published_posts", "delete_private_posts",
        "read_private_posts",
        "edit_pages", "edit_others_pages", "edit_published_pages", "edit_private_pages",
        "publish_pages", "delete_pages", "delete_others_pages", "delete_published_pages", "delete_private_pages",
        "read_private_pages",
        "upload_files",
        "manage_categories",
        "manage_links",
        "moderate_comments",
        "unfiltered_html",
    },
    "author": {
        "read",
        "edit_posts", "edit_published_posts",
        "publish_posts", "delete_posts", "delete_published_posts",
        "upload_files",
    },
    "contributor": {
        "read",
        "edit_posts", "delete_posts",
    },
    "subscriber": {
        "read",
    },
}

# Map MCP tool operations to required WordPress capabilities
OPERATION_CAPABILITIES: dict[str, list[str]] = {
    # Posts
    "get_posts": ["read"],
    "get_post": ["read"],
    "create_post": ["edit_posts"],
    "update_post": ["edit_posts"],
    "delete_post": ["delete_posts"],
    "publish_post": ["publish_posts"],
    # Pages
    "get_pages": ["read"],
    "get_page": ["read"],
    "create_page": ["edit_pages"],
    "update_page": ["edit_pages"],
    "delete_page": ["delete_pages"],
    "publish_page": ["publish_pages"],
    # Media
    "upload_media": ["upload_files"],
    "get_media": ["read"],
    "delete_media": ["upload_files"],
    # Taxonomies
    "manage_categories": ["manage_categories"],
    "manage_tags": ["manage_categories"],
    # Settings
    "get_settings": ["manage_options"],
    "update_settings": ["manage_options"],
    "get_front_page_settings": ["manage_options"],
    "set_front_page": ["manage_options"],
    # Menus
    "manage_menus": ["edit_theme_options"],
    # Templates
    "manage_templates": ["edit_theme_options"],
    # Users
    "list_users": ["list_users"],
    "create_user": ["create_users"],
    "update_user_role": ["promote_users"],
    "delete_user": ["delete_users"],
    # SEO (custom - authors can edit their own post SEO)
    "update_seo": ["edit_posts"],
}


class CapabilityChecker:
    """Checks WordPress capabilities for operations."""

    def get_capabilities_for_roles(self, roles: list[str]) -> set[str]:
        """Get the union of capabilities for a list of WordPress roles."""
        caps = set()
        for role in roles:
            role_lower = role.lower()
            if role_lower in ROLE_CAPABILITIES:
                caps |= ROLE_CAPABILITIES[role_lower]
            else:
                logger.warning("Unknown WordPress role: %s, defaulting to subscriber", role)
                caps |= ROLE_CAPABILITIES["subscriber"]
        if not caps:
            caps = {"read"}
        return caps

    def check(
        self,
        roles: list[str],
        required: Union[str, list[str]],
    ) -> tuple[bool, list[str]]:
        """Check if roles have the required capabilities.

        Args:
            roles: List of WordPress role names
            required: Single capability or list of capabilities

        Returns:
            Tuple of (has_all, missing_capabilities)
        """
        if isinstance(required, str):
            required = [required]

        user_caps = self.get_capabilities_for_roles(roles)
        missing = [cap for cap in required if cap not in user_caps]
        return len(missing) == 0, missing

    def get_required_capabilities(self, operation: str) -> list[str]:
        """Get the required WordPress capabilities for an MCP operation."""
        return OPERATION_CAPABILITIES.get(operation, [])

    def check_operation(
        self,
        roles: list[str],
        operation: str,
    ) -> tuple[bool, list[str]]:
        """Check if roles can perform a specific MCP operation.

        Args:
            roles: WordPress role names
            operation: MCP operation name (e.g., 'create_post')

        Returns:
            Tuple of (allowed, missing_capabilities)
        """
        required = self.get_required_capabilities(operation)
        if not required:
            return True, []
        return self.check(roles, required)


# Global instance
capability_checker = CapabilityChecker()
```

**Step 4: Run tests to verify they pass**

```bash
cd /home/xyzzy/wp-ai && docker compose -f docker-compose.production.yml exec mcp-server python -m pytest mcp-server/tests/test_capability_checker.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add mcp-server/src/articulate_mcp/capability_checker.py mcp-server/tests/test_capability_checker.py
git commit -m "feat: add CapabilityChecker service with role-capability mapping"
```

---

### Task 3: Add Capabilities REST Endpoint and MCP Tool

**Files:**
- Create: `mcp-server/src/articulate_mcp/routes/capabilities.py`
- Create: `mcp-server/src/articulate_mcp/tools/capabilities.py`
- Modify: `mcp-server/src/articulate_mcp/server.py`
- Modify: `mcp-server/src/articulate_mcp/graphql/queries.py` (already done in Task 1)

**Step 1: Create the REST endpoint**

Create `mcp-server/src/articulate_mcp/routes/capabilities.py`:

```python
"""REST endpoints for WordPress capabilities."""

import logging
from starlette.responses import JSONResponse

from articulate_mcp.decorators import require_auth
from articulate_mcp.connection_manager import connection_manager
from articulate_mcp.graphql.client import get_graphql_client
from articulate_mcp.graphql.queries import GET_VIEWER_CAPABILITIES
from articulate_mcp.capability_checker import capability_checker

logger = logging.getLogger("articulate-mcp")


@require_auth
async def get_capabilities_endpoint(request):
    """Get WordPress capabilities for the user's active connection.

    Returns the WordPress roles and resolved capabilities for the
    currently active WordPress connection.
    """
    user = request.state.user

    # Get active connection
    connection = await connection_manager.get_active_connection(user["id"])
    if not connection:
        return JSONResponse(
            {"error": "No active WordPress connection"},
            status_code=400,
        )

    # Fetch viewer info from WordPress via GraphQL
    try:
        client = await get_graphql_client(connection["id"], user["id"])
        result = await client.query(
            GET_VIEWER_CAPABILITIES,
            use_cache=True,
            user_id=user["id"],
        )

        viewer = result.get("viewer")
        if not viewer:
            return JSONResponse(
                {"error": "Could not fetch WordPress user info"},
                status_code=502,
            )

        # Extract roles
        roles = [node["name"] for node in viewer.get("roles", {}).get("nodes", [])]

        # Resolve capabilities from roles
        capabilities = sorted(capability_checker.get_capabilities_for_roles(roles))

        return JSONResponse({
            "wp_user_id": viewer.get("databaseId"),
            "wp_username": viewer.get("username"),
            "wp_email": viewer.get("email"),
            "roles": roles,
            "capabilities": capabilities,
            "is_administrator": "administrator" in roles,
            "connection_id": connection["id"],
            "connection_name": connection["name"],
        })

    except Exception as e:
        logger.error("Failed to fetch capabilities: %s", e)
        return JSONResponse(
            {"error": f"Failed to fetch WordPress capabilities: {str(e)}"},
            status_code=502,
        )
```

**Step 2: Create the MCP tool**

Create `mcp-server/src/articulate_mcp/tools/capabilities.py`:

```python
"""MCP tools for WordPress user capabilities and role management."""

import logging
from mcp.server.fastmcp import FastMCP

from articulate_mcp.graphql.client import get_graphql_client
from articulate_mcp.graphql.queries import GET_VIEWER_CAPABILITIES
from articulate_mcp.capability_checker import capability_checker
from articulate_mcp.tools.utils import get_connection_info

logger = logging.getLogger("articulate-mcp")


def register(mcp: FastMCP) -> None:
    """Register capability-related MCP tools."""

    @mcp.tool()
    async def get_wp_capabilities(context=None) -> str:
        """Get the current WordPress user's roles and capabilities.

        Returns the authenticated WordPress user's roles, capabilities,
        and what operations they can perform. Use this to understand
        what the current user is allowed to do on the WordPress site.
        """
        connection_id, user_id = get_connection_info(context)
        client = await get_graphql_client(connection_id, user_id)

        result = await client.query(
            GET_VIEWER_CAPABILITIES,
            use_cache=True,
            user_id=user_id,
        )

        viewer = result.get("viewer")
        if not viewer:
            return "Error: Could not fetch WordPress user info. Check connection credentials."

        roles = [node["name"] for node in viewer.get("roles", {}).get("nodes", [])]
        capabilities = sorted(capability_checker.get_capabilities_for_roles(roles))

        lines = [
            f"WordPress User: {viewer.get('username')} (ID: {viewer.get('databaseId')})",
            f"Email: {viewer.get('email')}",
            f"Roles: {', '.join(roles)}",
            f"",
            f"Capabilities ({len(capabilities)}):",
        ]
        for cap in capabilities:
            lines.append(f"  - {cap}")

        # Show what operations are available
        lines.append("")
        lines.append("Available Operations:")
        from articulate_mcp.capability_checker import OPERATION_CAPABILITIES
        for op, required_caps in sorted(OPERATION_CAPABILITIES.items()):
            allowed, missing = capability_checker.check(roles, required_caps)
            status = "✓" if allowed else "✗"
            lines.append(f"  {status} {op}")
            if not allowed:
                lines.append(f"    Missing: {', '.join(missing)}")

        return "\n".join(lines)
```

**Step 3: Wire into server.py**

Add to the imports section of `mcp-server/src/articulate_mcp/server.py`:

```python
from articulate_mcp.tools import capabilities as capabilities_tools
from articulate_mcp.routes.capabilities import get_capabilities_endpoint
```

Add to the tool registration block (after the last `xxx.register(mcp)` line):

```python
capabilities_tools.register(mcp)
```

Add to the routes list (in the `routes=[]` section):

```python
Route("/capabilities", get_capabilities_endpoint, methods=["GET"]),
```

**Step 4: Commit**

```bash
git add mcp-server/src/articulate_mcp/routes/capabilities.py \
       mcp-server/src/articulate_mcp/tools/capabilities.py \
       mcp-server/src/articulate_mcp/server.py
git commit -m "feat: add capabilities REST endpoint and MCP tool"
```

---

### Task 4: Add Next.js API Route and CapabilitiesContext

**Files:**
- Create: `web/src/app/api/capabilities/route.ts`
- Create: `web/src/contexts/capabilities-context.tsx`
- Modify: `web/src/app/layout.tsx` (or wherever providers are wrapped)

**Step 1: Create the Next.js API route**

Create `web/src/app/api/capabilities/route.ts`:

```typescript
import { NextResponse } from "next/server";
import { getSessionHeaders } from "@/lib/server-auth";

const MCP_URL = process.env.MCP_SERVER_URL || "http://mcp-server:8000";

export async function GET() {
  try {
    const headers = await getSessionHeaders();
    if (!headers) {
      return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
    }

    const res = await fetch(`${MCP_URL}/capabilities`, {
      headers: {
        ...headers,
        "Content-Type": "application/json",
      },
    });

    const data = await res.json();

    if (!res.ok) {
      return NextResponse.json(data, { status: res.status });
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error("Capabilities fetch error:", error);
    return NextResponse.json(
      { error: "Failed to fetch capabilities" },
      { status: 500 }
    );
  }
}
```

**Step 2: Create the CapabilitiesContext**

Create `web/src/contexts/capabilities-context.tsx`:

```tsx
"use client";

import React, { createContext, useContext, useState, useCallback, useEffect } from "react";
import { useAuth } from "./auth-context";
import { useConnections } from "./connection-context";

interface WPCapabilities {
  wp_user_id: number;
  wp_username: string;
  wp_email: string;
  roles: string[];
  capabilities: string[];
  is_administrator: boolean;
  connection_id: number;
  connection_name: string;
}

interface CapabilitiesContextType {
  capabilities: WPCapabilities | null;
  isLoading: boolean;
  error: string | null;
  hasCapability: (cap: string) => boolean;
  canPerformOperation: (op: string) => boolean;
  refreshCapabilities: () => Promise<void>;
}

// Map MCP operations to required capabilities (mirrors Python OPERATION_CAPABILITIES)
const OPERATION_CAPABILITIES: Record<string, string[]> = {
  create_post: ["edit_posts"],
  update_post: ["edit_posts"],
  delete_post: ["delete_posts"],
  publish_post: ["publish_posts"],
  create_page: ["edit_pages"],
  update_page: ["edit_pages"],
  delete_page: ["delete_pages"],
  publish_page: ["publish_pages"],
  upload_media: ["upload_files"],
  manage_categories: ["manage_categories"],
  manage_tags: ["manage_categories"],
  get_settings: ["manage_options"],
  update_settings: ["manage_options"],
  manage_menus: ["edit_theme_options"],
  manage_templates: ["edit_theme_options"],
  list_users: ["list_users"],
  create_user: ["create_users"],
  update_user_role: ["promote_users"],
};

const CapabilitiesContext = createContext<CapabilitiesContextType | undefined>(undefined);

export function CapabilitiesProvider({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  const { activeConnection } = useConnections();
  const [capabilities, setCapabilities] = useState<WPCapabilities | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshCapabilities = useCallback(async () => {
    if (!isAuthenticated || !activeConnection) {
      setCapabilities(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const res = await fetch("/api/capabilities");
      if (res.ok) {
        const data = await res.json();
        setCapabilities(data);
      } else {
        const data = await res.json().catch(() => ({}));
        setError(data.error || "Failed to fetch capabilities");
        setCapabilities(null);
      }
    } catch (err) {
      setError("Failed to fetch capabilities");
      setCapabilities(null);
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated, activeConnection]);

  // Refresh when auth or connection changes
  useEffect(() => {
    refreshCapabilities();
  }, [refreshCapabilities]);

  const hasCapability = useCallback(
    (cap: string): boolean => {
      if (!capabilities) return false;
      if (capabilities.is_administrator) return true;
      return capabilities.capabilities.includes(cap);
    },
    [capabilities]
  );

  const canPerformOperation = useCallback(
    (op: string): boolean => {
      if (!capabilities) return false;
      if (capabilities.is_administrator) return true;
      const required = OPERATION_CAPABILITIES[op];
      if (!required) return true; // unknown operation = allow (WP will enforce)
      return required.every((cap) => capabilities.capabilities.includes(cap));
    },
    [capabilities]
  );

  return (
    <CapabilitiesContext.Provider
      value={{
        capabilities,
        isLoading,
        error,
        hasCapability,
        canPerformOperation,
        refreshCapabilities,
      }}
    >
      {children}
    </CapabilitiesContext.Provider>
  );
}

export function useCapabilities() {
  const context = useContext(CapabilitiesContext);
  if (context === undefined) {
    throw new Error("useCapabilities must be used within a CapabilitiesProvider");
  }
  return context;
}
```

**Step 3: Wire into the provider tree**

Find the file that wraps `<AuthProvider>` and `<ConnectionProvider>` (likely `web/src/app/layout.tsx` or a providers component). Add `<CapabilitiesProvider>` **inside** `<ConnectionProvider>` since it depends on both auth and connections:

```tsx
import { CapabilitiesProvider } from "@/contexts/capabilities-context";

// In the provider tree:
<AuthProvider>
  <ConnectionProvider>
    <CapabilitiesProvider>
      {children}
    </CapabilitiesProvider>
  </ConnectionProvider>
</AuthProvider>
```

**Step 4: Commit**

```bash
git add web/src/app/api/capabilities/route.ts \
       web/src/contexts/capabilities-context.tsx \
       web/src/app/layout.tsx  # or wherever providers are
git commit -m "feat: add CapabilitiesContext and API route for WordPress capabilities"
```

---

### Task 5: Add Capability-Aware UI Rendering

**Files:**
- Modify: `web/src/components/editor/publish-panel.tsx`
- Modify: `web/src/components/editor/featured-image-panel.tsx`
- Modify: `web/src/components/layout/sidebar.tsx`

**Step 1: Update publish-panel.tsx**

Import and use capabilities in the PublishPanel component. If the user lacks `publish_posts`, show "Submit for Review" instead of "Publish Now":

```tsx
import { useCapabilities } from "@/contexts/capabilities-context";

// Inside the component:
const { canPerformOperation } = useCapabilities();
const canPublish = canPerformOperation("publish_post");
```

Conditionally render:
- If `canPublish` is true: Show existing "Publish Now" and "Schedule" buttons
- If `canPublish` is false: Replace "Publish Now" with "Submit for Review" (sets status to "pending")
- The schedule button should also be hidden if the user can't publish

**Step 2: Update featured-image-panel.tsx**

```tsx
import { useCapabilities } from "@/contexts/capabilities-context";

// Inside the component:
const { canPerformOperation } = useCapabilities();
const canUpload = canPerformOperation("upload_media");
```

If `canUpload` is false:
- Disable the file upload input
- Show a message: "Your WordPress role does not allow file uploads"
- The "From URL" tab can still be shown (URL-based featured images may not require upload_files)

**Step 3: Update sidebar.tsx**

This is a lightweight change - currently the sidebar only shows posts. When we add more navigation items in the future (Pages, Media, Settings), this context will gate visibility. For now, just add the import so it's ready:

```tsx
import { useCapabilities } from "@/contexts/capabilities-context";

// Inside the component (for future use):
const { hasCapability, canPerformOperation } = useCapabilities();
```

No UI changes needed in the sidebar yet since it only lists posts (which all roles can read).

**Step 4: Commit**

```bash
git add web/src/components/editor/publish-panel.tsx \
       web/src/components/editor/featured-image-panel.tsx \
       web/src/components/layout/sidebar.tsx
git commit -m "feat: add capability-aware UI rendering for publish and media panels"
```

---

## Phase 2: Pre-flight Capability Checks

### Task 6: Add `@require_wp_capability` Decorator

**Files:**
- Modify: `mcp-server/src/articulate_mcp/decorators.py`
- Create: `mcp-server/tests/test_capability_decorators.py`

**Step 1: Write the test**

Create `mcp-server/tests/test_capability_decorators.py`:

```python
"""Tests for WordPress capability decorators."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse

from articulate_mcp.decorators import require_wp_capability


class TestRequireWpCapability:
    """Test the require_wp_capability decorator."""

    def setup_method(self):
        """Create test endpoint with decorator."""

        @require_wp_capability("publish_posts")
        async def publish_endpoint(request):
            return JSONResponse({"success": True})

        @require_wp_capability(["edit_others_posts", "manage_categories"])
        async def admin_endpoint(request):
            return JSONResponse({"success": True})

        app = Starlette(routes=[
            Route("/publish", publish_endpoint, methods=["POST"]),
            Route("/admin", admin_endpoint, methods=["POST"]),
        ])
        self.client = TestClient(app)

    def _make_request(self, path, roles):
        """Make request with mocked auth state."""
        # We need to mock the request.state
        # For unit testing, we test the decorator logic directly
        pass

    def test_decorator_exists(self):
        """Verify the decorator is importable."""
        assert callable(require_wp_capability)

    @pytest.mark.asyncio
    async def test_passes_with_sufficient_role(self):
        """Test that administrator passes publish_posts check."""
        @require_wp_capability("publish_posts")
        async def endpoint(request):
            return JSONResponse({"success": True})

        request = MagicMock()
        request.state.user = {"id": 1}
        request.state.wp_roles = ["administrator"]

        response = await endpoint(request)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_fails_with_insufficient_role(self):
        """Test that contributor fails publish_posts check."""
        @require_wp_capability("publish_posts")
        async def endpoint(request):
            return JSONResponse({"success": True})

        request = MagicMock()
        request.state.user = {"id": 1}
        request.state.wp_roles = ["contributor"]

        response = await endpoint(request)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_fails_with_no_roles(self):
        """Test that missing wp_roles returns 403."""
        @require_wp_capability("publish_posts")
        async def endpoint(request):
            return JSONResponse({"success": True})

        request = MagicMock()
        request.state.user = {"id": 1}
        request.state.wp_roles = None

        response = await endpoint(request)
        assert response.status_code == 403
```

**Step 2: Run test to verify it fails**

```bash
cd /home/xyzzy/wp-ai && docker compose -f docker-compose.production.yml exec mcp-server python -m pytest mcp-server/tests/test_capability_decorators.py -v
```

Expected: FAIL (import error or missing function)

**Step 3: Implement the decorator**

Add to `mcp-server/src/articulate_mcp/decorators.py`:

```python
from articulate_mcp.capability_checker import capability_checker


def require_wp_capability(required_capabilities):
    """Decorator that checks WordPress capabilities before executing an endpoint.

    Args:
        required_capabilities: Single capability string or list of capabilities.

    Usage:
        @require_wp_capability("publish_posts")
        async def publish_endpoint(request):
            ...

        @require_wp_capability(["edit_others_posts", "manage_categories"])
        async def admin_endpoint(request):
            ...

    The decorator expects request.state.wp_roles to be set (by middleware).
    If wp_roles is not available, it returns 403.
    """
    if isinstance(required_capabilities, str):
        required_capabilities = [required_capabilities]

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(request, *args, **kwargs):
            # Get WordPress roles from request state
            wp_roles = getattr(request.state, "wp_roles", None)

            if not wp_roles:
                return JSONResponse(
                    {
                        "error": "WordPress role information not available",
                        "detail": "No active WordPress connection or roles could not be determined",
                    },
                    status_code=403,
                )

            has_caps, missing = capability_checker.check(wp_roles, required_capabilities)

            if not has_caps:
                role_names = ", ".join(wp_roles)
                missing_names = ", ".join(missing)
                return JSONResponse(
                    {
                        "error": "Insufficient WordPress capabilities",
                        "detail": f"Your WordPress role ({role_names}) lacks: {missing_names}",
                        "missing_capabilities": missing,
                        "your_roles": wp_roles,
                    },
                    status_code=403,
                )

            return await func(request, *args, **kwargs)

        return wrapper

    return decorator
```

Also add `import functools` at the top of `decorators.py` if not already present.

**Step 4: Run tests**

```bash
cd /home/xyzzy/wp-ai && docker compose -f docker-compose.production.yml exec mcp-server python -m pytest mcp-server/tests/test_capability_decorators.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add mcp-server/src/articulate_mcp/decorators.py \
       mcp-server/tests/test_capability_decorators.py
git commit -m "feat: add @require_wp_capability decorator for pre-flight permission checks"
```

---

### Task 7: Inject WordPress Roles into Auth Middleware

**Files:**
- Modify: `mcp-server/src/articulate_mcp/middleware/auth.py`

**Step 1: Update the auth middleware**

The middleware currently fetches the user and active connection. After fetching the connection, it should also fetch and cache the WordPress viewer roles.

In the section where `scope["state"]["connection"]` is set (for MCP endpoints), add:

```python
# After setting scope["state"]["connection"]:
# Fetch and cache WordPress roles
from articulate_mcp.graphql.client import get_graphql_client
from articulate_mcp.graphql.queries import GET_VIEWER_CAPABILITIES

try:
    client = await get_graphql_client(connection["id"], user["id"])
    viewer_result = await client.query(
        GET_VIEWER_CAPABILITIES,
        use_cache=True,
        user_id=user["id"],
    )
    viewer = viewer_result.get("viewer")
    if viewer:
        roles = [n["name"] for n in viewer.get("roles", {}).get("nodes", [])]
        scope["state"]["wp_roles"] = roles
    else:
        scope["state"]["wp_roles"] = []
except Exception as e:
    logger.warning("Could not fetch WP roles: %s", e)
    scope["state"]["wp_roles"] = []
```

Also add `wp_roles` injection for non-MCP authenticated endpoints. For REST endpoints that may use `@require_wp_capability`, the middleware should attempt to fetch roles if the user has an active connection:

```python
# For non-MCP authenticated endpoints, try to get WP roles
try:
    from articulate_mcp.connection_manager import connection_manager as conn_mgr
    active = await conn_mgr.get_active_connection(user["id"])
    if active:
        client = await get_graphql_client(active["id"], user["id"])
        viewer_result = await client.query(
            GET_VIEWER_CAPABILITIES,
            use_cache=True,
            user_id=user["id"],
        )
        viewer = viewer_result.get("viewer")
        if viewer:
            roles = [n["name"] for n in viewer.get("roles", {}).get("nodes", [])]
            scope["state"]["wp_roles"] = roles
        else:
            scope["state"]["wp_roles"] = []
    else:
        scope["state"]["wp_roles"] = []
except Exception:
    scope["state"]["wp_roles"] = []
```

**Important:** The GraphQL query uses Redis caching (TTL 300s from the `viewer` query pattern), so this doesn't add a network call on every request. Only the first request per 5-minute window will hit WordPress.

**Step 2: Commit**

```bash
git add mcp-server/src/articulate_mcp/middleware/auth.py
git commit -m "feat: inject WordPress roles into request state via auth middleware"
```

---

### Task 8: Add Capability Pre-flight to MCP Tools

**Files:**
- Modify: `mcp-server/src/articulate_mcp/tools/posts.py`
- Modify: `mcp-server/src/articulate_mcp/tools/media.py`
- Modify: `mcp-server/src/articulate_mcp/tools/settings.py`
- Modify: `mcp-server/src/articulate_mcp/tools/menus.py`
- Modify: `mcp-server/src/articulate_mcp/tools/templates.py`

**Step 1: Add a helper function to tools/utils.py (or wherever `get_connection_info` is)**

Find the file containing `get_connection_info` and add:

```python
from articulate_mcp.capability_checker import capability_checker


def check_wp_capability(context, operation: str) -> tuple[bool, str]:
    """Check if the current user has WordPress capabilities for an operation.

    Returns (allowed, error_message). If allowed, error_message is empty.
    Does NOT block - returns a warning message that tools can include in output.
    """
    try:
        wp_roles = context.get("wp_roles") or []
        if not wp_roles:
            return True, ""  # No role info available, let WordPress handle it

        allowed, missing = capability_checker.check_operation(wp_roles, operation)
        if not allowed:
            role_str = ", ".join(wp_roles)
            missing_str = ", ".join(missing)
            return False, (
                f"Warning: Your WordPress role ({role_str}) may lack "
                f"the capabilities needed for this operation: {missing_str}. "
                f"The operation may fail on the WordPress side."
            )
        return True, ""
    except Exception:
        return True, ""  # On error, let WordPress handle authorization
```

**Step 2: Add pre-flight checks to write operations in posts.py**

In `create_post()`, at the beginning of the function body:

```python
allowed, warning = check_wp_capability(context, "create_post")
if not allowed:
    return warning
```

In `update_post()`:

```python
allowed, warning = check_wp_capability(context, "update_post")
if not allowed:
    return warning
```

In `delete_post()`:

```python
allowed, warning = check_wp_capability(context, "delete_post")
if not allowed:
    return warning
```

**Step 3: Add similar checks to media.py, settings.py, menus.py, templates.py**

For each tool's write operation, add the same pattern with the appropriate operation name.

**Step 4: Commit**

```bash
git add mcp-server/src/articulate_mcp/tools/posts.py \
       mcp-server/src/articulate_mcp/tools/media.py \
       mcp-server/src/articulate_mcp/tools/settings.py \
       mcp-server/src/articulate_mcp/tools/menus.py \
       mcp-server/src/articulate_mcp/tools/templates.py \
       mcp-server/src/articulate_mcp/tools/utils.py
git commit -m "feat: add capability pre-flight checks to MCP write tools"
```

---

### Task 9: Show WordPress Role in Tenant/Org Member Lists

**Files:**
- Modify: `web/src/app/sites/page.tsx`
- Modify: `web/src/app/organizations/[id]/page.tsx`

**Step 1: Show WP role info on the Sites page**

In the `TenantCard` component, add a small badge or text showing the current WordPress role. Use the capabilities context:

```tsx
import { useCapabilities } from "@/contexts/capabilities-context";

// Inside TenantCard:
const { capabilities } = useCapabilities();

// In the card header area, after the status badge:
{capabilities && (
  <span className="text-xs text-muted-foreground">
    WP: {capabilities.roles.join(", ")}
  </span>
)}
```

**Step 2: Show WP role alongside org role in the organization page**

This is a future enhancement once per-user WP accounts exist. For now, add a placeholder comment:

```tsx
// TODO: Show WordPress role alongside organization role when per-user WP accounts are implemented
```

**Step 3: Commit**

```bash
git add web/src/app/sites/page.tsx web/src/app/organizations/[id]/page.tsx
git commit -m "feat: show WordPress role info in sites page"
```

---

## Phase 3: Role Management and Synchronization

### Task 10: Add WordPress User REST API Tools

**Files:**
- Create: `mcp-server/src/articulate_mcp/tools/wp_users.py`
- Modify: `mcp-server/src/articulate_mcp/server.py`

**Step 1: Create the WP users tool module**

Create `mcp-server/src/articulate_mcp/tools/wp_users.py`:

```python
"""MCP tools for WordPress user management via REST API."""

import logging
import httpx
from mcp.server.fastmcp import FastMCP

from articulate_mcp.connection_manager import connection_manager
from articulate_mcp.tools.utils import get_connection_info

logger = logging.getLogger("articulate-mcp")


async def _get_wp_rest_client(connection_id: int, user_id: int):
    """Get an httpx client configured for WordPress REST API."""
    connection = await connection_manager.get_connection(connection_id, user_id)
    if not connection:
        raise ValueError("Connection not found")

    wp_url = connection["wp_url"].rstrip("/")
    wp_user = connection["wp_user"]
    wp_pass = connection["wp_app_password"]

    return httpx.AsyncClient(
        base_url=f"{wp_url}/wp-json/wp/v2",
        auth=(wp_user, wp_pass),
        timeout=30.0,
    )


def register(mcp: FastMCP) -> None:
    """Register WordPress user management tools."""

    @mcp.tool()
    async def get_wp_users(
        role: str = "",
        search: str = "",
        per_page: int = 20,
        context=None,
    ) -> str:
        """List WordPress users on the connected site.

        Args:
            role: Filter by role (administrator, editor, author, contributor, subscriber)
            search: Search by username, email, or display name
            per_page: Number of results (max 100)
        """
        connection_id, user_id = get_connection_info(context)

        async with await _get_wp_rest_client(connection_id, user_id) as client:
            params = {"per_page": min(per_page, 100), "context": "edit"}
            if role:
                params["roles"] = role
            if search:
                params["search"] = search

            response = await client.get("/users", params=params)

            if response.status_code == 403:
                return "Error: Your WordPress user lacks the 'list_users' capability."
            response.raise_for_status()

            users = response.json()
            if not users:
                return "No WordPress users found."

            lines = [f"WordPress Users ({len(users)}):"]
            for u in users:
                roles = ", ".join(u.get("roles", []))
                lines.append(
                    f"  - {u['name']} ({u['username']}) "
                    f"| Email: {u['email']} "
                    f"| Roles: {roles} "
                    f"| ID: {u['id']}"
                )
            return "\n".join(lines)

    @mcp.tool()
    async def create_wp_user(
        username: str,
        email: str,
        password: str,
        role: str = "subscriber",
        first_name: str = "",
        last_name: str = "",
        context=None,
    ) -> str:
        """Create a new WordPress user on the connected site.

        Args:
            username: Login username
            email: Email address
            password: User password
            role: WordPress role (administrator, editor, author, contributor, subscriber)
            first_name: Optional first name
            last_name: Optional last name
        """
        connection_id, user_id = get_connection_info(context)

        valid_roles = {"administrator", "editor", "author", "contributor", "subscriber"}
        if role not in valid_roles:
            return f"Error: Invalid role '{role}'. Must be one of: {', '.join(sorted(valid_roles))}"

        async with await _get_wp_rest_client(connection_id, user_id) as client:
            payload = {
                "username": username,
                "email": email,
                "password": password,
                "roles": [role],
            }
            if first_name:
                payload["first_name"] = first_name
            if last_name:
                payload["last_name"] = last_name

            response = await client.post("/users", json=payload)

            if response.status_code == 403:
                return "Error: Your WordPress user lacks the 'create_users' capability."
            if response.status_code == 400:
                error = response.json()
                return f"Error: {error.get('message', 'Bad request')}"
            response.raise_for_status()

            user = response.json()
            return (
                f"Created WordPress user:\n"
                f"  Username: {user['username']}\n"
                f"  Email: {user['email']}\n"
                f"  Role: {role}\n"
                f"  ID: {user['id']}"
            )

    @mcp.tool()
    async def update_wp_user_role(
        wp_user_id: int,
        role: str,
        context=None,
    ) -> str:
        """Change a WordPress user's role.

        Args:
            wp_user_id: WordPress user ID
            role: New role (administrator, editor, author, contributor, subscriber)
        """
        connection_id, user_id = get_connection_info(context)

        valid_roles = {"administrator", "editor", "author", "contributor", "subscriber"}
        if role not in valid_roles:
            return f"Error: Invalid role '{role}'. Must be one of: {', '.join(sorted(valid_roles))}"

        async with await _get_wp_rest_client(connection_id, user_id) as client:
            response = await client.post(
                f"/users/{wp_user_id}",
                json={"roles": [role]},
            )

            if response.status_code == 403:
                return "Error: Your WordPress user lacks the 'promote_users' capability."
            if response.status_code == 404:
                return f"Error: WordPress user ID {wp_user_id} not found."
            response.raise_for_status()

            user = response.json()
            return (
                f"Updated WordPress user role:\n"
                f"  User: {user['username']} (ID: {user['id']})\n"
                f"  New role: {role}"
            )
```

**Step 2: Register in server.py**

Add to imports:

```python
from articulate_mcp.tools import wp_users
```

Add to tool registration:

```python
wp_users.register(mcp)
```

**Step 3: Commit**

```bash
git add mcp-server/src/articulate_mcp/tools/wp_users.py \
       mcp-server/src/articulate_mcp/server.py
git commit -m "feat: add WordPress user management MCP tools (list, create, update role)"
```

---

### Task 11: Per-User WordPress Accounts for Tenants

**Files:**
- Modify: `mcp-server/src/articulate_mcp/tenants/manager.py`
- Modify: `mcp-server/src/articulate_mcp/user_manager.py`
- Create: `mcp-server/src/articulate_mcp/tenants/wp_user_sync.py`
- Modify: `templates/wordpress/mu-plugins/articulate-sso.php`

**Step 1: Create the WP user sync module**

Create `mcp-server/src/articulate_mcp/tenants/wp_user_sync.py`:

```python
"""Sync Articulate users to WordPress tenant users.

When a user is added to a tenant (or a tenant is provisioned), this module
creates corresponding WordPress users on the tenant's WordPress instance and
maps Articulate tenant roles to WordPress roles.
"""

import logging
import httpx

logger = logging.getLogger("articulate-mcp")

# Map Articulate tenant roles to WordPress roles
ROLE_MAP = {
    "owner": "administrator",
    "admin": "administrator",
    "editor": "editor",
    "viewer": "subscriber",
}


async def create_wp_user_for_tenant(
    wp_url: str,
    wp_admin_user: str,
    wp_admin_password: str,
    articulate_user_email: str,
    articulate_user_name: str,
    articulate_role: str,
) -> dict | None:
    """Create a WordPress user on a tenant site mapped to an Articulate user.

    Args:
        wp_url: Tenant's WordPress URL (internal Docker URL)
        wp_admin_user: Admin username for the tenant
        wp_admin_password: Admin app password for the tenant
        articulate_user_email: The Articulate user's email
        articulate_user_name: The Articulate user's display name
        articulate_role: Articulate tenant role (owner, admin, editor, viewer)

    Returns:
        Dict with wp_user_id and wp_role, or None on failure
    """
    wp_role = ROLE_MAP.get(articulate_role, "subscriber")

    # Generate a username from email (prefix before @)
    username = f"art_{articulate_user_email.split('@')[0]}"

    async with httpx.AsyncClient(
        base_url=f"{wp_url}/wp-json/wp/v2",
        auth=(wp_admin_user, wp_admin_password),
        timeout=30.0,
    ) as client:
        # Check if user already exists by email
        response = await client.get("/users", params={"search": articulate_user_email, "context": "edit"})
        if response.status_code == 200:
            users = response.json()
            for u in users:
                if u.get("email", "").lower() == articulate_user_email.lower():
                    # User exists, update role if needed
                    current_roles = u.get("roles", [])
                    if wp_role not in current_roles:
                        await client.post(f"/users/{u['id']}", json={"roles": [wp_role]})
                        logger.info("Updated existing WP user %s role to %s", u["username"], wp_role)
                    return {"wp_user_id": u["id"], "wp_role": wp_role, "wp_username": u["username"]}

        # Create new user
        import secrets
        password = secrets.token_urlsafe(32)

        response = await client.post("/users", json={
            "username": username,
            "email": articulate_user_email,
            "password": password,
            "roles": [wp_role],
            "first_name": articulate_user_name.split()[0] if articulate_user_name else "",
            "last_name": " ".join(articulate_user_name.split()[1:]) if articulate_user_name else "",
        })

        if response.status_code in (200, 201):
            user = response.json()
            logger.info("Created WP user %s with role %s", username, wp_role)
            return {"wp_user_id": user["id"], "wp_role": wp_role, "wp_username": user["username"]}
        else:
            error = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            logger.error("Failed to create WP user: %s %s", response.status_code, error.get("message", ""))
            return None


async def update_wp_user_role_for_tenant(
    wp_url: str,
    wp_admin_user: str,
    wp_admin_password: str,
    wp_user_id: int,
    new_articulate_role: str,
) -> bool:
    """Update a WordPress user's role when their Articulate tenant role changes.

    Args:
        wp_url: Tenant's WordPress URL
        wp_admin_user: Admin username
        wp_admin_password: Admin app password
        wp_user_id: WordPress user ID to update
        new_articulate_role: New Articulate role (owner, admin, editor, viewer)

    Returns:
        True if successful
    """
    wp_role = ROLE_MAP.get(new_articulate_role, "subscriber")

    async with httpx.AsyncClient(
        base_url=f"{wp_url}/wp-json/wp/v2",
        auth=(wp_admin_user, wp_admin_password),
        timeout=30.0,
    ) as client:
        response = await client.post(f"/users/{wp_user_id}", json={"roles": [wp_role]})
        if response.status_code == 200:
            logger.info("Updated WP user %d role to %s", wp_user_id, wp_role)
            return True
        else:
            logger.error("Failed to update WP user role: %s", response.status_code)
            return False
```

**Step 2: Update the SSO mu-plugin**

Modify `templates/wordpress/mu-plugins/articulate-sso.php` to look up the per-user WordPress account instead of always creating/using `articulate-admin`:

The token validation response from the MCP server should now include `wp_username` (the per-user WordPress username). The mu-plugin should authenticate as that user instead of the shared admin.

Update the section that creates/gets the user:

```php
// Instead of always using 'articulate-admin', use the username from the token response
$wp_username = isset($body['wp_username']) ? sanitize_user($body['wp_username']) : 'articulate-admin';
$user = get_user_by('login', $wp_username);

if (!$user) {
    // Fallback: create the user if not found (shouldn't happen normally)
    $user_id = wp_create_user($wp_username, wp_generate_password(32), $body['email'] ?? '');
    if (is_wp_error($user_id)) {
        wp_die('Failed to create user account.');
    }
    $user = get_user_by('id', $user_id);
    $user->set_role($body['wp_role'] ?? 'subscriber');
}
```

**Step 3: Update validate_wp_login_token in user_manager.py**

The `validate_wp_login_token` method should return the per-user WordPress username and role. Modify `mcp-server/src/articulate_mcp/user_manager.py`:

In the `validate_wp_login_token` method, after fetching the token and user, look up the user's WordPress username for that tenant:

```python
# After getting user and tenant_id from the token:
# Look up the user's WP username for this tenant
tenant_user = await db.fetchone(
    """
    SELECT wp_username, wp_role FROM tenant_users
    WHERE tenant_id = %s AND user_id = %s
    """,
    (token_data["tenant_id"], token_data["user_id"]),
)

return {
    "user_id": token_data["user_id"],
    "email": user["email"],
    "name": user.get("name", ""),
    "tenant_id": token_data["tenant_id"],
    "wp_username": tenant_user["wp_username"] if tenant_user and tenant_user.get("wp_username") else "articulate-admin",
    "wp_role": tenant_user["wp_role"] if tenant_user and tenant_user.get("wp_role") else "administrator",
}
```

**Step 4: Add wp_username and wp_role columns to tenant_users**

Create migration `mcp-server/migrations/005_tenant_user_wp_mapping.sql`:

```sql
-- Migration 005: Add WordPress user mapping to tenant_users
ALTER TABLE tenant_users
    ADD COLUMN wp_user_id INT DEFAULT NULL,
    ADD COLUMN wp_username VARCHAR(255) DEFAULT NULL,
    ADD COLUMN wp_role VARCHAR(50) DEFAULT NULL
```

**Step 5: Commit**

```bash
git add mcp-server/src/articulate_mcp/tenants/wp_user_sync.py \
       mcp-server/src/articulate_mcp/user_manager.py \
       templates/wordpress/mu-plugins/articulate-sso.php \
       mcp-server/migrations/005_tenant_user_wp_mapping.sql
git commit -m "feat: add per-user WordPress accounts for tenants with role mapping"
```

---

### Task 12: Wire Tenant Provisioning to Create Per-User WP Accounts

**Files:**
- Modify: `mcp-server/src/articulate_mcp/tenants/manager.py`
- Modify: `mcp-server/src/articulate_mcp/routes/tenants.py`

**Step 1: Update tenant provisioning**

In `mcp-server/src/articulate_mcp/tenants/manager.py`, after the tenant's WordPress instance is running and the admin user exists, create a WordPress user for the tenant owner.

In the `create_tenant` method, after the Docker containers are started and status is set to 'running', add:

```python
from articulate_mcp.tenants.wp_user_sync import create_wp_user_for_tenant

# Create a WP user for the owner
# Wait a moment for WordPress to be ready
import asyncio
await asyncio.sleep(5)  # Give WP time to initialize

owner = await db.fetchone(
    "SELECT email, name FROM articulate_users_auth WHERE id = %s",
    (owner_user_id,),
)

if owner:
    wp_user = await create_wp_user_for_tenant(
        wp_url=f"http://{slug}-wordpress:80",  # internal Docker URL
        wp_admin_user="admin",
        wp_admin_password=wp_admin_password,  # from secrets generated earlier
        articulate_user_email=owner["email"],
        articulate_user_name=owner.get("name", ""),
        articulate_role="owner",
    )
    if wp_user:
        await db.execute(
            """
            UPDATE tenant_users
            SET wp_user_id = %s, wp_username = %s, wp_role = %s
            WHERE tenant_id = %s AND user_id = %s
            """,
            (wp_user["wp_user_id"], wp_user["wp_username"], wp_user["wp_role"],
             tenant_id, owner_user_id),
        )
```

**Step 2: Add endpoint for adding team members to a tenant**

In the tenant routes, when a user is added to a tenant (if not already existing), also create their WordPress account:

This depends on the existing tenant member management flow. If there's already an endpoint for adding users to tenants, modify it to also call `create_wp_user_for_tenant`. If not, this will be implemented as part of the tenant member management feature.

**Step 3: Commit**

```bash
git add mcp-server/src/articulate_mcp/tenants/manager.py \
       mcp-server/src/articulate_mcp/routes/tenants.py
git commit -m "feat: create per-user WordPress accounts during tenant provisioning"
```

---

### Task 13: Add Role Sync on Articulate Role Change

**Files:**
- Create: `mcp-server/src/articulate_mcp/routes/tenant_members.py`
- Modify: `mcp-server/src/articulate_mcp/server.py`

**Step 1: Create tenant member routes**

Create `mcp-server/src/articulate_mcp/routes/tenant_members.py`:

```python
"""REST endpoints for managing tenant team members and role sync."""

import logging
from starlette.responses import JSONResponse

from articulate_mcp.decorators import require_auth
from articulate_mcp.database import db
from articulate_mcp.tenants.wp_user_sync import (
    create_wp_user_for_tenant,
    update_wp_user_role_for_tenant,
)

logger = logging.getLogger("articulate-mcp")


@require_auth
async def add_tenant_member_endpoint(request):
    """Add a user to a tenant and create their WordPress account."""
    user = request.state.user
    tenant_id = request.path_params["id"]
    data = await request.json()

    email = data.get("email")
    role = data.get("role", "viewer")

    if not email:
        return JSONResponse({"error": "Email required"}, status_code=400)

    if role not in ("admin", "editor", "viewer"):
        return JSONResponse({"error": "Invalid role"}, status_code=400)

    # Check requester is tenant owner or admin
    requester_role = await db.fetchone(
        "SELECT role FROM tenant_users WHERE tenant_id = %s AND user_id = %s",
        (tenant_id, user["id"]),
    )
    if not requester_role or requester_role["role"] not in ("owner", "admin"):
        return JSONResponse({"error": "Not authorized"}, status_code=403)

    # Find the user to add
    target_user = await db.fetchone(
        "SELECT id, email, name FROM articulate_users_auth WHERE email = %s",
        (email,),
    )
    if not target_user:
        return JSONResponse({"error": "User not found"}, status_code=404)

    # Check not already a member
    existing = await db.fetchone(
        "SELECT id FROM tenant_users WHERE tenant_id = %s AND user_id = %s",
        (tenant_id, target_user["id"]),
    )
    if existing:
        return JSONResponse({"error": "User is already a member"}, status_code=409)

    # Get tenant info for WP user creation
    tenant = await db.fetchone(
        """
        SELECT t.slug, ts.wp_admin_password
        FROM tenants t
        JOIN tenant_secrets ts ON ts.tenant_id = t.id
        WHERE t.id = %s
        """,
        (tenant_id,),
    )
    if not tenant:
        return JSONResponse({"error": "Tenant not found"}, status_code=404)

    # Add to tenant_users
    await db.execute(
        "INSERT INTO tenant_users (tenant_id, user_id, role) VALUES (%s, %s, %s)",
        (tenant_id, target_user["id"], role),
    )

    # Create WordPress user
    from articulate_mcp.tenants.crypto import TenantCrypto
    import os
    crypto = TenantCrypto(os.getenv("ENCRYPTION_KEY"))
    wp_admin_pass = crypto.decrypt(tenant["wp_admin_password"])

    wp_user = await create_wp_user_for_tenant(
        wp_url=f"http://{tenant['slug']}-wordpress:80",
        wp_admin_user="admin",
        wp_admin_password=wp_admin_pass,
        articulate_user_email=target_user["email"],
        articulate_user_name=target_user.get("name", ""),
        articulate_role=role,
    )

    if wp_user:
        await db.execute(
            """
            UPDATE tenant_users
            SET wp_user_id = %s, wp_username = %s, wp_role = %s
            WHERE tenant_id = %s AND user_id = %s
            """,
            (wp_user["wp_user_id"], wp_user["wp_username"], wp_user["wp_role"],
             tenant_id, target_user["id"]),
        )

    return JSONResponse({
        "success": True,
        "member": {
            "user_id": target_user["id"],
            "email": target_user["email"],
            "role": role,
            "wp_username": wp_user["wp_username"] if wp_user else None,
            "wp_role": wp_user["wp_role"] if wp_user else None,
        },
    })


@require_auth
async def update_tenant_member_role_endpoint(request):
    """Update a tenant member's role and sync to WordPress."""
    user = request.state.user
    tenant_id = request.path_params["id"]
    member_user_id = int(request.path_params["member_id"])
    data = await request.json()

    new_role = data.get("role")
    if new_role not in ("admin", "editor", "viewer"):
        return JSONResponse({"error": "Invalid role"}, status_code=400)

    # Check requester is owner or admin
    requester_role = await db.fetchone(
        "SELECT role FROM tenant_users WHERE tenant_id = %s AND user_id = %s",
        (tenant_id, user["id"]),
    )
    if not requester_role or requester_role["role"] not in ("owner", "admin"):
        return JSONResponse({"error": "Not authorized"}, status_code=403)

    # Get current member info
    member = await db.fetchone(
        "SELECT * FROM tenant_users WHERE tenant_id = %s AND user_id = %s",
        (tenant_id, member_user_id),
    )
    if not member:
        return JSONResponse({"error": "Member not found"}, status_code=404)

    if member["role"] == "owner":
        return JSONResponse({"error": "Cannot change owner role"}, status_code=400)

    # Update Articulate role
    await db.execute(
        "UPDATE tenant_users SET role = %s WHERE tenant_id = %s AND user_id = %s",
        (new_role, tenant_id, member_user_id),
    )

    # Sync to WordPress if wp_user_id exists
    wp_synced = False
    if member.get("wp_user_id"):
        tenant = await db.fetchone(
            """
            SELECT t.slug, ts.wp_admin_password
            FROM tenants t
            JOIN tenant_secrets ts ON ts.tenant_id = t.id
            WHERE t.id = %s
            """,
            (tenant_id,),
        )
        if tenant:
            from articulate_mcp.tenants.crypto import TenantCrypto
            import os
            crypto = TenantCrypto(os.getenv("ENCRYPTION_KEY"))
            wp_admin_pass = crypto.decrypt(tenant["wp_admin_password"])

            wp_synced = await update_wp_user_role_for_tenant(
                wp_url=f"http://{tenant['slug']}-wordpress:80",
                wp_admin_user="admin",
                wp_admin_password=wp_admin_pass,
                wp_user_id=member["wp_user_id"],
                new_articulate_role=new_role,
            )

            if wp_synced:
                from articulate_mcp.tenants.wp_user_sync import ROLE_MAP
                new_wp_role = ROLE_MAP.get(new_role, "subscriber")
                await db.execute(
                    "UPDATE tenant_users SET wp_role = %s WHERE tenant_id = %s AND user_id = %s",
                    (new_wp_role, tenant_id, member_user_id),
                )

    return JSONResponse({
        "success": True,
        "role": new_role,
        "wp_synced": wp_synced,
    })
```

**Step 2: Wire routes into server.py**

Add imports and routes for the new tenant member endpoints:

```python
from articulate_mcp.routes.tenant_members import (
    add_tenant_member_endpoint,
    update_tenant_member_role_endpoint,
)

# In routes list:
Route("/tenants/{id}/members", add_tenant_member_endpoint, methods=["POST"]),
Route("/tenants/{id}/members/{member_id}", update_tenant_member_role_endpoint, methods=["PUT"]),
```

**Step 3: Commit**

```bash
git add mcp-server/src/articulate_mcp/routes/tenant_members.py \
       mcp-server/src/articulate_mcp/server.py
git commit -m "feat: add tenant member management with WordPress role sync"
```

---

### Task 14: Add UI for Tenant Member Management

**Files:**
- Create: `web/src/app/api/tenants/[id]/members/route.ts`
- Modify: `web/src/app/sites/page.tsx`

**Step 1: Create the Next.js API routes**

Create `web/src/app/api/tenants/[id]/members/route.ts`:

```typescript
import { NextRequest, NextResponse } from "next/server";
import { getSessionHeaders } from "@/lib/server-auth";

const MCP_URL = process.env.MCP_SERVER_URL || "http://mcp-server:8000";

export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const headers = await getSessionHeaders();
    if (!headers) {
      return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
    }

    const body = await request.json();

    const res = await fetch(`${MCP_URL}/tenants/${params.id}/members`, {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    return NextResponse.json({ error: "Failed to add member" }, { status: 500 });
  }
}
```

**Step 2: Add member management UI to the Sites page**

In `web/src/app/sites/page.tsx`, add a "Team" section to `TenantCard` that shows:
- List of current members with their Articulate role and WordPress role
- "Add Member" button (for owners/admins) with email + role inputs
- Role change dropdown for each member
- The `WP: role` badge next to each member

This follows the same pattern as the organization members page but simplified for tenants.

**Step 3: Commit**

```bash
git add web/src/app/api/tenants/\[id\]/members/route.ts \
       web/src/app/sites/page.tsx
git commit -m "feat: add tenant member management UI with role display"
```

---

## Phase 4: TODO List (Future)

> These are tracked for future implementation but not part of the current plan.

- [ ] **Custom Articulate capabilities** - Register custom WordPress capabilities (`articulate_manage_seo`, `articulate_use_ai`, `articulate_view_analytics`) via a mu-plugin shipped with tenant provisioning
- [ ] **Capability-based feature flags** - Gate premium features using a combination of Articulate subscription tier + WordPress capabilities
- [ ] **Custom role builder UI** - Allow organization owners to define custom WordPress roles with specific capability sets, deployed via REST API to tenant WordPress instances
- [ ] **Audit trail correlation** - Correlate Articulate audit logs with WordPress audit logs using per-user WordPress accounts (matching by `wp_user_id` in `tenant_users`)
- [ ] **Fine-grained post-level permissions** - Check `edit_post` meta capability (ownership-based) in addition to `edit_posts` primitive capability
- [ ] **Role synchronization for organizations** - Sync organization roles to WordPress roles across all organization-owned tenants (when an org member's role changes, update their WP role on all org tenants)
- [ ] **Capabilities caching in Redis** - Store fetched capabilities in Redis with 5-min TTL keyed by `caps:{connection_id}:{user_id}` for faster pre-flight checks
- [ ] **Capability diff on connection switch** - When switching active connections, show a toast notification summarizing the user's capabilities on the new connection

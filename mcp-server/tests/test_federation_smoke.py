"""Federation smoke tests — import FastMCP object, verify tool registration.

These tests do NOT require a live DB or Redis.  They exercise:
  - tool count (≥100)
  - __health tool presence
  - representative tool names from each major module
  - __health tool return structure (mocked infra)
  - consolidated transport helper (bare import, no uvicorn)
"""

from __future__ import annotations

import asyncio
import datetime
import importlib
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def mcp_server():
    """Import the FastMCP instance (no DB needed for list_tools)."""
    import articulate_mcp.server as srv
    return srv.mcp


@pytest.fixture(scope="module")
def tool_names(mcp_server):
    """Synchronously list all registered tool names."""
    return [t.name for t in asyncio.run(mcp_server.list_tools())]


# ---------------------------------------------------------------------------
# Slice 1 — consolidate: tool registration baseline
# ---------------------------------------------------------------------------

class TestToolRegistration:
    def test_tool_count_at_least_100(self, tool_names):
        assert len(tool_names) >= 100, f"Expected ≥100 tools, got {len(tool_names)}"

    def test_posts_tools_present(self, tool_names):
        assert any("post" in n.lower() for n in tool_names), "No post tools found"

    def test_pages_tools_present(self, tool_names):
        assert any("page" in n.lower() for n in tool_names), "No page tools found"

    def test_media_tools_present(self, tool_names):
        assert any("media" in n.lower() or "image" in n.lower() for n in tool_names)

    def test_tenant_tools_present(self, tool_names):
        assert any("tenant" in n.lower() for n in tool_names), "No tenant tools found"

    def test_learnpress_tools_present(self, tool_names):
        assert any("learn" in n.lower() or "course" in n.lower() for n in tool_names)

    def test_product_tools_present(self, tool_names):
        assert any("product" in n.lower() or "woo" in n.lower() for n in tool_names)


# ---------------------------------------------------------------------------
# Slice 2 — harden: __health tool
# ---------------------------------------------------------------------------

class TestHealthTool:
    def test_health_tool_registered(self, tool_names):
        assert "__health" in tool_names, f"__health not in tools: {tool_names[:10]}"

    @pytest.mark.asyncio
    async def test_health_returns_valid_structure(self, mcp_server):
        """Call __health directly; mock db/cache so no infra needed."""
        # Patch out the db/cache probes inside __health_tool
        mock_db = MagicMock()
        mock_db._pool = True  # signals "connected"
        mock_cache = MagicMock()
        mock_cache.client = None  # signals "degraded"

        with patch.dict("sys.modules", {
            "articulate_mcp.database": MagicMock(db=mock_db),
            "articulate_mcp.cache": MagicMock(cache=mock_cache),
        }):
            # Find and call the __health tool handler directly
            tools = await mcp_server.list_tools()
            health_tool = next((t for t in tools if t.name == "__health"), None)
            assert health_tool is not None

            # Call via the server's internal call_tool mechanism
            result = await mcp_server.call_tool("__health", {})

        # result is a list of TextContent from FastMCP
        import json
        payload = json.loads(result[0].text) if hasattr(result[0], "text") else result
        if isinstance(payload, list):
            payload = payload[0]
        if isinstance(payload, str):
            payload = json.loads(payload)

        assert "status" in payload
        assert payload["server"] == "articulate"
        assert "version" in payload
        assert "checks" in payload
        assert "ts" in payload
        # ts must be parseable as RFC3339
        ts = payload["ts"]
        datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")

    @pytest.mark.asyncio
    async def test_health_status_values(self, mcp_server):
        """status must be one of the three defined values."""
        result = await mcp_server.call_tool("__health", {})
        import json
        payload = json.loads(result[0].text) if hasattr(result[0], "text") else result
        if isinstance(payload, list):
            payload = payload[0]
        if isinstance(payload, str):
            payload = json.loads(payload)
        assert payload["status"] in {"ok", "degraded", "down"}


# ---------------------------------------------------------------------------
# Slice 1 — consolidate: main() transport branch (no uvicorn, no DB)
# ---------------------------------------------------------------------------

class TestTransportConsolidation:
    def test_server_module_imports_cleanly(self):
        """Server module must be importable without DB/Redis."""
        import articulate_mcp.server  # noqa: F401 — just verifying import

    def test_mcp_is_fastmcp_instance(self, mcp_server):
        from mcp.server.fastmcp import FastMCP
        assert isinstance(mcp_server, FastMCP)

    def test_bare_starlette_app_exists(self):
        """bare_starlette_app must be set (used in consolidated HTTP lifespan)."""
        import articulate_mcp.server as srv
        assert hasattr(srv, "bare_starlette_app")

    def test_startup_function_exists(self):
        import articulate_mcp.server as srv
        assert callable(srv.startup)

    def test_main_function_exists(self):
        import articulate_mcp.server as srv
        assert callable(srv.main)

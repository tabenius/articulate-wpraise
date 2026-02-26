"""Tests for WordPress preview tool."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from articulate_mcp.tools.preview import get_preview_html, register


@pytest.fixture
def mock_mcp():
    """Create a mock MCP server instance."""
    mcp = Mock()
    mcp.tool = Mock(return_value=lambda f: f)
    return mcp


@pytest.fixture
def mock_config():
    """Mock configuration with test WordPress URL."""
    mock_cfg = Mock()
    mock_cfg.wp_url = "http://wordpress:80"
    mock_cfg.wp_auth = ("admin", "test_password")
    return mock_cfg


class TestPreviewTool:
    """Test suite for the preview tool."""

    @pytest.mark.asyncio
    async def test_successful_preview_fetch(self, mock_mcp, mock_config):
        """Test successful preview HTML fetching."""
        with patch("articulate_mcp.tools.preview.config", mock_config):
            # Mock HTTP response
            mock_response = Mock()
            mock_response.json.return_value = {
                "success": True,
                "html": "<!DOCTYPE html><html><body>Test</body></html>",
                "post_id": 1,
                "theme": "twentytwentyfour",
                "post_type": "post",
                "post_status": "publish"
            }
            mock_response.raise_for_status = Mock()

            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                    return_value=mock_response
                )

                result = await get_preview_html(post_id=1)

                assert result["success"] is True
                assert "html" in result
                assert result["post_id"] == 1
                assert result["theme"] == "twentytwentyfour"
                assert "<!DOCTYPE html>" in result["html"]

    @pytest.mark.asyncio
    async def test_preview_with_missing_auth(self, mock_mcp):
        """Test preview fetch when authentication is not configured."""
        mock_cfg = Mock()
        mock_cfg.wp_url = "http://wordpress:80"
        mock_cfg.wp_auth = None  # No authentication

        with patch("articulate_mcp.tools.preview.config", mock_cfg):
            result = await get_preview_html(post_id=1)

            assert "error" in result
            assert "authentication not configured" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_preview_not_found(self, mock_mcp, mock_config):
        """Test preview fetch for non-existent post."""
        with patch("articulate_mcp.tools.preview.config", mock_config):
            # Mock 404 response
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.text = "Not Found"
            mock_response.json.return_value = {
                "code": "not_found",
                "message": "Post not found"
            }

            error = httpx.HTTPStatusError(
                "404", request=Mock(), response=mock_response
            )

            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                    side_effect=error
                )

                result = await get_preview_html(post_id=999)

                assert "error" in result
                assert "404" in result["error"]

    @pytest.mark.asyncio
    async def test_preview_unauthorized(self, mock_mcp, mock_config):
        """Test preview fetch with invalid credentials."""
        with patch("articulate_mcp.tools.preview.config", mock_config):
            # Mock 401 response
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            mock_response.json.return_value = {
                "code": "rest_forbidden",
                "message": "Sorry, you are not allowed to do that."
            }

            error = httpx.HTTPStatusError(
                "401", request=Mock(), response=mock_response
            )

            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                    side_effect=error
                )

                result = await get_preview_html(post_id=1)

                assert "error" in result
                assert "401" in result["error"]
                assert "not allowed" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_preview_server_error(self, mock_mcp, mock_config):
        """Test preview fetch with server error."""
        with patch("articulate_mcp.tools.preview.config", mock_config):
            # Mock 500 response
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_response.json.side_effect = Exception("Invalid JSON")

            error = httpx.HTTPStatusError(
                "500", request=Mock(), response=mock_response
            )

            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                    side_effect=error
                )

                result = await get_preview_html(post_id=1)

                assert "error" in result
                assert "500" in result["error"]

    @pytest.mark.asyncio
    async def test_preview_timeout(self, mock_mcp, mock_config):
        """Test preview fetch with timeout."""
        with patch("articulate_mcp.tools.preview.config", mock_config):
            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                    side_effect=httpx.TimeoutException("Request timeout")
                )

                result = await get_preview_html(post_id=1)

                assert "error" in result
                assert "timeout" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_preview_network_error(self, mock_mcp, mock_config):
        """Test preview fetch with network error."""
        with patch("articulate_mcp.tools.preview.config", mock_config):
            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                    side_effect=httpx.ConnectError("Connection failed")
                )

                result = await get_preview_html(post_id=1)

                assert "error" in result
                assert "failed" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_preview_success_false_in_response(self, mock_mcp, mock_config):
        """Test preview fetch when WordPress returns success=false."""
        with patch("articulate_mcp.tools.preview.config", mock_config):
            mock_response = Mock()
            mock_response.json.return_value = {
                "success": False,
                "error": "Preview generation failed"
            }
            mock_response.raise_for_status = Mock()

            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                    return_value=mock_response
                )

                result = await get_preview_html(post_id=1)

                assert "error" in result
                assert "generation failed" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_preview_url_construction(self, mock_mcp, mock_config):
        """Test that preview URL is correctly constructed."""
        with patch("articulate_mcp.tools.preview.config", mock_config):
            mock_response = Mock()
            mock_response.json.return_value = {
                "success": True,
                "html": "<html></html>",
                "post_id": 42
            }
            mock_response.raise_for_status = Mock()

            with patch("httpx.AsyncClient") as mock_client:
                mock_get = AsyncMock(return_value=mock_response)
                mock_client.return_value.__aenter__.return_value.get = mock_get

                await get_preview_html(post_id=42)

                # Verify the URL was called correctly
                expected_url = "http://wordpress:80/wp-json/articulate/v1/preview/42"
                mock_get.assert_called_once()
                actual_url = mock_get.call_args[0][0]
                assert actual_url == expected_url

    @pytest.mark.asyncio
    async def test_preview_auth_headers(self, mock_mcp, mock_config):
        """Test that authentication is passed correctly."""
        with patch("articulate_mcp.tools.preview.config", mock_config):
            mock_response = Mock()
            mock_response.json.return_value = {
                "success": True,
                "html": "<html></html>"
            }
            mock_response.raise_for_status = Mock()

            with patch("httpx.AsyncClient") as mock_client:
                mock_get = AsyncMock(return_value=mock_response)
                mock_client.return_value.__aenter__.return_value.get = mock_get

                await get_preview_html(post_id=1)

                # Verify auth was passed
                call_kwargs = mock_get.call_args[1]
                assert "auth" in call_kwargs
                assert call_kwargs["auth"] == ("admin", "test_password")

    @pytest.mark.asyncio
    async def test_preview_response_format_validation(self, mock_mcp, mock_config):
        """Test that all expected fields are present in successful response."""
        with patch("articulate_mcp.tools.preview.config", mock_config):
            mock_response = Mock()
            mock_response.json.return_value = {
                "success": True,
                "html": "<!DOCTYPE html><html><head><title>Test</title></head><body><p>Content</p></body></html>",
                "post_id": 1,
                "theme": "twentytwentyfour",
                "post_type": "post",
                "post_status": "publish"
            }
            mock_response.raise_for_status = Mock()

            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                    return_value=mock_response
                )

                result = await get_preview_html(post_id=1)

                # Verify all expected fields
                assert result["success"] is True
                assert "html" in result
                assert result["html"].startswith("<!DOCTYPE html>")
                assert result["post_id"] == 1
                assert result["theme"] == "twentytwentyfour"
                assert result["post_type"] == "post"
                assert result["post_status"] == "publish"


class TestPreviewIntegration:
    """Integration tests for preview functionality."""

    @pytest.mark.asyncio
    async def test_preview_with_different_post_types(self, mock_mcp, mock_config):
        """Test preview for different post types (post, page, custom)."""
        with patch("articulate_mcp.tools.preview.config", mock_config):
            for post_type in ["post", "page", "custom_type"]:
                mock_response = Mock()
                mock_response.json.return_value = {
                    "success": True,
                    "html": f"<html><body>{post_type}</body></html>",
                    "post_id": 1,
                    "post_type": post_type
                }
                mock_response.raise_for_status = Mock()

                with patch("httpx.AsyncClient") as mock_client:
                    mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                        return_value=mock_response
                    )

                    result = await get_preview_html(post_id=1)

                    assert result["success"] is True
                    assert result["post_type"] == post_type

    @pytest.mark.asyncio
    async def test_preview_with_different_statuses(self, mock_mcp, mock_config):
        """Test preview for posts with different statuses."""
        with patch("articulate_mcp.tools.preview.config", mock_config):
            for status in ["draft", "publish", "pending", "private"]:
                mock_response = Mock()
                mock_response.json.return_value = {
                    "success": True,
                    "html": f"<html><body>{status}</body></html>",
                    "post_id": 1,
                    "post_status": status
                }
                mock_response.raise_for_status = Mock()

                with patch("httpx.AsyncClient") as mock_client:
                    mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                        return_value=mock_response
                    )

                    result = await get_preview_html(post_id=1)

                    assert result["success"] is True
                    assert result["post_status"] == status

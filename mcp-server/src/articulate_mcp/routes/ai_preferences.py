"""AI Preferences API endpoints."""

from __future__ import annotations

import logging
from starlette.responses import JSONResponse

from articulate_mcp.ai_preferences import AIPreferencesManager
from articulate_mcp.decorators import require_auth
from articulate_mcp.json_utils import sanitize_for_json

logger = logging.getLogger(__name__)


@require_auth
async def get_ai_preferences_endpoint(request):
    """Get user's AI preferences."""
    try:
        user = request.state.user
        preferences = await AIPreferencesManager.get_preferences(user["id"])
        return JSONResponse(sanitize_for_json(preferences))
    except Exception as e:
        logger.error("Get AI preferences error: %s", e)
        return JSONResponse({"error": "Failed to get preferences"}, status_code=500)


@require_auth
async def update_ai_preferences_endpoint(request):
    """Update user's AI preferences."""
    try:
        user = request.state.user
        data = await request.json()

        preferences = await AIPreferencesManager.update_preferences(user["id"], data)
        return JSONResponse(sanitize_for_json(preferences))
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Update AI preferences error: %s", e)
        return JSONResponse({"error": "Failed to update preferences"}, status_code=500)

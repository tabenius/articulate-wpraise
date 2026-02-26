"""AI-powered image alt text generator using Claude's vision capabilities."""

from __future__ import annotations

import logging
import os
from typing import Any

from anthropic import Anthropic
from starlette.responses import JSONResponse

from articulate_mcp.ai_preferences import AIPreferencesManager
from articulate_mcp.decorators import require_auth

logger = logging.getLogger(__name__)

# Initialize Anthropic client
anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Model mapping
MODEL_MAP = {
    "sonnet": "claude-sonnet-4-20250514",
    "opus": "claude-opus-4-20250514",
    "haiku": "claude-haiku-4-20250514",
}


@require_auth
async def generate_alt_text_endpoint(request):
    """Generate alt text for an image using Claude's vision capabilities.

    Expected request body:
    {
        "image_url": "https://example.com/image.jpg",
        "context": "Optional context about the image",
        "style": "descriptive" | "concise" | "seo-focused" (optional, from preferences)
    }

    Returns:
    {
        "alt_text": "Generated alt text",
        "suggestions": ["Alternative 1", "Alternative 2", "Alternative 3"]
    }
    """
    try:
        user = request.state.user
        data = await request.json()

        image_url = data.get("image_url")
        context = data.get("context", "")

        if not image_url:
            return JSONResponse(
                {"error": "image_url is required"},
                status_code=400
            )

        # Get user's AI preferences
        preferences = await AIPreferencesManager.get_preferences(user["id"])

        # Use style from request or fall back to user preferences
        style = data.get("style", preferences.get("alt_text_style", "descriptive"))

        # Get the appropriate model for image analysis
        model_name = preferences["model_config"].get("image_analysis", "sonnet")
        model_id = MODEL_MAP.get(model_name, MODEL_MAP["sonnet"])

        # Build style-specific instructions
        style_instructions = {
            "descriptive": "Generate descriptive alt text that paints a clear picture for screen readers. Include relevant details about what's in the image, the setting, colors, and important visual elements. Keep it natural and flowing.",
            "concise": "Generate concise, to-the-point alt text that captures the essential information. Be brief but informative, focusing on the most important elements.",
            "seo-focused": "Generate SEO-optimized alt text that naturally incorporates relevant keywords while remaining accurate and helpful. Balance discoverability with accessibility."
        }

        style_instruction = style_instructions.get(style, style_instructions["descriptive"])

        # Build the prompt
        user_prompt = f"""{style_instruction}

{f'Context: {context}' if context else 'No additional context provided.'}

Generate 3 different alt text options for this image. Each should be accurate, accessible, and appropriate for the specified style.

Return your response as a JSON object with this exact structure:
{{
    "primary": "The best alt text option",
    "alternatives": ["Alternative option 1", "Alternative option 2"]
}}

Do not include any other text or explanation, just the JSON object."""

        # Call Claude API with vision
        response = anthropic_client.messages.create(
            model=model_id,
            max_tokens=500,
            temperature=0.7,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "url",
                                "url": image_url,
                            },
                        },
                        {
                            "type": "text",
                            "text": user_prompt
                        }
                    ],
                }
            ]
        )

        # Extract response
        import json
        response_text = response.content[0].text.strip()

        try:
            result = json.loads(response_text)
            alt_text = result.get("primary", "")
            alternatives = result.get("alternatives", [])
        except (json.JSONDecodeError, KeyError):
            # Fallback: use the full response as alt text
            alt_text = response_text
            alternatives = []

        # Track usage
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens

        # Rough cost estimation (prices per 1M tokens)
        cost_per_input = {
            "haiku": 0.80,
            "sonnet": 3.00,
            "opus": 15.00,
        }
        cost_per_output = {
            "haiku": 4.00,
            "sonnet": 15.00,
            "opus": 75.00,
        }

        cost_usd = (
            (input_tokens / 1_000_000) * cost_per_input.get(model_name, 3.00) +
            (output_tokens / 1_000_000) * cost_per_output.get(model_name, 15.00)
        )

        # Track usage in database
        await AIPreferencesManager.track_usage(
            user_id=user["id"],
            organization_id=None,
            feature="alt_text_generation",
            model=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            request_data={"image_url": image_url, "style": style},
            response_data={"alt_text": alt_text},
        )

        return JSONResponse({
            "alt_text": alt_text,
            "suggestions": [alt_text] + alternatives,
        })

    except Exception as e:
        logger.error("Alt text generation error: %s", e, exc_info=True)
        return JSONResponse(
            {"error": "Failed to generate alt text"},
            status_code=500
        )

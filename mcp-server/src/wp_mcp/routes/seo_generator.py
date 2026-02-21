"""AI-powered SEO content generator."""

from __future__ import annotations

import logging
import os
from typing import Any

from anthropic import Anthropic
from starlette.responses import JSONResponse

from wp_mcp.ai_preferences import AIPreferencesManager
from wp_mcp.decorators import require_auth

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
async def generate_seo_endpoint(request):
    """Generate SEO metadata using Claude AI.

    Expected request body:
    {
        "content_title": "Post title",
        "content_excerpt": "Post excerpt or first paragraph",
        "content_body": "Full post content (optional)",
        "focus_keyword": "Target keyword (optional)",
        "field": "seo_title" | "meta_description" | "focus_keyword" | "og_title" | "og_description"
    }

    Returns:
    {
        "suggestions": ["Option 1", "Option 2", "Option 3"],
        "field": "seo_title"
    }
    """
    try:
        user = request.state.user
        data = await request.json()

        content_title = data.get("content_title", "")
        content_excerpt = data.get("content_excerpt", "")
        content_body = data.get("content_body", "")
        focus_keyword = data.get("focus_keyword", "")
        field = data.get("field", "seo_title")

        if not content_title and not content_excerpt:
            return JSONResponse(
                {"error": "Either content_title or content_excerpt is required"},
                status_code=400
            )

        # Get user's AI preferences
        preferences = await AIPreferencesManager.get_preferences(user["id"])

        # Get the appropriate model for SEO optimization
        model_name = preferences["model_config"].get("seo_optimization", "haiku")
        model_id = MODEL_MAP.get(model_name, MODEL_MAP["haiku"])

        # Build system prompt with user preferences
        system_prompt_additions = await AIPreferencesManager.get_system_prompt_additions(user["id"])

        # Generate field-specific prompts
        prompts = {
            "seo_title": f"""Generate 3 SEO-optimized title options for this content.

Requirements:
- 50-60 characters (ideal for search results)
- Include the focus keyword naturally if provided
- Compelling and click-worthy
- Accurately represent the content
{f'- Focus keyword: {focus_keyword}' if focus_keyword else ''}

{system_prompt_additions}

Content title: {content_title}
Content excerpt: {content_excerpt[:500]}

Return ONLY a JSON array of 3 title strings, nothing else.
Example: ["Title Option 1", "Title Option 2", "Title Option 3"]""",

            "meta_description": f"""Generate 3 meta description options for this content.

Requirements:
- 150-160 characters (ideal for search results)
- Include the focus keyword naturally if provided
- Compelling call-to-action or value proposition
- Accurately summarize the content
{f'- Focus keyword: {focus_keyword}' if focus_keyword else ''}

{system_prompt_additions}

Content title: {content_title}
Content excerpt: {content_excerpt[:500]}

Return ONLY a JSON array of 3 description strings, nothing else.
Example: ["Description 1", "Description 2", "Description 3"]""",

            "focus_keyword": f"""Suggest 3 primary keyword options for this content.

Requirements:
- Single keyword or short phrase (2-4 words max)
- High relevance to the content
- Realistic search intent
- Consider SEO competition

{system_prompt_additions}

Content title: {content_title}
Content excerpt: {content_excerpt[:500]}

Return ONLY a JSON array of 3 keyword strings, nothing else.
Example: ["keyword one", "keyword two", "keyword three"]""",

            "og_title": f"""Generate 3 Open Graph title options for social media sharing.

Requirements:
- 60-90 characters (ideal for Facebook/LinkedIn)
- More engaging and conversational than SEO title
- Encourage clicks from social feeds
- Can use emojis if user preferences allow
{f'- Focus keyword: {focus_keyword}' if focus_keyword else ''}

{system_prompt_additions}

Content title: {content_title}
Content excerpt: {content_excerpt[:500]}

Return ONLY a JSON array of 3 title strings, nothing else.
Example: ["Social Title 1", "Social Title 2", "Social Title 3"]""",

            "og_description": f"""Generate 3 Open Graph description options for social media sharing.

Requirements:
- 150-200 characters
- Engaging and conversational
- Encourage clicks from social feeds
- Can use emojis if user preferences allow
{f'- Focus keyword: {focus_keyword}' if focus_keyword else ''}

{system_prompt_additions}

Content title: {content_title}
Content excerpt: {content_excerpt[:500]}

Return ONLY a JSON array of 3 description strings, nothing else.
Example: ["Description 1", "Description 2", "Description 3"]""",
        }

        user_prompt = prompts.get(field)
        if not user_prompt:
            return JSONResponse(
                {"error": f"Invalid field: {field}"},
                status_code=400
            )

        # Call Claude API
        response = anthropic_client.messages.create(
            model=model_id,
            max_tokens=500,
            temperature=0.7,
            messages=[
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
        )

        # Extract suggestions from response
        import json
        suggestions_text = response.content[0].text.strip()

        # Try to parse as JSON
        try:
            suggestions = json.loads(suggestions_text)
            if not isinstance(suggestions, list) or len(suggestions) == 0:
                raise ValueError("Response is not a valid array")
        except (json.JSONDecodeError, ValueError):
            # Fallback: treat as plain text and split by newlines
            suggestions = [s.strip() for s in suggestions_text.split("\n") if s.strip()][:3]

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
            (input_tokens / 1_000_000) * cost_per_input.get(model_name, 0.80) +
            (output_tokens / 1_000_000) * cost_per_output.get(model_name, 4.00)
        )

        # Track usage in database
        await AIPreferencesManager.track_usage(
            user_id=user["id"],
            organization_id=None,
            feature="seo_generation",
            model=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            request_data={"field": field, "title": content_title},
            response_data={"suggestions": suggestions},
        )

        return JSONResponse({
            "suggestions": suggestions[:3],  # Return max 3 suggestions
            "field": field,
        })

    except Exception as e:
        logger.error("SEO generation error: %s", e, exc_info=True)
        return JSONResponse(
            {"error": "Failed to generate SEO content"},
            status_code=500
        )

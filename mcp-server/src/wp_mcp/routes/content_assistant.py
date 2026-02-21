"""AI-powered content assistant for writing improvement and suggestions."""

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
async def analyze_content_endpoint(request):
    """Analyze content and provide suggestions for improvement.

    Expected request body:
    {
        "content": "The content to analyze",
        "analysis_types": ["tone", "readability", "grammar", "seo", "engagement"]
    }

    Returns:
    {
        "analyses": {
            "tone": {...},
            "readability": {...},
            etc.
        }
    }
    """
    try:
        user = request.state.user
        data = await request.json()

        content = data.get("content", "")
        analysis_types = data.get("analysis_types", ["tone", "readability", "grammar"])

        if not content:
            return JSONResponse(
                {"error": "content is required"},
                status_code=400
            )

        # Get user's AI preferences
        preferences = await AIPreferencesManager.get_preferences(user["id"])
        system_prompt_additions = await AIPreferencesManager.get_system_prompt_additions(user["id"])

        # Get the appropriate model for content analysis
        model_name = preferences["model_config"].get("content_analysis", "sonnet")
        model_id = MODEL_MAP.get(model_name, MODEL_MAP["sonnet"])

        # Build analysis prompts
        analyses = {}

        if "tone" in analysis_types:
            tone_result = await _analyze_tone(content, model_id, preferences)
            analyses["tone"] = tone_result

        if "readability" in analysis_types:
            readability_result = await _analyze_readability(content, model_id)
            analyses["readability"] = readability_result

        if "grammar" in analysis_types:
            grammar_result = await _check_grammar(content, model_id)
            analyses["grammar"] = grammar_result

        if "seo" in analysis_types:
            seo_result = await _analyze_seo(content, model_id)
            analyses["seo"] = seo_result

        if "engagement" in analysis_types:
            engagement_result = await _analyze_engagement(content, model_id)
            analyses["engagement"] = engagement_result

        return JSONResponse({"analyses": analyses})

    except Exception as e:
        logger.error("Content analysis error: %s", e, exc_info=True)
        return JSONResponse(
            {"error": "Failed to analyze content"},
            status_code=500
        )


@require_auth
async def improve_content_endpoint(request):
    """Improve content based on specific criteria.

    Expected request body:
    {
        "content": "The content to improve",
        "improvement_type": "clarity" | "engagement" | "conciseness" | "professionalism"
    }

    Returns:
    {
        "improved_content": "The improved version",
        "changes": "Summary of what was changed"
    }
    """
    try:
        user = request.state.user
        data = await request.json()

        content = data.get("content", "")
        improvement_type = data.get("improvement_type", "clarity")

        if not content:
            return JSONResponse(
                {"error": "content is required"},
                status_code=400
            )

        # Get user's AI preferences
        preferences = await AIPreferencesManager.get_preferences(user["id"])
        system_prompt_additions = await AIPreferencesManager.get_system_prompt_additions(user["id"])

        # Get the appropriate model
        model_name = preferences["model_config"].get("content_generation", "sonnet")
        model_id = MODEL_MAP.get(model_name, MODEL_MAP["sonnet"])

        # Build improvement prompts
        improvement_prompts = {
            "clarity": "Improve this content for clarity. Make it easier to understand, remove ambiguity, and ensure the main points are crystal clear. Keep the same meaning and tone.",
            "engagement": "Improve this content to be more engaging and compelling. Make it more interesting to read while maintaining accuracy and professionalism.",
            "conciseness": "Make this content more concise without losing important information. Remove redundancy and unnecessary words while keeping the core message.",
            "professionalism": "Improve the professional tone of this content. Make it more polished and suitable for a professional audience.",
            "seo": "Improve this content for SEO. Naturally incorporate relevant keywords, improve structure for readability, and enhance discoverability while maintaining quality."
        }

        improvement_instruction = improvement_prompts.get(
            improvement_type,
            improvement_prompts["clarity"]
        )

        user_prompt = f"""{improvement_instruction}

User preferences:
{system_prompt_additions}

Original content:
{content}

Provide your response in this JSON format:
{{
    "improved_content": "The improved version of the content",
    "changes_summary": "Brief summary of what you changed and why"
}}"""

        # Call Claude API
        response = anthropic_client.messages.create(
            model=model_id,
            max_tokens=2000,
            temperature=0.7,
            messages=[
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
        )

        # Extract response
        import json
        response_text = response.content[0].text.strip()

        try:
            result = json.loads(response_text)
            improved_content = result.get("improved_content", content)
            changes = result.get("changes_summary", "Content improved")
        except (json.JSONDecodeError, KeyError):
            # Fallback
            improved_content = response_text
            changes = "Content improved"

        # Track usage
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens

        cost_per_input = {"haiku": 0.80, "sonnet": 3.00, "opus": 15.00}
        cost_per_output = {"haiku": 4.00, "sonnet": 15.00, "opus": 75.00}

        cost_usd = (
            (input_tokens / 1_000_000) * cost_per_input.get(model_name, 3.00) +
            (output_tokens / 1_000_000) * cost_per_output.get(model_name, 15.00)
        )

        await AIPreferencesManager.track_usage(
            user_id=user["id"],
            organization_id=None,
            feature="content_improvement",
            model=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            request_data={"improvement_type": improvement_type},
            response_data={"improved": True},
        )

        return JSONResponse({
            "improved_content": improved_content,
            "changes": changes,
        })

    except Exception as e:
        logger.error("Content improvement error: %s", e, exc_info=True)
        return JSONResponse(
            {"error": "Failed to improve content"},
            status_code=500
        )


async def _analyze_tone(content: str, model_id: str, preferences: dict) -> dict:
    """Analyze the tone of the content."""
    prompt = f"""Analyze the tone of this content and provide feedback.

Target tone: {preferences.get('tone', 'professional')}
Target audience: {preferences.get('audience', 'general')}

Content:
{content}

Provide a JSON response with:
{{
    "current_tone": "description of current tone",
    "matches_target": true/false,
    "suggestions": ["suggestion 1", "suggestion 2"]
}}"""

    response = anthropic_client.messages.create(
        model=model_id,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )

    import json
    try:
        return json.loads(response.content[0].text.strip())
    except:
        return {"current_tone": "Unable to analyze", "matches_target": None, "suggestions": []}


async def _analyze_readability(content: str, model_id: str) -> dict:
    """Analyze readability of the content."""
    prompt = f"""Analyze the readability of this content.

Content:
{content}

Provide a JSON response with:
{{
    "grade_level": "estimated reading grade level",
    "score": 1-10 (10 being most readable),
    "suggestions": ["suggestion 1", "suggestion 2"]
}}"""

    response = anthropic_client.messages.create(
        model=model_id,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )

    import json
    try:
        return json.loads(response.content[0].text.strip())
    except:
        return {"grade_level": "Unknown", "score": 5, "suggestions": []}


async def _check_grammar(content: str, model_id: str) -> dict:
    """Check grammar and spelling."""
    prompt = f"""Check this content for grammar and spelling errors.

Content:
{content}

Provide a JSON response with:
{{
    "errors_found": number,
    "issues": [
        {{"text": "problematic text", "suggestion": "correction", "type": "grammar/spelling"}}
    ]
}}"""

    response = anthropic_client.messages.create(
        model=model_id,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    import json
    try:
        return json.loads(response.content[0].text.strip())
    except:
        return {"errors_found": 0, "issues": []}


async def _analyze_seo(content: str, model_id: str) -> dict:
    """Analyze SEO aspects of the content."""
    prompt = f"""Analyze the SEO quality of this content.

Content:
{content}

Provide a JSON response with:
{{
    "score": 1-10,
    "keywords": ["identified", "keywords"],
    "suggestions": ["suggestion 1", "suggestion 2"]
}}"""

    response = anthropic_client.messages.create(
        model=model_id,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )

    import json
    try:
        return json.loads(response.content[0].text.strip())
    except:
        return {"score": 5, "keywords": [], "suggestions": []}


async def _analyze_engagement(content: str, model_id: str) -> dict:
    """Analyze engagement potential of the content."""
    prompt = f"""Analyze how engaging this content is.

Content:
{content}

Provide a JSON response with:
{{
    "score": 1-10,
    "strengths": ["strength 1", "strength 2"],
    "improvements": ["improvement 1", "improvement 2"]
}}"""

    response = anthropic_client.messages.create(
        model=model_id,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )

    import json
    try:
        return json.loads(response.content[0].text.strip())
    except:
        return {"score": 5, "strengths": [], "improvements": []}

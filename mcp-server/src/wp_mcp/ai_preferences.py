"""AI Preferences Manager for user-configurable AI experience."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from wp_mcp.database import db

logger = logging.getLogger(__name__)

# Default AI preferences
DEFAULT_PREFERENCES = {
    "tone": "professional",
    "audience": "general",
    "writing_level": "moderate",
    "content_length": "medium",
    "auto_generate_seo": False,
    "seo_style": "balanced",
    "target_keyword_density": 1.5,
    "primary_language": "en",
    "translation_languages": [],
    "brand_voice": None,
    "company_values": [],
    "avoid_words": [],
    "preferred_terms": {},
    "auto_generate_alt_text": True,
    "alt_text_style": "descriptive",
    "suggestion_frequency": "balanced",
    "confirm_before_apply": True,
    "dismissed_suggestions": [],
    "default_model": "sonnet",
    "model_config": {
        "chat": "sonnet",
        "content_generation": "sonnet",
        "seo_optimization": "haiku",
        "content_analysis": "sonnet",
        "image_analysis": "sonnet",
    },
    "use_emojis": False,
    "include_sources": False,
}


class AIPreferencesManager:
    """Manager for AI preferences and settings."""

    @staticmethod
    async def get_preferences(user_id: int) -> dict[str, Any]:
        """Get AI preferences for a user.

        Args:
            user_id: User ID

        Returns:
            Dictionary of AI preferences (defaults if not set)
        """
        if not await db.connect():
            raise RuntimeError("Database connection failed")

        async with db.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT
                        tone, audience, writing_level, content_length,
                        auto_generate_seo, seo_style, target_keyword_density,
                        primary_language, translation_languages,
                        brand_voice, company_values, avoid_words, preferred_terms,
                        auto_generate_alt_text, alt_text_style,
                        suggestion_frequency, confirm_before_apply, dismissed_suggestions,
                        default_model, model_config,
                        use_emojis, include_sources
                    FROM wp_user_ai_preferences
                    WHERE user_id = %s
                    """,
                    (user_id,),
                )
                row = await cursor.fetchone()

                if not row:
                    # Return defaults if no preferences set
                    return DEFAULT_PREFERENCES.copy()

                # Parse JSON fields
                translation_languages = json.loads(row[8]) if row[8] else []
                company_values = json.loads(row[10]) if row[10] else []
                avoid_words = json.loads(row[11]) if row[11] else []
                preferred_terms = json.loads(row[12]) if row[12] else {}
                dismissed_suggestions = json.loads(row[17]) if row[17] else []
                model_config = json.loads(row[19]) if row[19] else DEFAULT_PREFERENCES["model_config"]

                return {
                    "tone": row[0],
                    "audience": row[1],
                    "writing_level": row[2],
                    "content_length": row[3],
                    "auto_generate_seo": bool(row[4]),
                    "seo_style": row[5],
                    "target_keyword_density": float(row[6]),
                    "primary_language": row[7],
                    "translation_languages": translation_languages,
                    "brand_voice": row[9],
                    "company_values": company_values,
                    "avoid_words": avoid_words,
                    "preferred_terms": preferred_terms,
                    "auto_generate_alt_text": bool(row[13]),
                    "alt_text_style": row[14],
                    "suggestion_frequency": row[15],
                    "confirm_before_apply": bool(row[16]),
                    "dismissed_suggestions": dismissed_suggestions,
                    "default_model": row[18],
                    "model_config": model_config,
                    "use_emojis": bool(row[20]),
                    "include_sources": bool(row[21]),
                }

    @staticmethod
    async def update_preferences(user_id: int, preferences: dict[str, Any]) -> dict[str, Any]:
        """Update AI preferences for a user.

        Args:
            user_id: User ID
            preferences: Dictionary of preferences to update

        Returns:
            Updated preferences dictionary
        """
        if not await db.connect():
            raise RuntimeError("Database connection failed")

        # Validate tone
        valid_tones = ["professional", "casual", "friendly", "authoritative", "conversational"]
        if "tone" in preferences and preferences["tone"] not in valid_tones:
            raise ValueError(f"Invalid tone. Must be one of: {', '.join(valid_tones)}")

        # Validate audience
        valid_audiences = ["general", "technical", "beginner", "expert", "children"]
        if "audience" in preferences and preferences["audience"] not in valid_audiences:
            raise ValueError(f"Invalid audience. Must be one of: {', '.join(valid_audiences)}")

        # Validate writing level
        valid_levels = ["simple", "moderate", "advanced", "academic"]
        if "writing_level" in preferences and preferences["writing_level"] not in valid_levels:
            raise ValueError(f"Invalid writing level. Must be one of: {', '.join(valid_levels)}")

        # Validate content length
        valid_lengths = ["concise", "medium", "detailed", "comprehensive"]
        if "content_length" in preferences and preferences["content_length"] not in valid_lengths:
            raise ValueError(f"Invalid content length. Must be one of: {', '.join(valid_lengths)}")

        # Validate SEO style
        valid_seo_styles = ["clickbait", "informative", "balanced", "conservative"]
        if "seo_style" in preferences and preferences["seo_style"] not in valid_seo_styles:
            raise ValueError(f"Invalid SEO style. Must be one of: {', '.join(valid_seo_styles)}")

        # Validate alt text style
        valid_alt_styles = ["descriptive", "concise", "seo-focused"]
        if "alt_text_style" in preferences and preferences["alt_text_style"] not in valid_alt_styles:
            raise ValueError(f"Invalid alt text style. Must be one of: {', '.join(valid_alt_styles)}")

        # Validate suggestion frequency
        valid_frequencies = ["aggressive", "balanced", "minimal", "off"]
        if "suggestion_frequency" in preferences and preferences["suggestion_frequency"] not in valid_frequencies:
            raise ValueError(f"Invalid suggestion frequency. Must be one of: {', '.join(valid_frequencies)}")

        # Validate default model
        valid_models = ["sonnet", "opus", "haiku"]
        if "default_model" in preferences and preferences["default_model"] not in valid_models:
            raise ValueError(f"Invalid model. Must be one of: {', '.join(valid_models)}")

        async with db.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Check if preferences exist
                await cursor.execute(
                    "SELECT id FROM wp_user_ai_preferences WHERE user_id = %s",
                    (user_id,),
                )
                exists = await cursor.fetchone()

                # Prepare JSON fields
                json_fields = {}
                if "translation_languages" in preferences:
                    json_fields["translation_languages"] = json.dumps(preferences["translation_languages"])
                if "company_values" in preferences:
                    json_fields["company_values"] = json.dumps(preferences["company_values"])
                if "avoid_words" in preferences:
                    json_fields["avoid_words"] = json.dumps(preferences["avoid_words"])
                if "preferred_terms" in preferences:
                    json_fields["preferred_terms"] = json.dumps(preferences["preferred_terms"])
                if "dismissed_suggestions" in preferences:
                    json_fields["dismissed_suggestions"] = json.dumps(preferences["dismissed_suggestions"])
                if "model_config" in preferences:
                    json_fields["model_config"] = json.dumps(preferences["model_config"])

                # Build update query
                update_fields = []
                values = []

                for key, value in preferences.items():
                    if key in json_fields:
                        update_fields.append(f"{key} = %s")
                        values.append(json_fields[key])
                    elif key in DEFAULT_PREFERENCES:
                        update_fields.append(f"{key} = %s")
                        values.append(value)

                if not update_fields:
                    # No valid fields to update
                    return await AIPreferencesManager.get_preferences(user_id)

                if exists:
                    # Update existing preferences
                    query = f"""
                        UPDATE wp_user_ai_preferences
                        SET {', '.join(update_fields)}
                        WHERE user_id = %s
                    """
                    values.append(user_id)
                    await cursor.execute(query, tuple(values))
                else:
                    # Insert new preferences
                    fields = ["user_id"] + list(preferences.keys())
                    placeholders = ["%s"] * len(fields)
                    query = f"""
                        INSERT INTO wp_user_ai_preferences ({', '.join(fields)})
                        VALUES ({', '.join(placeholders)})
                    """
                    insert_values = [user_id] + [
                        json_fields.get(k, preferences[k]) for k in preferences.keys()
                    ]
                    await cursor.execute(query, tuple(insert_values))

                await conn.commit()

        # Return updated preferences
        return await AIPreferencesManager.get_preferences(user_id)

    @staticmethod
    async def get_system_prompt_additions(user_id: int) -> str:
        """Get additional system prompt instructions based on user preferences.

        Args:
            user_id: User ID

        Returns:
            Additional system prompt text
        """
        preferences = await AIPreferencesManager.get_preferences(user_id)

        additions = []

        # Tone
        tone_map = {
            "professional": "Write in a professional, business-appropriate tone.",
            "casual": "Write in a casual, relaxed tone.",
            "friendly": "Write in a friendly, approachable tone.",
            "authoritative": "Write in an authoritative, expert tone.",
            "conversational": "Write in a conversational, dialogue-like tone.",
        }
        additions.append(tone_map.get(preferences["tone"], ""))

        # Audience
        audience_map = {
            "general": "Write for a general audience with no specialized knowledge.",
            "technical": "Write for a technical audience with domain expertise.",
            "beginner": "Write for beginners who are new to the topic.",
            "expert": "Write for experts with advanced knowledge.",
            "children": "Write for children in simple, easy-to-understand language.",
        }
        additions.append(audience_map.get(preferences["audience"], ""))

        # Writing level
        level_map = {
            "simple": "Use simple language and short sentences.",
            "moderate": "Use moderately complex language and varied sentence structure.",
            "advanced": "Use advanced vocabulary and complex sentence structures.",
            "academic": "Use academic language with formal terminology.",
        }
        additions.append(level_map.get(preferences["writing_level"], ""))

        # Content length
        length_map = {
            "concise": "Be concise and to the point.",
            "medium": "Provide moderate detail and explanation.",
            "detailed": "Provide detailed explanations and examples.",
            "comprehensive": "Provide comprehensive coverage with extensive detail.",
        }
        additions.append(length_map.get(preferences["content_length"], ""))

        # Brand voice
        if preferences.get("brand_voice"):
            additions.append(f"Brand voice guidelines: {preferences['brand_voice']}")

        # Avoid words
        if preferences.get("avoid_words") and len(preferences["avoid_words"]) > 0:
            additions.append(f"Avoid using these words: {', '.join(preferences['avoid_words'])}")

        # Preferred terms
        if preferences.get("preferred_terms") and len(preferences["preferred_terms"]) > 0:
            replacements = [f"'{k}' instead of '{v}'" for k, v in preferences["preferred_terms"].items()]
            additions.append(f"Use {', '.join(replacements)}")

        # Emojis
        if preferences.get("use_emojis"):
            additions.append("Use emojis where appropriate to make content more engaging.")
        else:
            additions.append("Do not use emojis in your responses.")

        return "\n".join(filter(None, additions))

    @staticmethod
    async def track_usage(
        user_id: int,
        organization_id: Optional[int],
        feature: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        request_data: Optional[dict[str, Any]] = None,
        response_data: Optional[dict[str, Any]] = None,
    ) -> None:
        """Track AI usage for analytics and billing.

        Args:
            user_id: User ID
            organization_id: Organization ID (optional)
            feature: Feature name (e.g., 'seo_generation', 'content_improve')
            model: Model used (e.g., 'sonnet', 'opus', 'haiku')
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cost_usd: Estimated cost in USD
            request_data: Optional request data to store
            response_data: Optional response data to store
        """
        if not await db.connect():
            logger.warning("Database connection failed, skipping usage tracking")
            return

        try:
            async with db.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        """
                        INSERT INTO wp_ai_usage
                        (user_id, organization_id, feature, model, input_tokens, output_tokens, cost_usd, request_data, response_data)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            user_id,
                            organization_id,
                            feature,
                            model,
                            input_tokens,
                            output_tokens,
                            cost_usd,
                            json.dumps(request_data) if request_data else None,
                            json.dumps(response_data) if response_data else None,
                        ),
                    )
                    await conn.commit()
        except Exception as e:
            logger.error(f"Failed to track AI usage: {e}")

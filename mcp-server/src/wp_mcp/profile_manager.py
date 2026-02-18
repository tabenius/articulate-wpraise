"""User profile management."""

from __future__ import annotations

import logging
import re
from typing import Optional

from wp_mcp.database import db

logger = logging.getLogger(__name__)


class ProfileManager:
    """Manage user profiles."""

    @staticmethod
    async def get_profile(user_id: int) -> Optional[dict]:
        """Get user profile.

        Args:
            user_id: User ID

        Returns:
            Profile dict with user info
        """
        profile = await db.fetchone(
            """
            SELECT id, email, username, name, avatar, banner, bio, created_at, updated_at
            FROM wp_users_auth
            WHERE id = %s
            """,
            (user_id,),
        )
        return profile

    @staticmethod
    async def update_profile(
        user_id: int,
        username: Optional[str] = None,
        name: Optional[str] = None,
        avatar: Optional[str] = None,
        banner: Optional[str] = None,
        bio: Optional[str] = None,
    ) -> dict:
        """Update user profile.

        Args:
            user_id: User ID
            username: Username (3-50 chars, alphanumeric + underscore/dash)
            name: Display name
            avatar: Avatar URL
            banner: Banner URL
            bio: Bio text (max 500 chars)

        Returns:
            Updated profile dict

        Raises:
            ValueError: If validation fails
        """
        # Validate username if provided
        if username is not None:
            username = username.strip()
            if not username:
                raise ValueError("Username cannot be empty")
            if len(username) < 3 or len(username) > 50:
                raise ValueError("Username must be 3-50 characters")
            if not re.match(r"^[a-zA-Z0-9_-]+$", username):
                raise ValueError(
                    "Username can only contain letters, numbers, underscore, and dash"
                )

            # Check if username is already taken by another user
            existing = await db.fetchone(
                "SELECT id FROM wp_users_auth WHERE username = %s AND id != %s",
                (username, user_id),
            )
            if existing:
                raise ValueError("Username already taken")

        # Validate bio length
        if bio is not None and len(bio) > 500:
            raise ValueError("Bio cannot exceed 500 characters")

        # Build update query dynamically
        updates = []
        params = []

        if username is not None:
            updates.append("username = %s")
            params.append(username)
        if name is not None:
            updates.append("name = %s")
            params.append(name)
        if avatar is not None:
            updates.append("avatar = %s")
            params.append(avatar)
        if banner is not None:
            updates.append("banner = %s")
            params.append(banner)
        if bio is not None:
            updates.append("bio = %s")
            params.append(bio)

        if not updates:
            # Nothing to update, just return current profile
            return await ProfileManager.get_profile(user_id)

        params.append(user_id)
        query = f"UPDATE wp_users_auth SET {', '.join(updates)} WHERE id = %s"

        await db.execute(query, tuple(params))
        logger.info(f"Profile updated for user {user_id}")

        # Return updated profile
        return await ProfileManager.get_profile(user_id)

    @staticmethod
    async def get_profile_by_username(username: str) -> Optional[dict]:
        """Get user profile by username.

        Args:
            username: Username

        Returns:
            Profile dict or None
        """
        profile = await db.fetchone(
            """
            SELECT id, email, username, name, avatar, banner, bio, created_at
            FROM wp_users_auth
            WHERE username = %s
            """,
            (username,),
        )
        return profile

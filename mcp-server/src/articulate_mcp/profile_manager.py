"""User profile management."""

from __future__ import annotations

import logging
import re
from typing import Optional

from articulate_mcp.database import db

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
            SELECT id, email, username, name, avatar, banner, bio, visibility, created_at, updated_at
            FROM articulate_users_auth
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
        visibility: Optional[str] = None,
    ) -> dict:
        """Update user profile.

        Args:
            user_id: User ID
            username: Username (3-50 chars, alphanumeric + underscore/dash)
            name: Display name
            avatar: Avatar URL
            banner: Banner URL
            bio: Bio text (max 500 chars)
            visibility: Profile visibility (public, private)

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
                "SELECT id FROM articulate_users_auth WHERE username = %s AND id != %s",
                (username, user_id),
            )
            if existing:
                raise ValueError("Username already taken")

        # Validate bio length
        if bio is not None and len(bio) > 500:
            raise ValueError("Bio cannot exceed 500 characters")

        # Validate visibility
        if visibility is not None:
            valid_visibility = ["public", "private"]
            if visibility not in valid_visibility:
                raise ValueError(f"Visibility must be one of: {', '.join(valid_visibility)}")

        # Build update query dynamically
        updates: list[str] = []
        params: list[str | int] = []

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
        if visibility is not None:
            updates.append("visibility = %s")
            params.append(visibility)

        if not updates:
            # Nothing to update, just return current profile
            profile = await ProfileManager.get_profile(user_id)
            assert profile is not None, "Profile should exist"
            return profile

        params.append(user_id)
        query = f"UPDATE articulate_users_auth SET {', '.join(updates)} WHERE id = %s"

        await db.execute(query, tuple(params))
        logger.info(f"Profile updated for user {user_id}")

        # Return updated profile
        profile = await ProfileManager.get_profile(user_id)
        assert profile is not None, "Profile should exist after update"
        return profile

    @staticmethod
    async def get_profile_by_username(
        username: str,
        requesting_user_id: Optional[int] = None
    ) -> Optional[dict]:
        """Get user profile by username.

        Args:
            username: Username
            requesting_user_id: ID of user requesting the profile (for visibility check)

        Returns:
            Profile dict or None (if not found or not visible)
        """
        profile = await db.fetchone(
            """
            SELECT id, email, username, name, avatar, banner, bio, visibility, created_at
            FROM articulate_users_auth
            WHERE username = %s
            """,
            (username,),
        )

        if not profile:
            return None

        # Check visibility
        if not await ProfileManager.is_profile_visible(
            profile["id"],
            requesting_user_id
        ):
            return None

        return profile

    @staticmethod
    async def is_profile_visible(
        profile_user_id: int,
        requesting_user_id: Optional[int] = None
    ) -> bool:
        """Check if a profile is visible to the requesting user.

        Args:
            profile_user_id: ID of the profile owner
            requesting_user_id: ID of user requesting access (None for anonymous)

        Returns:
            True if profile is visible, False otherwise
        """
        # Get profile visibility
        result = await db.fetchone(
            "SELECT visibility FROM articulate_users_auth WHERE id = %s",
            (profile_user_id,),
        )

        if not result:
            return False

        visibility = result.get("visibility", "public")

        # Own profile is always visible
        if requesting_user_id == profile_user_id:
            return True

        # Public profiles are visible to everyone
        if visibility == "public":
            return True

        # Private profiles are only visible to the owner
        return False

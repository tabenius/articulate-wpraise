"""Activity feed management."""

from __future__ import annotations

import json
import logging
from typing import Optional

from wp_mcp.database import db

logger = logging.getLogger(__name__)


class ActivityManager:
    """Manage activity feeds."""

    # Activity types
    PROFILE_UPDATED = "profile_updated"
    PROFILE_AVATAR_CHANGED = "profile_avatar_changed"
    ORGANIZATION_CREATED = "organization_created"
    ORGANIZATION_JOINED = "organization_joined"
    ORGANIZATION_LEFT = "organization_left"
    MEMBER_ROLE_CHANGED = "member_role_changed"
    OWNERSHIP_TRANSFERRED = "ownership_transferred"
    INVITE_SENT = "invite_sent"
    INVITE_ACCEPTED = "invite_accepted"

    @staticmethod
    async def log_activity(
        user_id: int,
        activity_type: str,
        organization_id: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> int:
        """Log an activity.

        Args:
            user_id: User who performed the activity
            activity_type: Type of activity
            organization_id: Related organization (optional)
            metadata: Additional activity data (optional)

        Returns:
            Activity ID
        """
        metadata_json = json.dumps(metadata) if metadata else None

        result = await db.execute(
            """
            INSERT INTO wp_activities (user_id, organization_id, activity_type, metadata)
            VALUES (%s, %s, %s, %s)
            """,
            (user_id, organization_id, activity_type, metadata_json),
        )

        activity_id = result
        logger.info(f"Activity logged: {activity_type} by user {user_id}")
        return activity_id

    @staticmethod
    async def get_user_activities(
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """Get activities for a user.

        Args:
            user_id: User ID
            limit: Maximum number of activities to return
            offset: Number of activities to skip

        Returns:
            List of activity dicts with user info
        """
        activities = await db.fetchall(
            """
            SELECT
                a.id,
                a.user_id,
                a.organization_id,
                a.activity_type,
                a.metadata,
                a.created_at,
                u.name as user_name,
                u.username as user_username,
                u.avatar as user_avatar,
                o.name as organization_name,
                o.slug as organization_slug
            FROM wp_activities a
            JOIN wp_users_auth u ON a.user_id = u.id
            LEFT JOIN wp_organizations o ON a.organization_id = o.id
            WHERE a.user_id = %s
            ORDER BY a.created_at DESC
            LIMIT %s OFFSET %s
            """,
            (user_id, limit, offset),
        )

        # Parse JSON metadata
        for activity in activities:
            if activity.get("metadata"):
                activity["metadata"] = json.loads(activity["metadata"])

        return activities

    @staticmethod
    async def get_organization_activities(
        organization_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """Get activities for an organization.

        Args:
            organization_id: Organization ID
            limit: Maximum number of activities to return
            offset: Number of activities to skip

        Returns:
            List of activity dicts with user info
        """
        activities = await db.fetchall(
            """
            SELECT
                a.id,
                a.user_id,
                a.organization_id,
                a.activity_type,
                a.metadata,
                a.created_at,
                u.name as user_name,
                u.username as user_username,
                u.avatar as user_avatar,
                o.name as organization_name,
                o.slug as organization_slug
            FROM wp_activities a
            JOIN wp_users_auth u ON a.user_id = u.id
            LEFT JOIN wp_organizations o ON a.organization_id = o.id
            WHERE a.organization_id = %s
            ORDER BY a.created_at DESC
            LIMIT %s OFFSET %s
            """,
            (organization_id, limit, offset),
        )

        # Parse JSON metadata
        for activity in activities:
            if activity.get("metadata"):
                activity["metadata"] = json.loads(activity["metadata"])

        return activities

    @staticmethod
    async def get_feed(
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """Get activity feed for a user (their activities + their organizations' activities).

        Args:
            user_id: User ID
            limit: Maximum number of activities to return
            offset: Number of activities to skip

        Returns:
            List of activity dicts
        """
        activities = await db.fetchall(
            """
            SELECT
                a.id,
                a.user_id,
                a.organization_id,
                a.activity_type,
                a.metadata,
                a.created_at,
                u.name as user_name,
                u.username as user_username,
                u.avatar as user_avatar,
                o.name as organization_name,
                o.slug as organization_slug
            FROM wp_activities a
            JOIN wp_users_auth u ON a.user_id = u.id
            LEFT JOIN wp_organizations o ON a.organization_id = o.id
            WHERE
                a.user_id = %s
                OR a.organization_id IN (
                    SELECT organization_id
                    FROM wp_organization_members
                    WHERE user_id = %s
                )
            ORDER BY a.created_at DESC
            LIMIT %s OFFSET %s
            """,
            (user_id, user_id, limit, offset),
        )

        # Parse JSON metadata
        for activity in activities:
            if activity.get("metadata"):
                activity["metadata"] = json.loads(activity["metadata"])

        return activities

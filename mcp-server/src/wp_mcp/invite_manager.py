"""Organization invite management."""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from wp_mcp.database import db

logger = logging.getLogger(__name__)


class InviteManager:
    """Manage organization invites."""

    @staticmethod
    async def create_invite(
        org_id: int,
        inviter_id: int,
        invitee_email: str,
        role: str = "member",
        expires_days: int = 7,
    ) -> dict:
        """Create an organization invite.

        Args:
            org_id: Organization ID
            inviter_id: User creating the invite
            invitee_email: Email of user to invite
            role: Role to assign (admin, member, viewer)
            expires_days: Days until invite expires

        Returns:
            Created invite dict

        Raises:
            ValueError: If validation fails or unauthorized
        """
        # Validate email
        if not invitee_email or "@" not in invitee_email:
            raise ValueError("Invalid email address")

        # Validate role
        if role not in ("admin", "member", "viewer"):
            raise ValueError("Invalid role. Must be: admin, member, or viewer")

        # Check if inviter has permission (owner or admin)
        member = await db.fetchone(
            """
            SELECT role FROM wp_organization_members
            WHERE organization_id = %s AND user_id = %s
            """,
            (org_id, inviter_id),
        )
        if not member or member["role"] not in ("owner", "admin"):
            raise ValueError("Unauthorized: Only owners and admins can invite members")

        # Check if user is already a member
        invitee = await db.fetchone(
            "SELECT id FROM wp_users_auth WHERE email = %s", (invitee_email,)
        )
        if invitee:
            existing_member = await db.fetchone(
                """
                SELECT id FROM wp_organization_members
                WHERE organization_id = %s AND user_id = %s
                """,
                (org_id, invitee["id"]),
            )
            if existing_member:
                raise ValueError("User is already a member of this organization")

        # Check if there's already a pending invite
        existing_invite = await db.fetchone(
            """
            SELECT id FROM wp_organization_invites
            WHERE organization_id = %s AND invitee_email = %s AND status = 'pending'
            """,
            (org_id, invitee_email),
        )
        if existing_invite:
            raise ValueError("An invite for this email is already pending")

        # Generate unique token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)

        # Create invite
        invite_id = await db.insert(
            """
            INSERT INTO wp_organization_invites
            (organization_id, inviter_id, invitee_email, invitee_id, role, token, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (org_id, inviter_id, invitee_email, invitee["id"] if invitee else None, role, token, expires_at),
        )

        logger.info(f"Invite created for {invitee_email} to org {org_id} by user {inviter_id}")

        # Log activity
        from wp_mcp.activity_manager import ActivityManager
        org_info = await db.fetchone("SELECT name FROM wp_organizations WHERE id = %s", (org_id,))
        await ActivityManager.log_activity(
            inviter_id,
            ActivityManager.INVITE_SENT,
            org_id,
            {"invitee_email": invitee_email, "role": role, "organization_name": org_info["name"] if org_info else None}
        )

        return await InviteManager.get_invite(invite_id)

    @staticmethod
    async def get_invite(invite_id: int) -> Optional[dict]:
        """Get invite details.

        Args:
            invite_id: Invite ID

        Returns:
            Invite dict with organization and inviter details
        """
        invite = await db.fetchone(
            """
            SELECT i.*, o.name as org_name, o.avatar as org_avatar,
                   u.name as inviter_name, u.email as inviter_email
            FROM wp_organization_invites i
            INNER JOIN wp_organizations o ON o.id = i.organization_id
            INNER JOIN wp_users_auth u ON u.id = i.inviter_id
            WHERE i.id = %s
            """,
            (invite_id,),
        )
        return invite

    @staticmethod
    async def get_invite_by_token(token: str) -> Optional[dict]:
        """Get invite by token.

        Args:
            token: Invite token

        Returns:
            Invite dict or None
        """
        invite = await db.fetchone(
            """
            SELECT i.*, o.name as org_name, o.avatar as org_avatar, o.bio as org_bio,
                   u.name as inviter_name, u.email as inviter_email
            FROM wp_organization_invites i
            INNER JOIN wp_organizations o ON o.id = i.organization_id
            INNER JOIN wp_users_auth u ON u.id = i.inviter_id
            WHERE i.token = %s
            """,
            (token,),
        )
        return invite

    @staticmethod
    async def get_invites_for_organization(org_id: int, user_id: int) -> list[dict]:
        """Get all invites for an organization.

        Args:
            org_id: Organization ID
            user_id: User requesting (must be owner or admin)

        Returns:
            List of invites

        Raises:
            ValueError: If unauthorized
        """
        # Check permission
        member = await db.fetchone(
            """
            SELECT role FROM wp_organization_members
            WHERE organization_id = %s AND user_id = %s
            """,
            (org_id, user_id),
        )
        if not member or member["role"] not in ("owner", "admin"):
            raise ValueError("Unauthorized: Only owners and admins can view invites")

        invites = await db.fetchall(
            """
            SELECT i.*, u.name as inviter_name
            FROM wp_organization_invites i
            INNER JOIN wp_users_auth u ON u.id = i.inviter_id
            WHERE i.organization_id = %s
            ORDER BY i.created_at DESC
            """,
            (org_id,),
        )
        return invites

    @staticmethod
    async def get_invites_for_user(user_email: str) -> list[dict]:
        """Get all pending invites for a user's email.

        Args:
            user_email: User's email address

        Returns:
            List of pending invites
        """
        invites = await db.fetchall(
            """
            SELECT i.*, o.name as org_name, o.avatar as org_avatar, o.bio as org_bio,
                   u.name as inviter_name, u.email as inviter_email
            FROM wp_organization_invites i
            INNER JOIN wp_organizations o ON o.id = i.organization_id
            INNER JOIN wp_users_auth u ON u.id = i.inviter_id
            WHERE i.invitee_email = %s AND i.status = 'pending'
            ORDER BY i.created_at DESC
            """,
            (user_email,),
        )

        # Mark expired invites
        now = datetime.now(timezone.utc)
        for invite in invites:
            # Make expires_at timezone-aware if needed
            expires_at = invite["expires_at"]
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)

            if expires_at < now:
                await InviteManager._mark_expired(invite["id"])
                invite["status"] = "expired"

        return invites

    @staticmethod
    async def accept_invite(token: str, user_id: int) -> dict:
        """Accept an organization invite.

        Args:
            token: Invite token
            user_id: User accepting the invite

        Returns:
            Organization dict

        Raises:
            ValueError: If invite invalid, expired, or unauthorized
        """
        # Get invite
        invite = await InviteManager.get_invite_by_token(token)
        if not invite:
            raise ValueError("Invalid invite token")

        # Check if invite is pending
        if invite["status"] != "pending":
            raise ValueError(f"Invite is {invite['status']}")

        # Check if expired
        # Make both datetimes timezone-aware for comparison
        expires_at = invite["expires_at"]
        if expires_at.tzinfo is None:
            # Database datetime is naive, make it UTC-aware
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at < datetime.now(timezone.utc):
            await InviteManager._mark_expired(invite["id"])
            raise ValueError("Invite has expired")

        # Check if user email matches
        user = await db.fetchone(
            "SELECT email FROM wp_users_auth WHERE id = %s", (user_id,)
        )
        if not user or user["email"] != invite["invitee_email"]:
            raise ValueError("This invite is for a different email address")

        # Check if already a member
        existing_member = await db.fetchone(
            """
            SELECT id FROM wp_organization_members
            WHERE organization_id = %s AND user_id = %s
            """,
            (invite["organization_id"], user_id),
        )
        if existing_member:
            raise ValueError("You are already a member of this organization")

        # Add user as member
        await db.insert(
            """
            INSERT INTO wp_organization_members (organization_id, user_id, role)
            VALUES (%s, %s, %s)
            """,
            (invite["organization_id"], user_id, invite["role"]),
        )

        # Mark invite as accepted
        await db.execute(
            """
            UPDATE wp_organization_invites
            SET status = 'accepted', responded_at = %s, invitee_id = %s
            WHERE id = %s
            """,
            (datetime.now(timezone.utc), user_id, invite["id"]),
        )

        logger.info(f"User {user_id} accepted invite to org {invite['organization_id']}")

        # Log activity
        from wp_mcp.activity_manager import ActivityManager
        await ActivityManager.log_activity(
            user_id,
            ActivityManager.INVITE_ACCEPTED,
            invite["organization_id"],
            {"role": invite["role"], "organization_name": invite["org_name"]}
        )
        # Also log join activity
        await ActivityManager.log_activity(
            user_id,
            ActivityManager.ORGANIZATION_JOINED,
            invite["organization_id"],
            {"organization_name": invite["org_name"], "role": invite["role"]}
        )

        # Return organization details
        from wp_mcp.organization_manager import OrganizationManager
        return await OrganizationManager.get_organization(invite["organization_id"])

    @staticmethod
    async def reject_invite(token: str, user_id: int) -> bool:
        """Reject an organization invite.

        Args:
            token: Invite token
            user_id: User rejecting the invite

        Returns:
            True if rejected

        Raises:
            ValueError: If invite invalid or unauthorized
        """
        # Get invite
        invite = await InviteManager.get_invite_by_token(token)
        if not invite:
            raise ValueError("Invalid invite token")

        # Check if invite is pending
        if invite["status"] != "pending":
            raise ValueError(f"Invite is {invite['status']}")

        # Check if user email matches
        user = await db.fetchone(
            "SELECT email FROM wp_users_auth WHERE id = %s", (user_id,)
        )
        if not user or user["email"] != invite["invitee_email"]:
            raise ValueError("This invite is for a different email address")

        # Mark invite as rejected
        await db.execute(
            """
            UPDATE wp_organization_invites
            SET status = 'rejected', responded_at = %s, invitee_id = %s
            WHERE id = %s
            """,
            (datetime.now(timezone.utc), user_id, invite["id"]),
        )

        logger.info(f"User {user_id} rejected invite to org {invite['organization_id']}")
        return True

    @staticmethod
    async def cancel_invite(invite_id: int, user_id: int) -> bool:
        """Cancel an invite (by organization admin/owner).

        Args:
            invite_id: Invite ID
            user_id: User canceling (must be owner or admin)

        Returns:
            True if canceled

        Raises:
            ValueError: If unauthorized
        """
        # Get invite
        invite = await InviteManager.get_invite(invite_id)
        if not invite:
            raise ValueError("Invite not found")

        # Check permission
        member = await db.fetchone(
            """
            SELECT role FROM wp_organization_members
            WHERE organization_id = %s AND user_id = %s
            """,
            (invite["organization_id"], user_id),
        )
        if not member or member["role"] not in ("owner", "admin"):
            raise ValueError("Unauthorized: Only owners and admins can cancel invites")

        # Delete invite
        await db.execute("DELETE FROM wp_organization_invites WHERE id = %s", (invite_id,))

        logger.info(f"Invite {invite_id} canceled by user {user_id}")
        return True

    @staticmethod
    async def _mark_expired(invite_id: int):
        """Mark an invite as expired."""
        await db.execute(
            "UPDATE wp_organization_invites SET status = 'expired' WHERE id = %s",
            (invite_id,),
        )

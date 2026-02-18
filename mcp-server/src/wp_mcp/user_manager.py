"""User management and authentication."""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt

from wp_mcp.audit import AuditLog
from wp_mcp.database import db

logger = logging.getLogger(__name__)


class UserManager:
    """Manage users and authentication."""

    @staticmethod
    async def register_user(email: str, password: str, name: str = "") -> dict:
        """Register a new user.

        Args:
            email: User email address
            password: Plain text password
            name: User display name

        Returns:
            User dict with id, email, name

        Raises:
            ValueError: If email already exists or validation fails
        """
        # Validate email
        if not email or "@" not in email:
            raise ValueError("Invalid email address")

        # Validate password
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")

        # Check if email already exists
        existing = await db.fetchone(
            "SELECT id FROM wp_users_auth WHERE email = %s", (email,)
        )
        if existing:
            raise ValueError("Email already registered")

        # Hash password
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode(
            "utf-8"
        )

        # Insert user
        user_id = await db.insert(
            "INSERT INTO wp_users_auth (email, password_hash, name) VALUES (%s, %s, %s)",
            (email, password_hash, name),
        )

        logger.info("User registered: %s (ID: %d)", email, user_id)

        return {
            "id": user_id,
            "email": email,
            "name": name,
        }

    @staticmethod
    async def delete_user(user_id: int, password: str) -> bool:
        """Delete user account with safeguards.

        Args:
            user_id: User ID to delete
            password: User's password for confirmation

        Returns:
            True if deleted successfully

        Raises:
            ValueError: If validation fails or user cannot be deleted
            RuntimeError: If deletion fails
        """
        if not user_id or user_id <= 0:
            raise ValueError("Invalid user ID")

        if not password:
            raise ValueError("Password confirmation required")

        # Get user
        user = await db.fetchone(
            "SELECT id, email, password_hash FROM wp_users_auth WHERE id = %s",
            (user_id,),
        )

        if not user:
            raise ValueError("User not found")

        # Verify password
        if not bcrypt.checkpw(
            password.encode("utf-8"), user["password_hash"].encode("utf-8")
        ):
            logger.warning("User deletion failed: invalid password (user %d)", user_id)
            raise ValueError("Invalid password")

        # Check if user is sole owner of any organizations
        sole_owner_orgs = await db.fetchall(
            """
            SELECT o.id, o.name
            FROM wp_organizations o
            WHERE o.owner_id = %s
            AND NOT EXISTS (
                SELECT 1 FROM wp_organization_members m
                WHERE m.organization_id = o.id
                AND m.user_id != %s
                AND m.role IN ('owner', 'admin')
            )
            """,
            (user_id, user_id),
        )

        if sole_owner_orgs:
            org_names = ", ".join([org["name"] for org in sole_owner_orgs])
            raise ValueError(
                f"Cannot delete account: You are the sole owner of organizations: {org_names}. "
                "Please transfer ownership or delete these organizations first."
            )

        # Begin transaction-like deletion (manual since we're using autocommit)
        try:
            # Delete user sessions (will cascade via FK)
            rows = await db.execute(
                "DELETE FROM wp_sessions WHERE user_id = %s",
                (user_id,),
            )
            logger.info(f"Deleted {rows} sessions for user {user_id}")

            # Delete organization memberships (will cascade via FK)
            rows = await db.execute(
                "DELETE FROM wp_organization_members WHERE user_id = %s",
                (user_id,),
            )
            logger.info(f"Deleted {rows} organization memberships for user {user_id}")

            # Delete pending invites created by user
            rows = await db.execute(
                "DELETE FROM wp_organization_invites WHERE inviter_id = %s AND status = 'pending'",
                (user_id,),
            )
            logger.info(f"Deleted {rows} pending invites created by user {user_id}")

            # Nullify invitee_id in invites (FK is SET NULL)
            rows = await db.execute(
                "UPDATE wp_organization_invites SET invitee_id = NULL WHERE invitee_id = %s",
                (user_id,),
            )
            logger.info(f"Nullified {rows} invite references for user {user_id}")

            # Delete WordPress connections (will cascade via FK)
            rows = await db.execute(
                "DELETE FROM wp_wordpress_connections WHERE user_id = %s",
                (user_id,),
            )
            logger.info(f"Deleted {rows} WordPress connections for user {user_id}")

            # Delete audit logs (if they exist and reference the user)
            rows = await db.execute(
                "UPDATE wp_audit_log SET user_id = NULL WHERE user_id = %s",
                (user_id,),
            )
            logger.info(f"Nullified {rows} audit log references for user {user_id}")

            # Finally, delete the user
            rows = await db.execute(
                "DELETE FROM wp_users_auth WHERE id = %s",
                (user_id,),
            )

            if rows == 0:
                raise RuntimeError("User deletion failed: no rows affected")

            logger.info(f"User {user_id} ({user['email']}) deleted successfully")
            return True

        except Exception as e:
            logger.error(f"User deletion failed for user {user_id}: {e}")
            raise RuntimeError(f"Failed to delete user: {str(e)}")

    @staticmethod
    async def authenticate(email: str, password: str) -> Optional[dict]:
        """Authenticate user and create session.

        Args:
            email: User email
            password: Plain text password

        Returns:
            Dict with user info and session_id, or None if auth fails
        """
        # Get user
        user = await db.fetchone(
            "SELECT id, email, password_hash, name FROM wp_users_auth WHERE email = %s",
            (email,),
        )

        if not user:
            logger.warning("Login failed: user not found (%s)", email)
            return None

        # Verify password
        if not bcrypt.checkpw(
            password.encode("utf-8"), user["password_hash"].encode("utf-8")
        ):
            logger.warning("Login failed: invalid password (%s)", email)
            return None

        # Create session
        session_id = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        await db.execute(
            "INSERT INTO wp_sessions (id, user_id, expires_at) VALUES (%s, %s, %s)",
            (session_id, user["id"], expires_at),
        )

        logger.info("User authenticated: %s (ID: %d)", email, user["id"])

        return {
            "user": {
                "id": user["id"],
                "email": user["email"],
                "name": user["name"],
            },
            "session_id": session_id,
            "expires_at": expires_at.isoformat(),
        }

    @staticmethod
    async def get_user_from_session(session_id: str) -> Optional[dict]:
        """Get user from session ID.

        Args:
            session_id: Session identifier

        Returns:
            User dict or None if session invalid/expired
        """
        if not session_id:
            return None

        # Get session
        session = await db.fetchone(
            """
            SELECT s.user_id, s.expires_at, u.email, u.name
            FROM wp_sessions s
            JOIN wp_users_auth u ON s.user_id = u.id
            WHERE s.id = %s
            """,
            (session_id,),
        )

        if not session:
            return None

        # Check expiration
        # Database returns naive datetime, make it timezone-aware (UTC)
        expires_at = session["expires_at"]
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at < datetime.now(timezone.utc):
            # Delete expired session
            await db.execute("DELETE FROM wp_sessions WHERE id = %s", (session_id,))
            logger.info("Session expired: %s", session_id)
            return None

        return {
            "id": session["user_id"],
            "email": session["email"],
            "name": session["name"],
        }

    @staticmethod
    async def logout(session_id: str) -> bool:
        """Logout user by deleting session.

        Args:
            session_id: Session identifier

        Returns:
            True if session was deleted
        """
        result = await db.execute("DELETE FROM wp_sessions WHERE id = %s", (session_id,))
        if result > 0:
            logger.info("User logged out: session %s", session_id)
            return True
        return False

    @staticmethod
    async def get_user(user_id: int) -> Optional[dict]:
        """Get user by ID.

        Args:
            user_id: User database ID

        Returns:
            User dict or None
        """
        user = await db.fetchone(
            "SELECT id, email, name, created_at FROM wp_users_auth WHERE id = %s",
            (user_id,),
        )

        if user:
            return {
                "id": user["id"],
                "email": user["email"],
                "name": user["name"],
                "created_at": user["created_at"].isoformat(),
            }

        return None

    @staticmethod
    async def cleanup_expired_sessions():
        """Remove expired sessions from database."""
        result = await db.execute(
            "DELETE FROM wp_sessions WHERE expires_at < %s", (datetime.now(timezone.utc),)
        )
        if result > 0:
            logger.info("Cleaned up %d expired sessions", result)

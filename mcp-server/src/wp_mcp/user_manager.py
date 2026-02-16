"""User management and authentication."""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt

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

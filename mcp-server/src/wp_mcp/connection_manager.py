"""WordPress connection management for multi-user setup."""

from __future__ import annotations

import logging
import os
from typing import Optional

from cryptography.fernet import Fernet

from wp_mcp.database import db
from wp_mcp.url_validator import validate_wordpress_url

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manage user WordPress connections."""

    def __init__(self):
        """Initialize connection manager with encryption."""
        # Get encryption key from environment or generate one
        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            # Generate a key for development (should be set in production)
            key = Fernet.generate_key().decode()
            logger.warning(
                "ENCRYPTION_KEY not set, using generated key (not suitable for production)"
            )

        self.cipher = Fernet(key.encode() if isinstance(key, str) else key)

    def _encrypt(self, value: str) -> str:
        """Encrypt a value."""
        return self.cipher.encrypt(value.encode()).decode()

    def _decrypt(self, value: str) -> str:
        """Decrypt a value."""
        return self.cipher.decrypt(value.encode()).decode()

    async def add_connection(
        self,
        user_id: int,
        name: str,
        wp_url: str,
        wp_graphql_endpoint: str,
        wp_user: str,
        wp_app_password: str,
    ) -> dict:
        """Add a new WordPress connection for a user.

        Args:
            user_id: User database ID
            name: Connection name (e.g., "My Blog")
            wp_url: WordPress site URL
            wp_graphql_endpoint: GraphQL endpoint URL
            wp_user: WordPress username
            wp_app_password: WordPress application password

        Returns:
            Connection dict

        Raises:
            ValueError: If connection with name already exists or URL validation fails
        """
        # Validate URLs to prevent SSRF
        is_valid, error = validate_wordpress_url(wp_url)
        if not is_valid:
            raise ValueError(f"Invalid WordPress URL: {error}")

        is_valid, error = validate_wordpress_url(wp_graphql_endpoint)
        if not is_valid:
            raise ValueError(f"Invalid GraphQL endpoint URL: {error}")

        # Check for duplicate name
        existing = await db.fetchone(
            "SELECT id FROM wp_wordpress_connections WHERE user_id = %s AND name = %s",
            (user_id, name),
        )
        if existing:
            raise ValueError(f"Connection '{name}' already exists")

        # Encrypt app password
        encrypted_password = self._encrypt(wp_app_password)

        # Check if user has no connections (make this first one active)
        has_connections = await db.fetchone(
            "SELECT id FROM wp_wordpress_connections WHERE user_id = %s LIMIT 1",
            (user_id,),
        )
        is_active = 1 if not has_connections else 0

        # Insert connection
        connection_id = await db.insert(
            """
            INSERT INTO wp_wordpress_connections
            (user_id, name, wp_url, wp_graphql_endpoint, wp_user, wp_app_password, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                user_id,
                name,
                wp_url,
                wp_graphql_endpoint,
                wp_user,
                encrypted_password,
                is_active,
            ),
        )

        logger.info(
            "Connection added: %s for user %d (ID: %d)", name, user_id, connection_id
        )

        return {
            "id": connection_id,
            "user_id": user_id,
            "name": name,
            "wp_url": wp_url,
            "wp_graphql_endpoint": wp_graphql_endpoint,
            "wp_user": wp_user,
            "is_active": bool(is_active),
        }

    async def get_connections(self, user_id: int) -> list[dict]:
        """Get all WordPress connections for a user.

        Args:
            user_id: User database ID

        Returns:
            List of connection dicts (without passwords)
        """
        connections = await db.fetchall(
            """
            SELECT id, name, wp_url, wp_graphql_endpoint, wp_user, is_active, created_at
            FROM wp_wordpress_connections
            WHERE user_id = %s
            ORDER BY created_at DESC
            """,
            (user_id,),
        )

        return [
            {
                "id": conn["id"],
                "name": conn["name"],
                "wp_url": conn["wp_url"],
                "wp_graphql_endpoint": conn["wp_graphql_endpoint"],
                "wp_user": conn["wp_user"],
                "is_active": bool(conn["is_active"]),
                "created_at": conn["created_at"].isoformat(),
            }
            for conn in connections
        ]

    async def get_connection(self, connection_id: int, user_id: int) -> Optional[dict]:
        """Get a specific connection with decrypted password.

        Args:
            connection_id: Connection database ID
            user_id: User database ID (for authorization)

        Returns:
            Connection dict with decrypted password, or None
        """
        connection = await db.fetchone(
            """
            SELECT id, user_id, name, wp_url, wp_graphql_endpoint, wp_user,
                   wp_app_password, is_active, created_at
            FROM wp_wordpress_connections
            WHERE id = %s AND user_id = %s
            """,
            (connection_id, user_id),
        )

        if not connection:
            return None

        # Decrypt password
        try:
            decrypted_password = self._decrypt(connection["wp_app_password"])
        except Exception as e:
            logger.error("Failed to decrypt password for connection %d: %s", connection_id, e)
            decrypted_password = ""

        return {
            "id": connection["id"],
            "user_id": connection["user_id"],
            "name": connection["name"],
            "wp_url": connection["wp_url"],
            "wp_graphql_endpoint": connection["wp_graphql_endpoint"],
            "wp_user": connection["wp_user"],
            "wp_app_password": decrypted_password,
            "is_active": bool(connection["is_active"]),
            "created_at": connection["created_at"].isoformat(),
        }

    async def get_active_connection(self, user_id: int) -> Optional[dict]:
        """Get the active WordPress connection for a user.

        Args:
            user_id: User database ID

        Returns:
            Active connection dict with decrypted password, or None
        """
        connection = await db.fetchone(
            """
            SELECT id, user_id, name, wp_url, wp_graphql_endpoint, wp_user,
                   wp_app_password, is_active
            FROM wp_wordpress_connections
            WHERE user_id = %s AND is_active = 1
            LIMIT 1
            """,
            (user_id,),
        )

        if not connection:
            return None

        # Decrypt password
        try:
            decrypted_password = self._decrypt(connection["wp_app_password"])
        except Exception as e:
            logger.error("Failed to decrypt password for connection %d: %s", connection["id"], e)
            decrypted_password = ""

        return {
            "id": connection["id"],
            "user_id": connection["user_id"],
            "name": connection["name"],
            "wp_url": connection["wp_url"],
            "wp_graphql_endpoint": connection["wp_graphql_endpoint"],
            "wp_user": connection["wp_user"],
            "wp_app_password": decrypted_password,
            "is_active": True,
        }

    async def set_active_connection(self, connection_id: int, user_id: int) -> bool:
        """Set a connection as active for a user.

        Args:
            connection_id: Connection database ID
            user_id: User database ID (for authorization)

        Returns:
            True if successful

        Raises:
            ValueError: If connection not found or unauthorized
        """
        # Verify connection exists and belongs to user
        connection = await db.fetchone(
            "SELECT id FROM wp_wordpress_connections WHERE id = %s AND user_id = %s",
            (connection_id, user_id),
        )

        if not connection:
            raise ValueError("Connection not found or unauthorized")

        # Deactivate all connections for user
        await db.execute(
            "UPDATE wp_wordpress_connections SET is_active = 0 WHERE user_id = %s",
            (user_id,),
        )

        # Activate selected connection
        await db.execute(
            "UPDATE wp_wordpress_connections SET is_active = 1 WHERE id = %s",
            (connection_id,),
        )

        logger.info("Connection %d activated for user %d", connection_id, user_id)
        return True

    async def update_connection(
        self,
        connection_id: int,
        user_id: int,
        name: Optional[str] = None,
        wp_url: Optional[str] = None,
        wp_graphql_endpoint: Optional[str] = None,
        wp_user: Optional[str] = None,
        wp_app_password: Optional[str] = None,
    ) -> bool:
        """Update a WordPress connection.

        Args:
            connection_id: Connection database ID
            user_id: User database ID (for authorization)
            name: New connection name (optional)
            wp_url: New WordPress URL (optional)
            wp_graphql_endpoint: New GraphQL endpoint (optional)
            wp_user: New WordPress username (optional)
            wp_app_password: New application password (optional)

        Returns:
            True if successful

        Raises:
            ValueError: If connection not found, unauthorized, or URL validation fails
        """
        # Validate URLs if provided
        if wp_url is not None:
            is_valid, error = validate_wordpress_url(wp_url)
            if not is_valid:
                raise ValueError(f"Invalid WordPress URL: {error}")

        if wp_graphql_endpoint is not None:
            is_valid, error = validate_wordpress_url(wp_graphql_endpoint)
            if not is_valid:
                raise ValueError(f"Invalid GraphQL endpoint URL: {error}")

        # Verify connection exists and belongs to user
        connection = await db.fetchone(
            "SELECT id FROM wp_wordpress_connections WHERE id = %s AND user_id = %s",
            (connection_id, user_id),
        )

        if not connection:
            raise ValueError("Connection not found or unauthorized")

        # Build update query
        updates = []
        params = []

        if name is not None:
            updates.append("name = %s")
            params.append(name)
        if wp_url is not None:
            updates.append("wp_url = %s")
            params.append(wp_url)
        if wp_graphql_endpoint is not None:
            updates.append("wp_graphql_endpoint = %s")
            params.append(wp_graphql_endpoint)
        if wp_user is not None:
            updates.append("wp_user = %s")
            params.append(wp_user)
        if wp_app_password is not None:
            updates.append("wp_app_password = %s")
            params.append(self._encrypt(wp_app_password))

        if not updates:
            return True  # Nothing to update

        params.append(connection_id)
        query = f"UPDATE wp_wordpress_connections SET {', '.join(updates)} WHERE id = %s"

        await db.execute(query, tuple(params))
        logger.info("Connection %d updated for user %d", connection_id, user_id)
        return True

    async def delete_connection(self, connection_id: int, user_id: int) -> bool:
        """Delete a WordPress connection.

        Args:
            connection_id: Connection database ID
            user_id: User database ID (for authorization)

        Returns:
            True if deleted

        Raises:
            ValueError: If connection not found or unauthorized
        """
        result = await db.execute(
            "DELETE FROM wp_wordpress_connections WHERE id = %s AND user_id = %s",
            (connection_id, user_id),
        )

        if result == 0:
            raise ValueError("Connection not found or unauthorized")

        logger.info("Connection %d deleted for user %d", connection_id, user_id)
        return True


# Global connection manager instance
connection_manager = ConnectionManager()

"""Organization API key management for WordPress site registration."""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from wp_mcp.database import db

logger = logging.getLogger(__name__)


class OrgApiKeyManager:
    """Manage organization API keys for remote WordPress registration."""

    # API key format: wpai_org_{organization_id}_{32_random_chars}
    KEY_PREFIX = "wpai_org_"
    KEY_LENGTH = 32  # Random part length in bytes
    DEFAULT_EXPIRY_DAYS = 7

    @staticmethod
    def _generate_api_key(org_id: int) -> tuple[str, str, str]:
        """Generate a new API key.

        Args:
            org_id: Organization ID to embed in key

        Returns:
            Tuple of (full_key, key_hash, key_prefix)
        """
        # Generate URL-safe random token
        random_part = secrets.token_urlsafe(OrgApiKeyManager.KEY_LENGTH)

        # Full key format: wpai_org_{org_id}_{random}
        full_key = f"{OrgApiKeyManager.KEY_PREFIX}{org_id}_{random_part}"

        # Hash for storage (SHA-256)
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()

        # Prefix for display (first 12 chars)
        key_prefix = full_key[:12]

        return full_key, key_hash, key_prefix

    @staticmethod
    async def create_api_key(
        organization_id: int,
        created_by: int,
        description: Optional[str] = None,
        expiry_days: int = DEFAULT_EXPIRY_DAYS,
    ) -> dict[str, Any]:
        """Create a new organization API key.

        Args:
            organization_id: Organization ID
            created_by: User ID creating the key (must be org owner/admin)
            description: Optional description
            expiry_days: Days until expiration (default 7)

        Returns:
            Dict with key details including full key (only shown once!)

        Raises:
            ValueError: If user lacks permission or validation fails
        """
        # Check if user has permission (owner or admin)
        member = await db.fetchone(
            """
            SELECT role FROM wp_organization_members
            WHERE organization_id = %s AND user_id = %s
            """,
            (organization_id, created_by),
        )

        if not member:
            raise ValueError("Not a member of this organization")

        if member["role"] not in ("owner", "admin"):
            raise ValueError("Only owners and admins can create API keys")

        # Generate key
        full_key, key_hash, key_prefix = OrgApiKeyManager._generate_api_key(
            organization_id
        )

        # Calculate expiration (UTC timezone-aware)
        expires_at = datetime.now(timezone.utc) + timedelta(days=expiry_days)

        # Insert into database
        key_id = await db.insert(
            """
            INSERT INTO wp_org_api_keys
            (organization_id, created_by, key_hash, key_prefix, description, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                organization_id,
                created_by,
                key_hash,
                key_prefix,
                description,
                expires_at,
            ),
        )

        logger.info(
            f"API key created: {key_prefix}... for org {organization_id} "
            f"by user {created_by}"
        )

        return {
            "id": key_id,
            "key": full_key,  # ONLY returned on creation!
            "key_prefix": key_prefix,
            "organization_id": organization_id,
            "description": description,
            "expires_at": expires_at.isoformat(),
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    async def validate_and_consume_key(api_key: str) -> Optional[dict[str, Any]]:
        """Validate an API key and mark it as used (single-use).

        Args:
            api_key: Full API key string

        Returns:
            Organization details if valid and unused, None otherwise
        """
        # Hash the provided key
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        # Look up key with organization details
        key_record = await db.fetchone(
            """
            SELECT
                k.id,
                k.organization_id,
                k.key_prefix,
                k.used_at,
                k.is_active,
                k.expires_at,
                o.name as org_name,
                o.slug as org_slug
            FROM wp_org_api_keys k
            INNER JOIN wp_organizations o ON o.id = k.organization_id
            WHERE k.key_hash = %s
            """,
            (key_hash,),
        )

        if not key_record:
            logger.warning("API key validation failed: key not found")
            return None

        # Check if already used (single-use enforcement)
        if key_record["used_at"]:
            logger.warning(
                f"API key already used: {key_record['key_prefix']}... "
                f"(used at {key_record['used_at']})"
            )
            return None

        # Check if active
        if not key_record["is_active"]:
            logger.warning(f"API key revoked: {key_record['key_prefix']}...")
            return None

        # Check expiration (handle both timezone-aware and naive datetimes)
        expires_at = key_record["expires_at"]
        if expires_at.tzinfo is None:
            # If naive, assume UTC
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at < datetime.now(timezone.utc):
            logger.warning(
                f"API key expired: {key_record['key_prefix']}... "
                f"(expired {key_record['expires_at']})"
            )
            return None

        # Mark as used (single-use)
        await db.execute(
            """
            UPDATE wp_org_api_keys
            SET used_at = %s
            WHERE id = %s
            """,
            (datetime.now(timezone.utc), key_record["id"]),
        )

        logger.info(
            f"API key consumed: {key_record['key_prefix']}... "
            f"for org {key_record['organization_id']}"
        )

        return {
            "organization_id": key_record["organization_id"],
            "organization_name": key_record["org_name"],
            "organization_slug": key_record["org_slug"],
            "key_id": key_record["id"],
        }

    @staticmethod
    async def list_keys(
        organization_id: int, user_id: int
    ) -> list[dict[str, Any]]:
        """List API keys for an organization.

        Args:
            organization_id: Organization ID
            user_id: Requesting user ID (must be member)

        Returns:
            List of key dicts (without full keys or hashes)

        Raises:
            ValueError: If user is not a member
        """
        # Check membership
        member = await db.fetchone(
            """
            SELECT role FROM wp_organization_members
            WHERE organization_id = %s AND user_id = %s
            """,
            (organization_id, user_id),
        )

        if not member:
            raise ValueError("Not a member of this organization")

        # Fetch keys
        keys = await db.fetchall(
            """
            SELECT
                k.id,
                k.key_prefix,
                k.description,
                k.expires_at,
                k.used_at,
                k.is_active,
                k.created_at,
                u.username as created_by_username
            FROM wp_org_api_keys k
            INNER JOIN wp_users_auth u ON u.id = k.created_by
            WHERE k.organization_id = %s
            ORDER BY k.created_at DESC
            """,
            (organization_id,),
        )

        return [
            {
                "id": key["id"],
                "key_prefix": key["key_prefix"],
                "description": key["description"],
                "expires_at": (
                    key["expires_at"].isoformat() if key["expires_at"] else None
                ),
                "used_at": key["used_at"].isoformat() if key["used_at"] else None,
                "is_active": bool(key["is_active"]),
                "created_at": key["created_at"].isoformat(),
                "created_by": key["created_by_username"],
            }
            for key in keys
        ]

    @staticmethod
    async def revoke_key(
        key_id: int, organization_id: int, user_id: int
    ) -> bool:
        """Revoke an API key.

        Args:
            key_id: API key ID
            organization_id: Organization ID (for verification)
            user_id: Requesting user ID (must be owner/admin)

        Returns:
            True if revoked successfully

        Raises:
            ValueError: If unauthorized or key not found
        """
        # Check permission (owner or admin)
        member = await db.fetchone(
            """
            SELECT role FROM wp_organization_members
            WHERE organization_id = %s AND user_id = %s
            """,
            (organization_id, user_id),
        )

        if not member or member["role"] not in ("owner", "admin"):
            raise ValueError("Only owners and admins can revoke API keys")

        # Revoke key
        rows = await db.execute(
            """
            UPDATE wp_org_api_keys
            SET is_active = 0
            WHERE id = %s AND organization_id = %s
            """,
            (key_id, organization_id),
        )

        if rows == 0:
            raise ValueError("API key not found")

        logger.info(f"API key {key_id} revoked by user {user_id}")
        return True

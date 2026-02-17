"""
Multi-Tenancy Support for WP-AI

Manages isolated WordPress instances per user/organization.
Each tenant can have their own WordPress site with separate database.
"""

import uuid
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from cryptography.fernet import Fernet
from wp_mcp.database import get_connection

logger = logging.getLogger(__name__)


class TenantManager:
    """Manages multi-tenant WordPress instances"""

    def __init__(self, encryption_key: str):
        """
        Initialize tenant manager

        Args:
            encryption_key: Fernet key for encrypting tenant DB passwords
        """
        self.cipher = Fernet(encryption_key.encode())

    def create_tenant(
        self,
        name: str,
        slug: str,
        owner_user_id: int,
        wp_url: str,
        wp_graphql_endpoint: str,
        wp_admin_user: str,
        wp_admin_email: Optional[str] = None,
        db_host: Optional[str] = None,
        db_name: Optional[str] = None,
        db_user: Optional[str] = None,
        db_password: Optional[str] = None,
        max_posts: int = 1000,
        max_storage_mb: int = 5000,
        max_users: int = 10,
    ) -> str:
        """
        Create a new tenant

        Args:
            name: Human-readable tenant name
            slug: URL-safe identifier (e.g., 'acme-corp')
            owner_user_id: User ID of the tenant owner
            wp_url: WordPress instance URL
            wp_graphql_endpoint: GraphQL endpoint URL
            wp_admin_user: WordPress admin username
            wp_admin_email: WordPress admin email
            db_host: Database host (if using separate DB)
            db_name: Database name
            db_user: Database username
            db_password: Database password (will be encrypted)
            max_posts: Maximum number of posts allowed
            max_storage_mb: Maximum storage in MB
            max_users: Maximum number of users

        Returns:
            tenant_id: UUID of created tenant
        """
        tenant_id = str(uuid.uuid4())

        # Encrypt database password if provided
        db_password_encrypted = None
        if db_password:
            db_password_encrypted = self.cipher.encrypt(db_password.encode()).decode()

        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO tenants (
                    id, name, slug, owner_user_id,
                    wp_url, wp_graphql_endpoint, wp_admin_user, wp_admin_email,
                    db_host, db_port, db_name, db_user, db_password_encrypted,
                    max_posts, max_storage_mb, max_users,
                    status, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """,
                (
                    tenant_id,
                    name,
                    slug,
                    owner_user_id,
                    wp_url,
                    wp_graphql_endpoint,
                    wp_admin_user,
                    wp_admin_email,
                    db_host,
                    3306,  # Default MySQL port
                    db_name,
                    db_user,
                    db_password_encrypted,
                    max_posts,
                    max_storage_mb,
                    max_users,
                    "active",
                ),
            )

            # Add owner to tenant_users
            cursor.execute(
                """
                INSERT INTO tenant_users (tenant_id, user_id, role)
                VALUES (%s, %s, %s)
                """,
                (tenant_id, owner_user_id, "owner"),
            )

            # Initialize usage tracking
            cursor.execute(
                """
                INSERT INTO tenant_usage (tenant_id)
                VALUES (%s)
                """,
                (tenant_id,),
            )

            conn.commit()
            logger.info(f"Created tenant {tenant_id} ({name}) for user {owner_user_id}")
            return tenant_id

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to create tenant: {e}")
            raise
        finally:
            cursor.close()

    def get_tenant(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get tenant by ID"""
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute(
                """
                SELECT id, name, slug, owner_user_id, wp_url, wp_graphql_endpoint,
                       wp_admin_user, wp_admin_email, db_host, db_port, db_name, db_user,
                       status, max_posts, max_storage_mb, max_users,
                       created_at, updated_at
                FROM tenants
                WHERE id = %s AND status != 'deleted'
                """,
                (tenant_id,),
            )

            tenant = cursor.fetchone()
            return tenant

        finally:
            cursor.close()

    def get_user_tenants(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all tenants accessible by a user"""
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute(
                """
                SELECT t.id, t.name, t.slug, t.wp_url, t.status,
                       tu.role, t.created_at
                FROM tenants t
                INNER JOIN tenant_users tu ON t.id = tu.tenant_id
                WHERE tu.user_id = %s AND t.status = 'active'
                ORDER BY t.created_at DESC
                """,
                (user_id,),
            )

            tenants = cursor.fetchall()
            return tenants

        finally:
            cursor.close()

    def update_tenant_status(self, tenant_id: str, status: str) -> bool:
        """Update tenant status (active, suspended, deleted)"""
        if status not in ("active", "suspended", "deleted"):
            raise ValueError(f"Invalid status: {status}")

        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                UPDATE tenants
                SET status = %s,
                    deleted_at = CASE WHEN %s = 'deleted' THEN NOW() ELSE NULL END
                WHERE id = %s
                """,
                (status, status, tenant_id),
            )

            conn.commit()
            affected = cursor.rowcount > 0
            if affected:
                logger.info(f"Updated tenant {tenant_id} status to {status}")
            return affected

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to update tenant status: {e}")
            raise
        finally:
            cursor.close()

    def add_user_to_tenant(
        self, tenant_id: str, user_id: int, role: str = "viewer"
    ) -> bool:
        """Add a user to a tenant with specified role"""
        if role not in ("owner", "admin", "editor", "viewer"):
            raise ValueError(f"Invalid role: {role}")

        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO tenant_users (tenant_id, user_id, role)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE role = VALUES(role)
                """,
                (tenant_id, user_id, role),
            )

            conn.commit()
            logger.info(f"Added user {user_id} to tenant {tenant_id} with role {role}")
            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to add user to tenant: {e}")
            raise
        finally:
            cursor.close()

    def remove_user_from_tenant(self, tenant_id: str, user_id: int) -> bool:
        """Remove a user from a tenant"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            # Don't allow removing the owner
            cursor.execute(
                "SELECT role FROM tenant_users WHERE tenant_id = %s AND user_id = %s",
                (tenant_id, user_id),
            )
            result = cursor.fetchone()

            if result and result[0] == "owner":
                raise ValueError("Cannot remove owner from tenant")

            cursor.execute(
                "DELETE FROM tenant_users WHERE tenant_id = %s AND user_id = %s",
                (tenant_id, user_id),
            )

            conn.commit()
            affected = cursor.rowcount > 0
            if affected:
                logger.info(f"Removed user {user_id} from tenant {tenant_id}")
            return affected

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to remove user from tenant: {e}")
            raise
        finally:
            cursor.close()

    def get_tenant_usage(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get current usage stats for a tenant"""
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute(
                """
                SELECT post_count, storage_used_mb, user_count, updated_at
                FROM tenant_usage
                WHERE tenant_id = %s
                """,
                (tenant_id,),
            )

            usage = cursor.fetchone()
            return usage

        finally:
            cursor.close()

    def update_tenant_usage(
        self, tenant_id: str, post_count: int, storage_used_mb: float, user_count: int
    ) -> bool:
        """Update tenant usage statistics"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                UPDATE tenant_usage
                SET post_count = %s, storage_used_mb = %s, user_count = %s,
                    updated_at = NOW()
                WHERE tenant_id = %s
                """,
                (post_count, storage_used_mb, user_count, tenant_id),
            )

            conn.commit()
            return cursor.rowcount > 0

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to update tenant usage: {e}")
            raise
        finally:
            cursor.close()

    def get_decrypted_db_password(self, tenant_id: str) -> Optional[str]:
        """Get decrypted database password for a tenant"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT db_password_encrypted FROM tenants WHERE id = %s",
                (tenant_id,),
            )

            result = cursor.fetchone()
            if not result or not result[0]:
                return None

            encrypted_password = result[0]
            decrypted = self.cipher.decrypt(encrypted_password.encode()).decode()
            return decrypted

        finally:
            cursor.close()

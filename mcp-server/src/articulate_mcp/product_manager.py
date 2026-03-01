"""Product management for digital sales and access grants."""

from __future__ import annotations

import json
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from articulate_mcp.database import db

logger = logging.getLogger(__name__)


class ProductManager:
    """Manage digital products and access grants."""

    @staticmethod
    def _format_product(row: dict[str, Any]) -> dict[str, Any]:
        """Format a product row from the database.

        Converts datetime fields to ISO format strings and parses JSON fields.
        """
        if row is None:
            return row

        result = dict(row)

        # Parse content_ids from JSON string to list
        if result.get("content_ids"):
            if isinstance(result["content_ids"], str):
                result["content_ids"] = json.loads(result["content_ids"])
        else:
            result["content_ids"] = []

        # Convert datetime fields to ISO format strings
        for field in ("created_at", "updated_at"):
            if result.get(field) and isinstance(result[field], datetime):
                if result[field].tzinfo is None:
                    result[field] = result[field].replace(tzinfo=timezone.utc)
                result[field] = result[field].isoformat()

        # Convert is_active to boolean
        if "is_active" in result:
            result["is_active"] = bool(result["is_active"])

        return result

    @staticmethod
    def _format_grant(row: dict[str, Any]) -> dict[str, Any]:
        """Format an access grant row from the database.

        Converts datetime fields to ISO format strings and parses JSON fields.
        """
        if row is None:
            return row

        result = dict(row)

        # Convert datetime fields to ISO format strings
        for field in ("created_at", "expires_at", "revoked_at", "last_accessed_at"):
            if result.get(field) and isinstance(result[field], datetime):
                if result[field].tzinfo is None:
                    result[field] = result[field].replace(tzinfo=timezone.utc)
                result[field] = result[field].isoformat()

        return result

    @staticmethod
    async def create_product(
        name: str,
        price_cents: int,
        created_by: int,
        currency: str = "usd",
        description: str = "",
        content_ids: Optional[list[int]] = None,
        file_path: Optional[str] = None,
        file_name: Optional[str] = None,
        access_duration_days: Optional[int] = None,
        download_limit: Optional[int] = None,
        organization_id: Optional[int] = None,
        stripe_price_id: Optional[str] = None,
        stripe_product_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create a new digital product.

        Args:
            name: Product name
            price_cents: Price in smallest currency unit (e.g. cents for USD)
            created_by: User ID of the product creator
            currency: Three-letter currency code (default: usd)
            description: Product description
            content_ids: List of WP post/page IDs this product grants access to
            file_path: Path or URL to downloadable file
            file_name: Original filename for download
            access_duration_days: Number of days access lasts (None = permanent)
            download_limit: Max number of downloads (None = unlimited)
            organization_id: Organization that owns this product
            stripe_price_id: Stripe Price object ID
            stripe_product_id: Stripe Product object ID

        Returns:
            Created product dict
        """
        content_ids_json = json.dumps(content_ids) if content_ids else None

        product_id = await db.insert(
            """
            INSERT INTO articulate_products
                (name, price_cents, created_by, currency, description,
                 content_ids, file_path, file_name, access_duration_days,
                 download_limit, organization_id, stripe_price_id, stripe_product_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                name, price_cents, created_by, currency, description,
                content_ids_json, file_path, file_name, access_duration_days,
                download_limit, organization_id, stripe_price_id, stripe_product_id,
            ),
        )

        logger.info("Created product %d: %s (by user %d)", product_id, name, created_by)

        product = await db.fetchone(
            "SELECT * FROM articulate_products WHERE id = %s", (product_id,)
        )
        return ProductManager._format_product(product)

    @staticmethod
    async def get_product(product_id: int) -> Optional[dict[str, Any]]:
        """Get a product by ID.

        Args:
            product_id: Product ID

        Returns:
            Product dict or None if not found
        """
        row = await db.fetchone(
            "SELECT * FROM articulate_products WHERE id = %s", (product_id,)
        )
        if row is None:
            return None
        return ProductManager._format_product(row)

    @staticmethod
    async def list_products(
        created_by: Optional[int] = None,
        organization_id: Optional[int] = None,
        active_only: bool = True,
    ) -> list[dict[str, Any]]:
        """List products with optional filters.

        Args:
            created_by: Filter by creator user ID
            organization_id: Filter by organization ID
            active_only: Only return active products (default: True)

        Returns:
            List of product dicts
        """
        conditions = []
        params: list[Any] = []

        if active_only:
            conditions.append("is_active = 1")

        if created_by is not None:
            conditions.append("created_by = %s")
            params.append(created_by)

        if organization_id is not None:
            conditions.append("organization_id = %s")
            params.append(organization_id)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT * FROM articulate_products WHERE {where_clause} ORDER BY created_at DESC"

        rows = await db.fetchall(query, tuple(params))
        return [ProductManager._format_product(row) for row in rows]

    @staticmethod
    async def update_product(product_id: int, **kwargs: Any) -> Optional[dict[str, Any]]:
        """Update a product.

        Args:
            product_id: Product ID to update
            **kwargs: Fields to update (name, price_cents, currency, description,
                      content_ids, file_path, file_name, access_duration_days,
                      download_limit, is_active, stripe_price_id, stripe_product_id)

        Returns:
            Updated product dict or None if not found
        """
        allowed_fields = {
            "name", "price_cents", "currency", "description", "content_ids",
            "file_path", "file_name", "access_duration_days", "download_limit",
            "is_active", "stripe_price_id", "stripe_product_id", "organization_id",
        }

        updates = {}
        for key, value in kwargs.items():
            if key in allowed_fields:
                if key == "content_ids" and value is not None:
                    updates[key] = json.dumps(value)
                else:
                    updates[key] = value

        if not updates:
            return await ProductManager.get_product(product_id)

        set_clause = ", ".join(f"{k} = %s" for k in updates)
        params = list(updates.values()) + [product_id]

        affected = await db.execute(
            f"UPDATE articulate_products SET {set_clause} WHERE id = %s",
            tuple(params),
        )

        if affected == 0:
            return None

        logger.info("Updated product %d: %s", product_id, list(updates.keys()))
        return await ProductManager.get_product(product_id)

    @staticmethod
    async def create_access_grant(
        product_id: int,
        customer_email: str,
        customer_name: Optional[str] = None,
        amount_paid: int = 0,
        currency: str = "usd",
        stripe_session_id: Optional[str] = None,
        stripe_payment_intent_id: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """Create an access grant for a customer after purchase.

        Generates a unique access token and inherits expiry/download limits
        from the product.

        Args:
            product_id: Product being purchased
            customer_email: Customer's email address
            customer_name: Customer's name
            amount_paid: Amount paid in smallest currency unit
            currency: Currency code
            stripe_session_id: Stripe Checkout session ID
            stripe_payment_intent_id: Stripe PaymentIntent ID
            user_id: Linked Articulate user ID if registered

        Returns:
            Created access grant dict
        """
        # Get the product to inherit settings
        product = await db.fetchone(
            "SELECT * FROM articulate_products WHERE id = %s", (product_id,)
        )
        if product is None:
            raise ValueError(f"Product {product_id} not found")

        # Generate unique access token (48 characters)
        access_token = secrets.token_urlsafe(36)

        # Calculate expiry from product settings
        expires_at = None
        if product["access_duration_days"] is not None:
            expires_at = datetime.now(timezone.utc) + timedelta(
                days=product["access_duration_days"]
            )

        # Inherit download limit from product
        download_limit = product["download_limit"]

        grant_id = await db.insert(
            """
            INSERT INTO articulate_access_grants
                (product_id, customer_email, customer_name, user_id,
                 access_token, stripe_session_id, stripe_payment_intent_id,
                 amount_paid, currency, download_limit, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                product_id, customer_email, customer_name, user_id,
                access_token, stripe_session_id, stripe_payment_intent_id,
                amount_paid, currency, download_limit, expires_at,
            ),
        )

        logger.info(
            "Created access grant %d for product %d (customer: %s)",
            grant_id, product_id, customer_email,
        )

        grant = await db.fetchone(
            "SELECT * FROM articulate_access_grants WHERE id = %s", (grant_id,)
        )
        return ProductManager._format_grant(grant)

    @staticmethod
    async def validate_access_token(token: str) -> Optional[dict[str, Any]]:
        """Validate an access token and return grant + product info.

        Checks that the token:
        - Exists and is not revoked
        - Has not expired
        - Has not exceeded download limit

        Args:
            token: The access token to validate

        Returns:
            Dict with grant and product info (including content_ids), or None if invalid
        """
        grant = await db.fetchone(
            """
            SELECT g.*, p.name AS product_name, p.content_ids, p.file_path,
                   p.file_name, p.description AS product_description,
                   p.is_active AS product_active
            FROM articulate_access_grants g
            JOIN articulate_products p ON g.product_id = p.id
            WHERE g.access_token = %s
            """,
            (token,),
        )

        if grant is None:
            return None

        # Check if revoked
        if grant.get("revoked_at") is not None:
            logger.debug("Access token rejected: revoked (grant %d)", grant["id"])
            return None

        # Check if expired
        if grant.get("expires_at") is not None:
            expires_at = grant["expires_at"]
            if isinstance(expires_at, datetime):
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                if expires_at < datetime.now(timezone.utc):
                    logger.debug("Access token rejected: expired (grant %d)", grant["id"])
                    return None

        # Check download limit
        if grant.get("download_limit") is not None:
            if grant["download_count"] >= grant["download_limit"]:
                logger.debug(
                    "Access token rejected: download limit reached (grant %d, %d/%d)",
                    grant["id"], grant["download_count"], grant["download_limit"],
                )
                return None

        # Parse content_ids from JSON
        result = dict(grant)
        if result.get("content_ids"):
            if isinstance(result["content_ids"], str):
                result["content_ids"] = json.loads(result["content_ids"])
        else:
            result["content_ids"] = []

        # Convert datetime fields
        for field in ("created_at", "expires_at", "revoked_at", "last_accessed_at"):
            if result.get(field) and isinstance(result[field], datetime):
                if result[field].tzinfo is None:
                    result[field] = result[field].replace(tzinfo=timezone.utc)
                result[field] = result[field].isoformat()

        return result

    @staticmethod
    async def record_download(grant_id: int) -> None:
        """Record a download for an access grant.

        Increments download_count and updates last_accessed_at.

        Args:
            grant_id: Access grant ID
        """
        await db.execute(
            """
            UPDATE articulate_access_grants
            SET download_count = download_count + 1,
                last_accessed_at = %s
            WHERE id = %s
            """,
            (datetime.now(timezone.utc), grant_id),
        )
        logger.info("Recorded download for grant %d", grant_id)

    @staticmethod
    async def revoke_access(grant_id: int) -> None:
        """Revoke an access grant.

        Args:
            grant_id: Access grant ID
        """
        await db.execute(
            """
            UPDATE articulate_access_grants
            SET revoked_at = %s
            WHERE id = %s
            """,
            (datetime.now(timezone.utc), grant_id),
        )
        logger.info("Revoked access grant %d", grant_id)

    @staticmethod
    async def list_grants_for_product(product_id: int) -> list[dict[str, Any]]:
        """List all access grants for a product.

        Args:
            product_id: Product ID

        Returns:
            List of access grant dicts
        """
        rows = await db.fetchall(
            """
            SELECT * FROM articulate_access_grants
            WHERE product_id = %s
            ORDER BY created_at DESC
            """,
            (product_id,),
        )
        return [ProductManager._format_grant(row) for row in rows]

    @staticmethod
    async def list_grants_for_customer(email: str) -> list[dict[str, Any]]:
        """List all access grants for a customer by email.

        Args:
            email: Customer email address

        Returns:
            List of access grant dicts
        """
        rows = await db.fetchall(
            """
            SELECT * FROM articulate_access_grants
            WHERE customer_email = %s
            ORDER BY created_at DESC
            """,
            (email,),
        )
        return [ProductManager._format_grant(row) for row in rows]

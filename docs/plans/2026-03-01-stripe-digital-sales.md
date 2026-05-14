# Stripe Digital File Sales Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Sell digital files through Articulate with Stripe Checkout, delivering unique per-customer access tokens for content access.

**Architecture:** Products are stored in the MCP database (not WordPress). Stripe Checkout Sessions handle payment. On successful payment, a webhook creates a unique access grant with a token emailed to the customer. The token unlocks specific WordPress content (posts, pages, courses) through the MCP server layer. No WordPress e-commerce plugins needed.

**Tech Stack:** Python `stripe` package, Stripe Checkout Sessions API, Stripe Webhooks, MariaDB, Postfix SMTP, Next.js frontend, existing MCP server patterns (Starlette routes, FastMCP tools, aiomysql).

---

### Task 1: Add `stripe` Python Dependency

**Files:**
- Modify: `mcp-server/pyproject.toml`

**Step 1: Add stripe to dependencies**

In `mcp-server/pyproject.toml`, add `"stripe>=8.0.0"` to the `dependencies` list:

```toml
dependencies = [
    "mcp[cli]>=1.0.0",
    "httpx>=0.27.0",
    "python-dotenv>=1.0.0",
    "uvicorn>=0.30.0",
    "redis>=5.0.0",
    "celery>=5.3.0",
    "aiomysql>=0.2.0",
    "bcrypt>=4.0.0",
    "cryptography>=41.0.0",
    "Pillow>=10.0.0",
    "anthropic>=0.40.0",
    "python-on-whales>=0.70.0",
    "Jinja2>=3.1.0",
    "stripe>=8.0.0",
]
```

**Step 2: Add Stripe env vars to docker-compose**

In `docker-compose.production.yml`, add to the `mcp-server` service `environment` section:

```yaml
    STRIPE_SECRET_KEY: ${STRIPE_SECRET_KEY:-}
    STRIPE_WEBHOOK_SECRET: ${STRIPE_WEBHOOK_SECRET:-}
    STRIPE_PUBLISHABLE_KEY: ${STRIPE_PUBLISHABLE_KEY:-}
```

**Step 3: Verify the package installs**

```bash
cd mcp-server && uv pip install -e ".[dev]"
python -c "import stripe; print(stripe.VERSION)"
```

Expected: prints stripe version (e.g., `12.1.0`)

**Step 4: Commit**

```bash
git add mcp-server/pyproject.toml docker-compose.production.yml
git commit -m "feat: add stripe dependency and env vars"
```

---

### Task 2: Database Migration — Products and Access Grants

**Files:**
- Create: `docker/wordpress/migrations/011-digital-products.sh`

**Step 1: Write the migration script**

Create `docker/wordpress/migrations/011-digital-products.sh`:

```bash
#!/bin/bash
set -e

echo "[Migration 011] Adding digital products and access grants..."

wp db query "
CREATE TABLE IF NOT EXISTS articulate_products (
  id BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  organization_id BIGINT(20) UNSIGNED NULL,
  created_by BIGINT(20) UNSIGNED NOT NULL,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  price_cents INT UNSIGNED NOT NULL DEFAULT 0 COMMENT 'Price in smallest currency unit',
  currency VARCHAR(3) NOT NULL DEFAULT 'usd',
  stripe_price_id VARCHAR(255) NULL COMMENT 'Stripe Price object ID',
  stripe_product_id VARCHAR(255) NULL COMMENT 'Stripe Product object ID',
  content_ids JSON NULL COMMENT 'WP post/page IDs this grants access to',
  file_path VARCHAR(500) NULL COMMENT 'Path or URL to downloadable file',
  file_name VARCHAR(255) NULL COMMENT 'Original filename for download',
  access_duration_days INT NULL COMMENT 'NULL = permanent access',
  download_limit INT NULL COMMENT 'NULL = unlimited downloads',
  is_active TINYINT(1) DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_org (organization_id),
  KEY idx_created_by (created_by),
  KEY idx_active (is_active),
  KEY idx_stripe_product (stripe_product_id),
  CONSTRAINT fk_product_creator FOREIGN KEY (created_by) REFERENCES articulate_users_auth(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
" --allow-root

echo "✓ Created articulate_products table"

wp db query "
CREATE TABLE IF NOT EXISTS articulate_access_grants (
  id BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  product_id BIGINT(20) UNSIGNED NOT NULL,
  customer_email VARCHAR(255) NOT NULL,
  customer_name VARCHAR(255) NULL,
  user_id BIGINT(20) UNSIGNED NULL COMMENT 'Linked Articulate user if registered',
  access_token VARCHAR(64) NOT NULL COMMENT 'Unique token for content access',
  stripe_session_id VARCHAR(255) NULL,
  stripe_payment_intent_id VARCHAR(255) NULL,
  amount_paid INT UNSIGNED NOT NULL DEFAULT 0,
  currency VARCHAR(3) NOT NULL DEFAULT 'usd',
  download_count INT UNSIGNED NOT NULL DEFAULT 0,
  download_limit INT UNSIGNED NULL COMMENT 'NULL = unlimited, inherited from product',
  expires_at DATETIME NULL COMMENT 'NULL = permanent',
  revoked_at DATETIME NULL COMMENT 'Admin can revoke access',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  last_accessed_at DATETIME NULL,
  PRIMARY KEY (id),
  UNIQUE KEY unique_token (access_token),
  KEY idx_product (product_id),
  KEY idx_email (customer_email),
  KEY idx_user (user_id),
  KEY idx_stripe_session (stripe_session_id),
  KEY idx_active (revoked_at, expires_at),
  CONSTRAINT fk_grant_product FOREIGN KEY (product_id) REFERENCES articulate_products(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
" --allow-root

echo "✓ Created articulate_access_grants table"

wp db query "
CREATE TABLE IF NOT EXISTS articulate_stripe_events (
  id BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  event_id VARCHAR(255) NOT NULL COMMENT 'Stripe event ID for idempotency',
  event_type VARCHAR(100) NOT NULL,
  payload JSON NULL,
  processed TINYINT(1) DEFAULT 0,
  processed_at DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY unique_event (event_id),
  KEY idx_type (event_type),
  KEY idx_processed (processed)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
" --allow-root

echo "✓ Created articulate_stripe_events table"

echo "[Migration 011] ✅ Digital products migration completed successfully"
```

**Step 2: Make the migration executable**

```bash
chmod +x docker/wordpress/migrations/011-digital-products.sh
```

**Step 3: Run the migration**

```bash
docker exec articulate-wordpress bash -c "cd /var/www/html && bash /tmp/migrations/011-digital-products.sh"
```

If the migrations directory is not mounted, run directly:

```bash
docker cp docker/wordpress/migrations/011-digital-products.sh articulate-wordpress:/tmp/011-digital-products.sh
docker exec articulate-wordpress bash -c "cd /var/www/html && bash /tmp/011-digital-products.sh"
```

Expected: Three "✓ Created" messages and final "✅ completed" message.

**Step 4: Verify tables exist**

```bash
docker exec articulate-db mariadb -u wpuser -pwppassword wordpress -e "SHOW TABLES LIKE 'articulate_%';"
```

Expected: `articulate_products`, `articulate_access_grants`, `articulate_stripe_events` appear in the list.

**Step 5: Commit**

```bash
git add docker/wordpress/migrations/011-digital-products.sh
git commit -m "feat: add database tables for digital products and access grants"
```

---

### Task 3: ProductManager Service

**Files:**
- Create: `mcp-server/src/articulate_mcp/product_manager.py`
- Test: `mcp-server/tests/test_product_manager.py`

**Step 1: Write the failing test**

Create `mcp-server/tests/test_product_manager.py`:

```python
"""Tests for ProductManager."""

import pytest
from tests.conftest import requires_db
from articulate_mcp.database import db

pytestmark = requires_db


@pytest.mark.asyncio
async def test_create_product(setup_db):
    """Test creating a digital product."""
    from articulate_mcp.product_manager import ProductManager

    # Create a test user first
    await db.execute(
        "DELETE FROM articulate_users_auth WHERE email = %s",
        ("product-test@example.com",),
    )
    user_id = await db.insert(
        """INSERT INTO articulate_users_auth (email, password_hash, name, email_verified)
           VALUES (%s, %s, %s, TRUE)""",
        ("product-test@example.com", "fakehash", "Test User"),
    )

    try:
        product = await ProductManager.create_product(
            name="Test Ebook",
            price_cents=1999,
            currency="usd",
            created_by=user_id,
            description="A test digital product",
            content_ids=[1, 2, 3],
        )

        assert product["id"] > 0
        assert product["name"] == "Test Ebook"
        assert product["price_cents"] == 1999
        assert product["currency"] == "usd"
        assert product["content_ids"] == [1, 2, 3]
        assert product["is_active"] is True

        # Fetch it back
        fetched = await ProductManager.get_product(product["id"])
        assert fetched is not None
        assert fetched["name"] == "Test Ebook"

        # List products
        products = await ProductManager.list_products(created_by=user_id)
        assert len(products) >= 1
        assert any(p["id"] == product["id"] for p in products)
    finally:
        await db.execute("DELETE FROM articulate_products WHERE created_by = %s", (user_id,))
        await db.execute(
            "DELETE FROM articulate_users_auth WHERE email = %s",
            ("product-test@example.com",),
        )


@pytest.mark.asyncio
async def test_create_and_validate_access_grant(setup_db):
    """Test creating an access grant and validating its token."""
    from articulate_mcp.product_manager import ProductManager

    await db.execute(
        "DELETE FROM articulate_users_auth WHERE email = %s",
        ("grant-test@example.com",),
    )
    user_id = await db.insert(
        """INSERT INTO articulate_users_auth (email, password_hash, name, email_verified)
           VALUES (%s, %s, %s, TRUE)""",
        ("grant-test@example.com", "fakehash", "Grant Tester"),
    )

    try:
        product = await ProductManager.create_product(
            name="Grant Test Product",
            price_cents=500,
            created_by=user_id,
            content_ids=[10, 20],
        )

        grant = await ProductManager.create_access_grant(
            product_id=product["id"],
            customer_email="buyer@example.com",
            customer_name="Buyer",
            amount_paid=500,
        )

        assert grant["access_token"]
        assert len(grant["access_token"]) == 48
        assert grant["customer_email"] == "buyer@example.com"

        # Validate the token
        validated = await ProductManager.validate_access_token(grant["access_token"])
        assert validated is not None
        assert validated["product_id"] == product["id"]
        assert validated["content_ids"] == [10, 20]

        # Revoke and re-validate
        await ProductManager.revoke_access(grant["id"])
        revoked = await ProductManager.validate_access_token(grant["access_token"])
        assert revoked is None
    finally:
        await db.execute(
            "DELETE FROM articulate_access_grants WHERE customer_email = %s",
            ("buyer@example.com",),
        )
        await db.execute("DELETE FROM articulate_products WHERE created_by = %s", (user_id,))
        await db.execute(
            "DELETE FROM articulate_users_auth WHERE email = %s",
            ("grant-test@example.com",),
        )
```

**Step 2: Run test to verify it fails**

```bash
cd /home/xyzzy/wp-ai && python -m pytest mcp-server/tests/test_product_manager.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'articulate_mcp.product_manager'`

**Step 3: Write ProductManager implementation**

Create `mcp-server/src/articulate_mcp/product_manager.py`:

```python
"""Product and access grant management for digital file sales."""

from __future__ import annotations

import json
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from articulate_mcp.database import db

logger = logging.getLogger(__name__)


class ProductManager:
    """Manages digital products and customer access grants."""

    @staticmethod
    async def create_product(
        name: str,
        price_cents: int,
        created_by: int,
        currency: str = "usd",
        description: str = "",
        content_ids: list[int] | None = None,
        file_path: str | None = None,
        file_name: str | None = None,
        access_duration_days: int | None = None,
        download_limit: int | None = None,
        organization_id: int | None = None,
        stripe_price_id: str | None = None,
        stripe_product_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new digital product.

        Args:
            name: Product display name.
            price_cents: Price in smallest currency unit (e.g., 1999 = $19.99).
            created_by: User ID of the product creator.
            currency: ISO 4217 currency code (default "usd").
            description: Product description.
            content_ids: List of WordPress post/page IDs this product grants access to.
            file_path: Path or URL to the downloadable file.
            file_name: Original filename for downloads.
            access_duration_days: Days access lasts (None = permanent).
            download_limit: Max downloads per customer (None = unlimited).
            organization_id: Org that owns this product.
            stripe_price_id: Stripe Price ID if already created.
            stripe_product_id: Stripe Product ID if already created.

        Returns:
            Created product dict with id and all fields.
        """
        product_id = await db.insert(
            """INSERT INTO articulate_products
               (name, description, price_cents, currency, stripe_price_id,
                stripe_product_id, content_ids, file_path, file_name,
                access_duration_days, download_limit, organization_id, created_by)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                name,
                description,
                price_cents,
                currency,
                stripe_price_id,
                stripe_product_id,
                json.dumps(content_ids) if content_ids else None,
                file_path,
                file_name,
                access_duration_days,
                download_limit,
                organization_id,
                created_by,
            ),
        )

        return await ProductManager.get_product(product_id)  # type: ignore[return-value]

    @staticmethod
    async def get_product(product_id: int) -> Optional[dict[str, Any]]:
        """Get a product by ID."""
        row = await db.fetchone(
            "SELECT * FROM articulate_products WHERE id = %s", (product_id,)
        )
        if not row:
            return None
        return ProductManager._format_product(row)

    @staticmethod
    async def list_products(
        created_by: int | None = None,
        organization_id: int | None = None,
        active_only: bool = True,
    ) -> list[dict[str, Any]]:
        """List products with optional filters."""
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

        where = " AND ".join(conditions) if conditions else "1=1"
        rows = await db.fetchall(
            f"SELECT * FROM articulate_products WHERE {where} ORDER BY created_at DESC",
            tuple(params),
        )
        return [ProductManager._format_product(r) for r in rows]

    @staticmethod
    async def update_product(
        product_id: int, **kwargs: Any
    ) -> Optional[dict[str, Any]]:
        """Update product fields. Only provided kwargs are updated."""
        allowed = {
            "name", "description", "price_cents", "currency",
            "content_ids", "file_path", "file_name",
            "access_duration_days", "download_limit", "is_active",
            "stripe_price_id", "stripe_product_id",
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return await ProductManager.get_product(product_id)

        if "content_ids" in updates:
            updates["content_ids"] = json.dumps(updates["content_ids"])

        set_clause = ", ".join(f"{k} = %s" for k in updates)
        values = list(updates.values()) + [product_id]
        await db.execute(
            f"UPDATE articulate_products SET {set_clause} WHERE id = %s",
            tuple(values),
        )
        return await ProductManager.get_product(product_id)

    @staticmethod
    async def create_access_grant(
        product_id: int,
        customer_email: str,
        customer_name: str | None = None,
        amount_paid: int = 0,
        currency: str = "usd",
        stripe_session_id: str | None = None,
        stripe_payment_intent_id: str | None = None,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        """Create a unique access grant for a customer.

        Generates a cryptographically secure 48-char token.

        Args:
            product_id: The product being purchased.
            customer_email: Buyer's email address.
            customer_name: Buyer's name (optional).
            amount_paid: Amount paid in smallest currency unit.
            currency: Payment currency.
            stripe_session_id: Stripe Checkout Session ID.
            stripe_payment_intent_id: Stripe PaymentIntent ID.
            user_id: Linked Articulate user ID (optional).

        Returns:
            Access grant dict with the unique access_token.
        """
        token = secrets.token_urlsafe(36)  # 48 chars

        # Get product to determine expiry and download limits
        product = await ProductManager.get_product(product_id)
        expires_at = None
        download_limit = None
        if product:
            if product.get("access_duration_days"):
                expires_at = datetime.now(timezone.utc) + timedelta(
                    days=product["access_duration_days"]
                )
            download_limit = product.get("download_limit")

        grant_id = await db.insert(
            """INSERT INTO articulate_access_grants
               (product_id, customer_email, customer_name, user_id,
                access_token, stripe_session_id, stripe_payment_intent_id,
                amount_paid, currency, download_limit, expires_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                product_id,
                customer_email,
                customer_name,
                user_id,
                token,
                stripe_session_id,
                stripe_payment_intent_id,
                amount_paid,
                currency,
                download_limit,
                expires_at,
            ),
        )

        grant = await db.fetchone(
            "SELECT * FROM articulate_access_grants WHERE id = %s", (grant_id,)
        )
        return ProductManager._format_grant(grant)  # type: ignore[arg-type]

    @staticmethod
    async def validate_access_token(token: str) -> Optional[dict[str, Any]]:
        """Validate an access token and return grant + product info if valid.

        Checks: token exists, not revoked, not expired, within download limit.

        Returns:
            Dict with grant info and content_ids if valid, None otherwise.
        """
        row = await db.fetchone(
            """SELECT g.*, p.content_ids, p.file_path, p.file_name, p.name AS product_name
               FROM articulate_access_grants g
               JOIN articulate_products p ON g.product_id = p.id
               WHERE g.access_token = %s
                 AND g.revoked_at IS NULL""",
            (token,),
        )

        if not row:
            return None

        # Check expiry
        if row.get("expires_at"):
            expires = row["expires_at"]
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires < datetime.now(timezone.utc):
                return None

        # Check download limit
        if row.get("download_limit") is not None:
            if row["download_count"] >= row["download_limit"]:
                return None

        # Parse content_ids
        content_ids = row.get("content_ids")
        if isinstance(content_ids, str):
            content_ids = json.loads(content_ids)

        return {
            "grant_id": row["id"],
            "product_id": row["product_id"],
            "product_name": row.get("product_name"),
            "customer_email": row["customer_email"],
            "content_ids": content_ids or [],
            "file_path": row.get("file_path"),
            "file_name": row.get("file_name"),
            "download_count": row["download_count"],
            "download_limit": row.get("download_limit"),
            "expires_at": row["expires_at"].isoformat() if row.get("expires_at") else None,
        }

    @staticmethod
    async def record_download(grant_id: int) -> None:
        """Increment download count and update last_accessed_at."""
        await db.execute(
            """UPDATE articulate_access_grants
               SET download_count = download_count + 1,
                   last_accessed_at = NOW()
               WHERE id = %s""",
            (grant_id,),
        )

    @staticmethod
    async def revoke_access(grant_id: int) -> None:
        """Revoke an access grant."""
        await db.execute(
            "UPDATE articulate_access_grants SET revoked_at = NOW() WHERE id = %s",
            (grant_id,),
        )

    @staticmethod
    async def list_grants_for_product(product_id: int) -> list[dict[str, Any]]:
        """List all access grants for a product."""
        rows = await db.fetchall(
            """SELECT * FROM articulate_access_grants
               WHERE product_id = %s ORDER BY created_at DESC""",
            (product_id,),
        )
        return [ProductManager._format_grant(r) for r in rows]

    @staticmethod
    async def list_grants_for_customer(email: str) -> list[dict[str, Any]]:
        """List all access grants for a customer email."""
        rows = await db.fetchall(
            """SELECT g.*, p.name AS product_name
               FROM articulate_access_grants g
               JOIN articulate_products p ON g.product_id = p.id
               WHERE g.customer_email = %s
               ORDER BY g.created_at DESC""",
            (email,),
        )
        return [ProductManager._format_grant(r) for r in rows]

    @staticmethod
    def _format_product(row: dict[str, Any]) -> dict[str, Any]:
        """Format a product row for API response."""
        content_ids = row.get("content_ids")
        if isinstance(content_ids, str):
            content_ids = json.loads(content_ids)

        return {
            "id": row["id"],
            "name": row["name"],
            "description": row.get("description", ""),
            "price_cents": row["price_cents"],
            "currency": row.get("currency", "usd"),
            "stripe_price_id": row.get("stripe_price_id"),
            "stripe_product_id": row.get("stripe_product_id"),
            "content_ids": content_ids or [],
            "file_path": row.get("file_path"),
            "file_name": row.get("file_name"),
            "access_duration_days": row.get("access_duration_days"),
            "download_limit": row.get("download_limit"),
            "organization_id": row.get("organization_id"),
            "created_by": row["created_by"],
            "is_active": bool(row.get("is_active", True)),
            "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        }

    @staticmethod
    def _format_grant(row: dict[str, Any]) -> dict[str, Any]:
        """Format an access grant row for API response."""
        return {
            "id": row["id"],
            "product_id": row["product_id"],
            "product_name": row.get("product_name"),
            "customer_email": row["customer_email"],
            "customer_name": row.get("customer_name"),
            "user_id": row.get("user_id"),
            "access_token": row["access_token"],
            "stripe_session_id": row.get("stripe_session_id"),
            "amount_paid": row.get("amount_paid", 0),
            "currency": row.get("currency", "usd"),
            "download_count": row.get("download_count", 0),
            "download_limit": row.get("download_limit"),
            "expires_at": row["expires_at"].isoformat() if row.get("expires_at") else None,
            "revoked_at": row["revoked_at"].isoformat() if row.get("revoked_at") else None,
            "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
            "last_accessed_at": (
                row["last_accessed_at"].isoformat() if row.get("last_accessed_at") else None
            ),
        }
```

**Step 4: Run test to verify it passes**

```bash
cd /home/xyzzy/wp-ai && python -m pytest mcp-server/tests/test_product_manager.py -v
```

Expected: 2 tests PASS.

**Step 5: Commit**

```bash
git add mcp-server/src/articulate_mcp/product_manager.py mcp-server/tests/test_product_manager.py
git commit -m "feat: add ProductManager for digital products and access grants"
```

---

### Task 4: Stripe Payment Routes

**Files:**
- Create: `mcp-server/src/articulate_mcp/routes/payments.py`
- Modify: `mcp-server/src/articulate_mcp/server.py` (add route registrations)

**Step 1: Write the payment routes**

Create `mcp-server/src/articulate_mcp/routes/payments.py`:

```python
"""Stripe payment routes for digital product sales."""

from __future__ import annotations

import json
import logging
import os

import stripe
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from articulate_mcp.database import db
from articulate_mcp.product_manager import ProductManager
from articulate_mcp.user_manager import UserManager
from articulate_mcp.email_service import send_access_token_email

logger = logging.getLogger(__name__)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
APP_URL = os.getenv("APP_URL", "https://app.ragbaz.xyz")


async def create_checkout_endpoint(request: Request) -> JSONResponse:
    """Create a Stripe Checkout Session for a product.

    POST /payments/checkout
    Body: { "product_id": int }

    Returns: { "checkout_url": str, "session_id": str }
    """
    try:
        data = await request.json()
        product_id = data.get("product_id")

        if not product_id:
            return JSONResponse({"error": "product_id required"}, status_code=400)

        product = await ProductManager.get_product(product_id)
        if not product or not product["is_active"]:
            return JSONResponse({"error": "Product not found"}, status_code=404)

        if not stripe.api_key:
            return JSONResponse(
                {"error": "Stripe not configured"}, status_code=503
            )

        session = stripe.checkout.Session.create(
            line_items=[
                {
                    "price_data": {
                        "currency": product["currency"],
                        "product_data": {
                            "name": product["name"],
                            "description": product.get("description", ""),
                        },
                        "unit_amount": product["price_cents"],
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=f"{APP_URL}/purchase/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{APP_URL}/purchase/cancel",
            metadata={
                "product_id": str(product["id"]),
            },
        )

        return JSONResponse(
            {"checkout_url": session.url, "session_id": session.id}
        )

    except stripe.StripeError as e:
        logger.error("Stripe error creating checkout: %s", e)
        return JSONResponse({"error": str(e)}, status_code=502)
    except Exception as e:
        logger.error("Error creating checkout: %s", e)
        return JSONResponse({"error": "Failed to create checkout"}, status_code=500)


async def stripe_webhook_endpoint(request: Request) -> Response:
    """Handle Stripe webhook events.

    POST /payments/webhook
    No auth required — verified by Stripe signature.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if not WEBHOOK_SECRET:
        logger.error("STRIPE_WEBHOOK_SECRET not configured")
        return Response(status_code=500)

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, WEBHOOK_SECRET
        )
    except ValueError:
        logger.warning("Invalid webhook payload")
        return Response(status_code=400)
    except stripe.SignatureVerificationError:
        logger.warning("Invalid webhook signature")
        return Response(status_code=400)

    # Idempotency: skip already-processed events
    existing = await db.fetchone(
        "SELECT id FROM articulate_stripe_events WHERE event_id = %s",
        (event["id"],),
    )
    if existing:
        logger.info("Skipping duplicate event: %s", event["id"])
        return Response(status_code=200)

    # Store the event
    await db.insert(
        """INSERT INTO articulate_stripe_events (event_id, event_type, payload)
           VALUES (%s, %s, %s)""",
        (event["id"], event["type"], json.dumps(event["data"])),
    )

    # Process checkout.session.completed
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        await _handle_checkout_completed(session, event["id"])

    return Response(status_code=200)


async def _handle_checkout_completed(session: dict, event_id: str) -> None:
    """Fulfill a completed checkout session."""
    product_id_str = session.get("metadata", {}).get("product_id")
    if not product_id_str:
        logger.error("Checkout session missing product_id metadata: %s", session["id"])
        return

    product_id = int(product_id_str)
    customer_email = session.get("customer_details", {}).get("email", "")
    customer_name = session.get("customer_details", {}).get("name", "")
    amount_paid = session.get("amount_total", 0)
    currency = session.get("currency", "usd")

    if not customer_email:
        logger.error("Checkout session missing customer email: %s", session["id"])
        return

    # Create the access grant
    grant = await ProductManager.create_access_grant(
        product_id=product_id,
        customer_email=customer_email,
        customer_name=customer_name,
        amount_paid=amount_paid,
        currency=currency,
        stripe_session_id=session["id"],
        stripe_payment_intent_id=session.get("payment_intent"),
    )

    logger.info(
        "Access grant created: product=%d, customer=%s, token=%s...",
        product_id,
        customer_email,
        grant["access_token"][:8],
    )

    # Send access email
    product = await ProductManager.get_product(product_id)
    product_name = product["name"] if product else "Digital Product"
    send_access_token_email(
        to=customer_email,
        name=customer_name,
        product_name=product_name,
        access_token=grant["access_token"],
    )

    # Mark event as processed
    await db.execute(
        "UPDATE articulate_stripe_events SET processed = 1, processed_at = NOW() WHERE event_id = %s",
        (event_id,),
    )


async def check_session_endpoint(request: Request) -> JSONResponse:
    """Check the status of a Stripe Checkout Session.

    GET /payments/session/{session_id}

    Returns grant info if payment completed.
    """
    session_id = request.path_params.get("session_id", "")
    if not session_id:
        return JSONResponse({"error": "session_id required"}, status_code=400)

    grant = await db.fetchone(
        """SELECT g.*, p.name AS product_name
           FROM articulate_access_grants g
           JOIN articulate_products p ON g.product_id = p.id
           WHERE g.stripe_session_id = %s""",
        (session_id,),
    )

    if grant:
        return JSONResponse({
            "status": "completed",
            "product_name": grant.get("product_name"),
            "access_token": grant["access_token"],
            "customer_email": grant["customer_email"],
        })

    return JSONResponse({"status": "pending"})


async def validate_token_endpoint(request: Request) -> JSONResponse:
    """Validate an access token and return accessible content IDs.

    POST /payments/validate-token
    Body: { "token": str }

    Returns: { "valid": bool, "content_ids": [...], "product_name": str }
    """
    try:
        data = await request.json()
        token = data.get("token", "").strip()

        if not token:
            return JSONResponse({"error": "token required"}, status_code=400)

        result = await ProductManager.validate_access_token(token)

        if result is None:
            return JSONResponse({"valid": False})

        return JSONResponse({
            "valid": True,
            "product_name": result.get("product_name"),
            "content_ids": result.get("content_ids", []),
            "file_path": result.get("file_path"),
            "file_name": result.get("file_name"),
            "download_count": result.get("download_count", 0),
            "download_limit": result.get("download_limit"),
            "expires_at": result.get("expires_at"),
        })
    except Exception as e:
        logger.error("Token validation error: %s", e)
        return JSONResponse({"error": "Validation failed"}, status_code=500)


async def list_products_public_endpoint(request: Request) -> JSONResponse:
    """List active products (public, no auth required).

    GET /payments/products
    """
    products = await ProductManager.list_products(active_only=True)
    # Strip internal fields for public listing
    public = [
        {
            "id": p["id"],
            "name": p["name"],
            "description": p.get("description", ""),
            "price_cents": p["price_cents"],
            "currency": p["currency"],
        }
        for p in products
    ]
    return JSONResponse(public)
```

**Step 2: Add access token email to email_service.py**

Add to `mcp-server/src/articulate_mcp/email_service.py`:

```python
def send_access_token_email(
    to: str, name: str, product_name: str, access_token: str
) -> bool:
    """Send access token email after purchase."""
    access_url = f"{APP_URL}/access?token={access_token}"
    subject = f"Your access to {product_name}"

    html = f"""
    <div style="font-family:system-ui,sans-serif;max-width:560px;margin:0 auto;padding:32px">
      <h2 style="margin:0 0 16px">Thank you for your purchase{', ' + name if name else ''}!</h2>
      <p style="color:#555;line-height:1.6">
        You now have access to <strong>{product_name}</strong>.
      </p>
      <p style="margin:24px 0">
        <a href="{access_url}"
           style="background:#18181b;color:#fff;padding:12px 24px;border-radius:6px;
                  text-decoration:none;display:inline-block;font-weight:500">
          Access Your Content
        </a>
      </p>
      <p style="color:#888;font-size:13px">
        Your personal access token: <code>{access_token}</code><br>
        Keep this safe — it is your unique key to the content.
      </p>
    </div>
    """

    text = (
        f"Thank you for your purchase{', ' + name if name else ''}!\n\n"
        f"You now have access to {product_name}.\n\n"
        f"Access your content: {access_url}\n\n"
        f"Your personal access token: {access_token}\n"
        "Keep this safe — it is your unique key to the content."
    )

    return _send(to, subject, html, text)
```

**Step 3: Register routes in server.py**

In `mcp-server/src/articulate_mcp/server.py`, add the imports and route registrations.

Add import near other route imports:

```python
from articulate_mcp.routes.payments import (
    create_checkout_endpoint,
    stripe_webhook_endpoint,
    check_session_endpoint,
    validate_token_endpoint,
    list_products_public_endpoint,
)
```

Add routes to `mcp._app.routes.extend([...])`:

```python
    # Payments (Stripe)
    Route("/payments/products", list_products_public_endpoint, methods=["GET"]),
    Route("/payments/checkout", create_checkout_endpoint, methods=["POST"]),
    Route("/payments/webhook", stripe_webhook_endpoint, methods=["POST"]),
    Route("/payments/session/{session_id}", check_session_endpoint, methods=["GET"]),
    Route("/payments/validate-token", validate_token_endpoint, methods=["POST"]),
```

**Step 4: Add payment paths to auth middleware public paths**

In `mcp-server/src/articulate_mcp/middleware/auth.py`, add to `public_paths`:

```python
    "/payments/webhook",         # Stripe webhook (verified by signature)
    "/payments/products",        # Public product listing
    "/payments/validate-token",  # Token validation (no user session needed)
    "/payments/session/",        # Check session status (no user session needed)
```

**Step 5: Commit**

```bash
git add mcp-server/src/articulate_mcp/routes/payments.py \
        mcp-server/src/articulate_mcp/email_service.py \
        mcp-server/src/articulate_mcp/server.py \
        mcp-server/src/articulate_mcp/middleware/auth.py
git commit -m "feat: add Stripe payment routes and webhook handler"
```

---

### Task 5: MCP Tools for Product Management

**Files:**
- Create: `mcp-server/src/articulate_mcp/tools/products.py`
- Modify: `mcp-server/src/articulate_mcp/server.py` (register tools)

**Step 1: Write product management tools**

Create `mcp-server/src/articulate_mcp/tools/products.py`:

```python
"""MCP tools for managing digital products and access grants."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from articulate_mcp.product_manager import ProductManager
from articulate_mcp.context_helper import get_connection_info


def register(mcp: FastMCP) -> None:
    """Register product management tools with the MCP server."""

    @mcp.tool()
    async def create_product(
        name: str,
        price_cents: int,
        description: str = "",
        content_ids: list[int] | None = None,
        file_path: str | None = None,
        file_name: str | None = None,
        access_duration_days: int | None = None,
        download_limit: int | None = None,
        currency: str = "usd",
        context: dict | None = None,
    ) -> dict[str, Any]:
        """Create a digital product for sale.

        Args:
            name: Product display name.
            price_cents: Price in smallest currency unit (e.g., 1999 = $19.99).
            description: Product description.
            content_ids: WordPress post/page IDs this product grants access to.
            file_path: Path or URL to the downloadable file.
            file_name: Original filename for downloads.
            access_duration_days: Days access lasts after purchase (omit for permanent).
            download_limit: Max downloads per customer (omit for unlimited).
            currency: ISO 4217 currency code (default "usd").

        Returns:
            The created product with its ID and all fields.
        """
        _, user_id = get_connection_info(context)
        return await ProductManager.create_product(
            name=name,
            price_cents=price_cents,
            created_by=user_id,
            currency=currency,
            description=description,
            content_ids=content_ids,
            file_path=file_path,
            file_name=file_name,
            access_duration_days=access_duration_days,
            download_limit=download_limit,
        )

    @mcp.tool()
    async def list_products(
        active_only: bool = True,
        context: dict | None = None,
    ) -> list[dict[str, Any]]:
        """List digital products.

        Args:
            active_only: Only show active products (default True).

        Returns:
            List of product objects.
        """
        _, user_id = get_connection_info(context)
        return await ProductManager.list_products(
            created_by=user_id, active_only=active_only
        )

    @mcp.tool()
    async def get_product(
        product_id: int,
        context: dict | None = None,
    ) -> dict[str, Any]:
        """Get a digital product by ID.

        Args:
            product_id: The product database ID.

        Returns:
            Product object or error.
        """
        product = await ProductManager.get_product(product_id)
        if not product:
            return {"error": f"Product {product_id} not found"}
        return product

    @mcp.tool()
    async def update_product(
        product_id: int,
        name: str | None = None,
        description: str | None = None,
        price_cents: int | None = None,
        content_ids: list[int] | None = None,
        is_active: bool | None = None,
        context: dict | None = None,
    ) -> dict[str, Any]:
        """Update a digital product.

        Args:
            product_id: The product database ID.
            name: New product name.
            description: New description.
            price_cents: New price in smallest currency unit.
            content_ids: New list of WordPress content IDs to grant access to.
            is_active: Enable or disable the product.

        Returns:
            Updated product object.
        """
        kwargs: dict[str, Any] = {}
        if name is not None:
            kwargs["name"] = name
        if description is not None:
            kwargs["description"] = description
        if price_cents is not None:
            kwargs["price_cents"] = price_cents
        if content_ids is not None:
            kwargs["content_ids"] = content_ids
        if is_active is not None:
            kwargs["is_active"] = is_active

        result = await ProductManager.update_product(product_id, **kwargs)
        if not result:
            return {"error": f"Product {product_id} not found"}
        return result

    @mcp.tool()
    async def list_access_grants(
        product_id: int | None = None,
        customer_email: str | None = None,
        context: dict | None = None,
    ) -> list[dict[str, Any]]:
        """List access grants for a product or customer.

        Args:
            product_id: Filter by product ID.
            customer_email: Filter by customer email.

        Returns:
            List of access grant objects.
        """
        if product_id:
            return await ProductManager.list_grants_for_product(product_id)
        if customer_email:
            return await ProductManager.list_grants_for_customer(customer_email)
        return {"error": "Provide product_id or customer_email"}  # type: ignore[return-value]

    @mcp.tool()
    async def grant_access(
        product_id: int,
        customer_email: str,
        customer_name: str = "",
        context: dict | None = None,
    ) -> dict[str, Any]:
        """Manually grant access to a product (no payment required).

        Use this to give free access to specific customers.

        Args:
            product_id: The product to grant access to.
            customer_email: Customer's email address.
            customer_name: Customer's name.

        Returns:
            Access grant with the unique token.
        """
        from articulate_mcp.email_service import send_access_token_email

        grant = await ProductManager.create_access_grant(
            product_id=product_id,
            customer_email=customer_email,
            customer_name=customer_name,
        )

        product = await ProductManager.get_product(product_id)
        product_name = product["name"] if product else "Digital Product"
        send_access_token_email(
            to=customer_email,
            name=customer_name,
            product_name=product_name,
            access_token=grant["access_token"],
        )

        return grant

    @mcp.tool()
    async def revoke_access(
        grant_id: int,
        context: dict | None = None,
    ) -> dict[str, Any]:
        """Revoke a customer's access grant.

        Args:
            grant_id: The access grant database ID.

        Returns:
            Confirmation of revocation.
        """
        await ProductManager.revoke_access(grant_id)
        return {"success": True, "grant_id": grant_id, "status": "revoked"}
```

**Step 2: Register tools in server.py**

In `mcp-server/src/articulate_mcp/server.py`, add to the tool registration section (around line 136-154):

```python
from articulate_mcp.tools import products as product_tools
product_tools.register(mcp)
```

**Step 3: Commit**

```bash
git add mcp-server/src/articulate_mcp/tools/products.py \
        mcp-server/src/articulate_mcp/server.py
git commit -m "feat: add MCP tools for product and access grant management"
```

---

### Task 6: Next.js API Routes for Payments

**Files:**
- Create: `web/src/app/api/payments/checkout/route.ts`
- Create: `web/src/app/api/payments/products/route.ts`
- Create: `web/src/app/api/payments/session/[sessionId]/route.ts`
- Create: `web/src/app/api/payments/validate-token/route.ts`
- Create: `web/src/app/api/payments/webhook/route.ts`

**Step 1: Create the checkout route**

Create `web/src/app/api/payments/checkout/route.ts`:

```typescript
import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const MCP_SERVER_URL = process.env.MCP_SERVER_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
  try {
    const cookieStore = await cookies();
    const sessionCookie = cookieStore.get("session");
    if (!sessionCookie) {
      return NextResponse.json({ error: "Authentication required" }, { status: 401 });
    }

    const body = await request.json();

    const response = await fetch(`${MCP_SERVER_URL}/payments/checkout`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Session-ID": sessionCookie.value,
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error("Checkout error:", error);
    return NextResponse.json({ error: "Failed to create checkout" }, { status: 500 });
  }
}
```

**Step 2: Create the products listing route**

Create `web/src/app/api/payments/products/route.ts`:

```typescript
import { NextResponse } from "next/server";

const MCP_SERVER_URL = process.env.MCP_SERVER_URL || "http://localhost:8000";

export async function GET() {
  try {
    const response = await fetch(`${MCP_SERVER_URL}/payments/products`);
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error("Products list error:", error);
    return NextResponse.json({ error: "Failed to list products" }, { status: 500 });
  }
}
```

**Step 3: Create the session check route**

Create `web/src/app/api/payments/session/[sessionId]/route.ts`:

```typescript
import { NextRequest, NextResponse } from "next/server";

const MCP_SERVER_URL = process.env.MCP_SERVER_URL || "http://localhost:8000";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  try {
    const { sessionId } = await params;
    const response = await fetch(`${MCP_SERVER_URL}/payments/session/${sessionId}`);
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error("Session check error:", error);
    return NextResponse.json({ error: "Failed to check session" }, { status: 500 });
  }
}
```

**Step 4: Create the token validation route**

Create `web/src/app/api/payments/validate-token/route.ts`:

```typescript
import { NextRequest, NextResponse } from "next/server";

const MCP_SERVER_URL = process.env.MCP_SERVER_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const response = await fetch(`${MCP_SERVER_URL}/payments/validate-token`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error("Token validation error:", error);
    return NextResponse.json({ error: "Validation failed" }, { status: 500 });
  }
}
```

**Step 5: Create the webhook route**

Create `web/src/app/api/payments/webhook/route.ts`:

```typescript
import { NextRequest, NextResponse } from "next/server";

const MCP_SERVER_URL = process.env.MCP_SERVER_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
  try {
    // Pass through raw body and Stripe signature to MCP server
    const body = await request.text();
    const sig = request.headers.get("stripe-signature") || "";

    const response = await fetch(`${MCP_SERVER_URL}/payments/webhook`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "stripe-signature": sig,
      },
      body,
    });

    return new NextResponse(null, { status: response.status });
  } catch (error) {
    console.error("Webhook relay error:", error);
    return new NextResponse(null, { status: 500 });
  }
}
```

**Step 6: Commit**

```bash
git add web/src/app/api/payments/
git commit -m "feat: add Next.js API routes for Stripe payments"
```

---

### Task 7: Access Page Frontend

**Files:**
- Create: `web/src/app/access/page.tsx`
- Create: `web/src/app/purchase/success/page.tsx`

**Step 1: Create the access page**

This page lets customers enter their access token to view protected content.

Create `web/src/app/access/page.tsx`:

```tsx
"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";

export default function AccessPage() {
  const searchParams = useSearchParams();
  const [token, setToken] = useState(searchParams.get("token") || "");
  const [result, setResult] = useState<{
    valid: boolean;
    product_name?: string;
    content_ids?: number[];
    file_path?: string;
    file_name?: string;
    download_count?: number;
    download_limit?: number | null;
    expires_at?: string | null;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Auto-validate if token in URL
  useEffect(() => {
    const urlToken = searchParams.get("token");
    if (urlToken) {
      validateToken(urlToken);
    }
  }, [searchParams]);

  async function validateToken(t: string) {
    if (!t.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch("/api/payments/validate-token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: t.trim() }),
      });
      const data = await response.json();

      if (data.error) {
        setError(data.error);
      } else {
        setResult(data);
      }
    } catch {
      setError("Failed to validate token");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold">Access Content</h1>
          <p className="text-muted-foreground mt-2">
            Enter your access token to view purchased content
          </p>
        </div>

        <div className="space-y-4">
          <input
            type="text"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && validateToken(token)}
            placeholder="Paste your access token..."
            className="w-full px-4 py-3 border rounded-lg bg-background text-sm
                       focus:outline-none focus:ring-2 focus:ring-primary"
          />
          <button
            onClick={() => validateToken(token)}
            disabled={loading || !token.trim()}
            className="w-full py-3 bg-primary text-primary-foreground rounded-lg
                       font-medium disabled:opacity-50"
          >
            {loading ? "Validating..." : "Access Content"}
          </button>
        </div>

        {error && (
          <div className="p-4 bg-destructive/10 text-destructive rounded-lg text-sm">
            {error}
          </div>
        )}

        {result && !result.valid && (
          <div className="p-4 bg-destructive/10 text-destructive rounded-lg text-sm">
            Invalid or expired token. Please check your token and try again.
          </div>
        )}

        {result && result.valid && (
          <div className="p-4 bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg space-y-3">
            <h2 className="font-semibold text-green-800 dark:text-green-200">
              Access Granted
            </h2>
            <p className="text-sm text-green-700 dark:text-green-300">
              <strong>{result.product_name}</strong>
            </p>
            {result.content_ids && result.content_ids.length > 0 && (
              <p className="text-sm text-green-600 dark:text-green-400">
                {result.content_ids.length} content item{result.content_ids.length !== 1 ? "s" : ""} available
              </p>
            )}
            {result.download_limit && (
              <p className="text-xs text-green-600 dark:text-green-400">
                Downloads: {result.download_count} / {result.download_limit}
              </p>
            )}
            {result.expires_at && (
              <p className="text-xs text-green-600 dark:text-green-400">
                Expires: {new Date(result.expires_at).toLocaleDateString()}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
```

**Step 2: Create the purchase success page**

Create `web/src/app/purchase/success/page.tsx`:

```tsx
"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";

export default function PurchaseSuccessPage() {
  const searchParams = useSearchParams();
  const sessionId = searchParams.get("session_id");
  const [status, setStatus] = useState<"loading" | "completed" | "pending">("loading");
  const [accessToken, setAccessToken] = useState("");
  const [productName, setProductName] = useState("");

  useEffect(() => {
    if (!sessionId) return;

    async function checkSession() {
      try {
        const response = await fetch(`/api/payments/session/${sessionId}`);
        const data = await response.json();

        if (data.status === "completed") {
          setStatus("completed");
          setAccessToken(data.access_token);
          setProductName(data.product_name);
        } else {
          setStatus("pending");
          // Retry after 3 seconds (webhook may still be processing)
          setTimeout(checkSession, 3000);
        }
      } catch {
        setStatus("pending");
      }
    }

    checkSession();
  }, [sessionId]);

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-md space-y-6 text-center">
        {status === "loading" && (
          <p className="text-muted-foreground">Processing your purchase...</p>
        )}

        {status === "pending" && (
          <div className="space-y-4">
            <h1 className="text-2xl font-bold">Payment Received</h1>
            <p className="text-muted-foreground">
              Your access is being set up. Check your email shortly for your
              access token.
            </p>
          </div>
        )}

        {status === "completed" && (
          <div className="space-y-4">
            <div className="text-4xl">&#10003;</div>
            <h1 className="text-2xl font-bold">Purchase Complete!</h1>
            <p className="text-muted-foreground">
              You now have access to <strong>{productName}</strong>.
            </p>
            <div className="p-4 bg-muted rounded-lg">
              <p className="text-xs text-muted-foreground mb-2">Your access token:</p>
              <code className="text-sm font-mono break-all">{accessToken}</code>
            </div>
            <p className="text-xs text-muted-foreground">
              This token has also been emailed to you.
            </p>
            <a
              href={`/access?token=${accessToken}`}
              className="inline-block py-3 px-6 bg-primary text-primary-foreground
                         rounded-lg font-medium"
            >
              Access Your Content
            </a>
          </div>
        )}
      </div>
    </div>
  );
}
```

**Step 3: Commit**

```bash
git add web/src/app/access/page.tsx web/src/app/purchase/success/page.tsx
git commit -m "feat: add access token entry page and purchase success page"
```

---

### Task 8: Build, Deploy, and End-to-End Test

**Step 1: Rebuild MCP server with stripe dependency**

```bash
docker compose -f docker-compose.production.yml build mcp-server
```

**Step 2: Rebuild frontend**

```bash
docker compose -f docker-compose.production.yml build webedit
```

**Step 3: Deploy**

```bash
docker compose -f docker-compose.production.yml up -d mcp-server webedit
```

**Step 4: Run the database migration**

```bash
docker cp docker/wordpress/migrations/011-digital-products.sh articulate-wordpress:/tmp/011-digital-products.sh
docker exec articulate-wordpress bash -c "cd /var/www/html && bash /tmp/011-digital-products.sh"
```

**Step 5: Verify tables**

```bash
docker exec articulate-db mariadb -u wpuser -pwppassword wordpress -e "DESCRIBE articulate_products;"
docker exec articulate-db mariadb -u wpuser -pwppassword wordpress -e "DESCRIBE articulate_access_grants;"
docker exec articulate-db mariadb -u wpuser -pwppassword wordpress -e "DESCRIBE articulate_stripe_events;"
```

Expected: All three tables described with correct columns.

**Step 6: Test product creation via API**

```bash
curl -s -b "session=<SESSION_ID>" -X POST \
  -H "Content-Type: application/json" \
  -d '{"product_id": 1}' \
  "https://app.ragbaz.xyz/api/payments/checkout"
```

Expected: Either `{"checkout_url": "...", "session_id": "..."}` (if Stripe configured) or `{"error": "Stripe not configured"}` (if env vars not set yet).

**Step 7: Test public product listing**

```bash
curl -s "https://app.ragbaz.xyz/api/payments/products"
```

Expected: `[]` (empty array — no products yet).

**Step 8: Test token validation**

```bash
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"token": "nonexistent"}' \
  "https://app.ragbaz.xyz/api/payments/validate-token"
```

Expected: `{"valid": false}`

**Step 9: Commit**

```bash
git add -A
git commit -m "feat: deploy digital file sales with Stripe integration"
```

---

### Task 9: Configure Stripe (Manual Setup)

This task is manual and requires Stripe Dashboard access.

**Step 1: Create Stripe account** (if not already done)

Go to https://dashboard.stripe.com and create/log in to your account.

**Step 2: Get API keys**

- Go to Developers > API keys
- Copy the **Secret key** (starts with `sk_test_` for test mode)
- Copy the **Publishable key** (starts with `pk_test_`)

**Step 3: Create webhook endpoint**

- Go to Developers > Webhooks > Add endpoint
- URL: `https://app.ragbaz.xyz/api/payments/webhook`
- Events to listen for: `checkout.session.completed`
- Copy the **Webhook signing secret** (starts with `whsec_`)

**Step 4: Add keys to environment**

Add to your `.env` file or deployment environment:

```bash
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

**Step 5: Restart MCP server**

```bash
docker compose -f docker-compose.production.yml up -d mcp-server
```

**Step 6: Test end-to-end with Stripe CLI (optional)**

```bash
# Install Stripe CLI and forward webhooks locally for testing
stripe listen --forward-to https://app.ragbaz.xyz/api/payments/webhook
stripe trigger checkout.session.completed
```

---

## Summary

| Task | What It Builds | Files |
|------|---------------|-------|
| 1 | Stripe dependency + env vars | `pyproject.toml`, `docker-compose.production.yml` |
| 2 | Database tables | `011-digital-products.sh` |
| 3 | ProductManager service + tests | `product_manager.py`, `test_product_manager.py` |
| 4 | Stripe payment routes + email | `routes/payments.py`, `email_service.py`, `server.py`, `auth.py` |
| 5 | MCP tools for product management | `tools/products.py`, `server.py` |
| 6 | Next.js API proxy routes | `web/src/app/api/payments/*` |
| 7 | Access + success frontend pages | `web/src/app/access/`, `web/src/app/purchase/success/` |
| 8 | Build, deploy, integration test | Docker rebuild + migration |
| 9 | Stripe Dashboard config | Manual setup |

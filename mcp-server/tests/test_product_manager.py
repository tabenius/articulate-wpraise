"""Integration tests for ProductManager."""

import pytest
from datetime import datetime, timedelta, timezone
from tests.conftest import requires_db

from articulate_mcp.database import db
from articulate_mcp.product_manager import ProductManager

pytestmark = requires_db


async def _create_test_user(email: str = "product-test@example.com") -> dict:
    """Create a minimal test user for product tests."""
    await db.execute(
        "DELETE FROM articulate_users_auth WHERE email = %s", (email,)
    )
    user_id = await db.insert(
        """
        INSERT INTO articulate_users_auth (email, password_hash, name, email_verified)
        VALUES (%s, %s, %s, TRUE)
        """,
        (email, "$2b$12$fakehashfortest", "Product Test User"),
    )
    return {"id": user_id, "email": email}


async def _cleanup_test_user(email: str = "product-test@example.com") -> None:
    """Remove test user and cascaded data."""
    await db.execute(
        "DELETE FROM articulate_users_auth WHERE email = %s", (email,)
    )


@pytest.mark.asyncio
async def test_create_product(setup_db):
    """Test creating a product, fetching it, and listing products."""
    user = await _create_test_user()
    try:
        # Create a product with all fields
        product = await ProductManager.create_product(
            name="Premium Course",
            price_cents=4999,
            created_by=user["id"],
            currency="usd",
            description="An amazing course",
            content_ids=[101, 202, 303],
            file_path="/downloads/course.zip",
            file_name="course.zip",
            access_duration_days=365,
            download_limit=5,
        )

        # Verify all returned fields
        assert product["id"] > 0
        assert product["name"] == "Premium Course"
        assert product["price_cents"] == 4999
        assert product["currency"] == "usd"
        assert product["description"] == "An amazing course"
        assert product["content_ids"] == [101, 202, 303]
        assert product["file_path"] == "/downloads/course.zip"
        assert product["file_name"] == "course.zip"
        assert product["access_duration_days"] == 365
        assert product["download_limit"] == 5
        assert product["is_active"] is True
        assert product["created_at"] is not None

        # Fetch the product back by ID
        fetched = await ProductManager.get_product(product["id"])
        assert fetched is not None
        assert fetched["name"] == "Premium Course"
        assert fetched["content_ids"] == [101, 202, 303]

        # List products by creator
        products = await ProductManager.list_products(created_by=user["id"])
        assert len(products) >= 1
        assert any(p["id"] == product["id"] for p in products)

        # Update the product
        updated = await ProductManager.update_product(
            product["id"],
            name="Updated Course",
            price_cents=5999,
        )
        assert updated is not None
        assert updated["name"] == "Updated Course"
        assert updated["price_cents"] == 5999

        # Deactivate and verify active_only filter works
        await ProductManager.update_product(product["id"], is_active=False)
        active_products = await ProductManager.list_products(
            created_by=user["id"], active_only=True
        )
        assert not any(p["id"] == product["id"] for p in active_products)

        all_products = await ProductManager.list_products(
            created_by=user["id"], active_only=False
        )
        assert any(p["id"] == product["id"] for p in all_products)

        # Non-existent product returns None
        assert await ProductManager.get_product(999999) is None

        # Cleanup
        await db.execute(
            "DELETE FROM articulate_products WHERE id = %s", (product["id"],)
        )
    finally:
        await _cleanup_test_user()


@pytest.mark.asyncio
async def test_create_and_validate_access_grant(setup_db):
    """Test creating a grant, validating the token, revoking, and re-validating."""
    user = await _create_test_user("grant-test@example.com")
    try:
        # Create a product with a download limit
        product = await ProductManager.create_product(
            name="E-Book Download",
            price_cents=1999,
            created_by=user["id"],
            content_ids=[42],
            download_limit=3,
            access_duration_days=30,
        )

        # Create an access grant
        grant = await ProductManager.create_access_grant(
            product_id=product["id"],
            customer_email="buyer@example.com",
            customer_name="Jane Buyer",
            amount_paid=1999,
            currency="usd",
            stripe_session_id="cs_test_123",
            stripe_payment_intent_id="pi_test_456",
        )

        assert grant["id"] > 0
        assert grant["product_id"] == product["id"]
        assert grant["customer_email"] == "buyer@example.com"
        assert grant["customer_name"] == "Jane Buyer"
        assert grant["amount_paid"] == 1999
        assert grant["access_token"] is not None
        assert len(grant["access_token"]) == 48
        assert grant["download_count"] == 0
        assert grant["download_limit"] == 3  # inherited from product
        assert grant["expires_at"] is not None  # inherited 30-day expiry
        assert grant["revoked_at"] is None

        # Validate the access token
        validated = await ProductManager.validate_access_token(grant["access_token"])
        assert validated is not None
        assert validated["id"] == grant["id"]
        assert validated["product_name"] == "E-Book Download"
        assert validated["content_ids"] == [42]

        # Record a download and verify
        await ProductManager.record_download(grant["id"])
        validated2 = await ProductManager.validate_access_token(grant["access_token"])
        assert validated2 is not None
        assert validated2["download_count"] == 1

        # List grants for product and customer
        product_grants = await ProductManager.list_grants_for_product(product["id"])
        assert len(product_grants) >= 1
        assert any(g["id"] == grant["id"] for g in product_grants)

        customer_grants = await ProductManager.list_grants_for_customer("buyer@example.com")
        assert len(customer_grants) >= 1
        assert any(g["id"] == grant["id"] for g in customer_grants)

        # Revoke the grant
        await ProductManager.revoke_access(grant["id"])

        # Validate again — should be None (revoked)
        revoked_result = await ProductManager.validate_access_token(grant["access_token"])
        assert revoked_result is None

        # Non-existent token returns None
        assert await ProductManager.validate_access_token("bogus_token") is None

        # Cleanup
        await db.execute(
            "DELETE FROM articulate_access_grants WHERE id = %s", (grant["id"],)
        )
        await db.execute(
            "DELETE FROM articulate_products WHERE id = %s", (product["id"],)
        )
    finally:
        await _cleanup_test_user("grant-test@example.com")


@pytest.mark.asyncio
async def test_download_limit_enforcement(setup_db):
    """Test that download limit is enforced during token validation."""
    user = await _create_test_user("dlimit-test@example.com")
    try:
        product = await ProductManager.create_product(
            name="Limited Download",
            price_cents=500,
            created_by=user["id"],
            download_limit=2,
        )

        grant = await ProductManager.create_access_grant(
            product_id=product["id"],
            customer_email="limited@example.com",
            amount_paid=500,
        )

        # Use up both downloads
        await ProductManager.record_download(grant["id"])
        await ProductManager.record_download(grant["id"])

        # Third attempt should be rejected
        result = await ProductManager.validate_access_token(grant["access_token"])
        assert result is None, "Token should be invalid after exceeding download limit"

        # Cleanup
        await db.execute(
            "DELETE FROM articulate_access_grants WHERE id = %s", (grant["id"],)
        )
        await db.execute(
            "DELETE FROM articulate_products WHERE id = %s", (product["id"],)
        )
    finally:
        await _cleanup_test_user("dlimit-test@example.com")


@pytest.mark.asyncio
async def test_expiry_enforcement(setup_db):
    """Test that expired grants are rejected during token validation."""
    user = await _create_test_user("expiry-test@example.com")
    try:
        product = await ProductManager.create_product(
            name="Expiring Product",
            price_cents=1000,
            created_by=user["id"],
            access_duration_days=1,
        )

        grant = await ProductManager.create_access_grant(
            product_id=product["id"],
            customer_email="expiry@example.com",
            amount_paid=1000,
        )

        # Token should work now
        result = await ProductManager.validate_access_token(grant["access_token"])
        assert result is not None

        # Manually expire the grant
        past = datetime.now(timezone.utc) - timedelta(days=2)
        await db.execute(
            "UPDATE articulate_access_grants SET expires_at = %s WHERE id = %s",
            (past, grant["id"]),
        )

        # Token should now be rejected
        result = await ProductManager.validate_access_token(grant["access_token"])
        assert result is None, "Token should be invalid after expiry"

        # Cleanup
        await db.execute(
            "DELETE FROM articulate_access_grants WHERE id = %s", (grant["id"],)
        )
        await db.execute(
            "DELETE FROM articulate_products WHERE id = %s", (product["id"],)
        )
    finally:
        await _cleanup_test_user("expiry-test@example.com")

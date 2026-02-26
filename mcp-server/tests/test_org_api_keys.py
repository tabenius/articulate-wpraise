"""Integration tests for Organization API Keys."""

import pytest
from datetime import datetime, timedelta, timezone

from articulate_mcp.database import db
from articulate_mcp.org_api_key_manager import OrgApiKeyManager
from articulate_mcp.connection_manager import connection_manager
from articulate_mcp.user_manager import UserManager


@pytest.fixture
async def setup_db():
    """Setup database connection for tests."""
    await db.connect()
    yield
    await db.disconnect()


@pytest.fixture
async def test_user(setup_db):
    """Create a test user."""
    # Cleanup existing
    await db.execute("DELETE FROM articulate_users_auth WHERE email = %s", ("apitest@example.com",))

    # Create user
    user = await UserManager.register_user(
        email="apitest@example.com",
        password="testpass123",
        name="API Test User"
    )

    yield user

    # Cleanup
    await db.execute("DELETE FROM articulate_users_auth WHERE email = %s", ("apitest@example.com",))


@pytest.fixture
async def test_organization(test_user):
    """Create a test organization."""
    # Cleanup existing
    await db.execute("DELETE FROM articulate_organizations WHERE slug = %s", ("test-org-api",))

    # Create organization
    org_id = await db.insert(
        """
        INSERT INTO articulate_organizations (name, slug, owner_id)
        VALUES (%s, %s, %s)
        """,
        ("Test Org API", "test-org-api", test_user["id"])
    )

    # Add user as owner
    await db.insert(
        """
        INSERT INTO articulate_organization_members (organization_id, user_id, role)
        VALUES (%s, %s, %s)
        """,
        (org_id, test_user["id"], "owner")
    )

    yield {"id": org_id, "name": "Test Org API", "slug": "test-org-api"}

    # Cleanup (cascade will handle members)
    await db.execute("DELETE FROM articulate_organizations WHERE id = %s", (org_id,))


@pytest.mark.asyncio
async def test_create_api_key(test_organization, test_user):
    """Test creating an organization API key."""
    org_id = test_organization["id"]
    user_id = test_user["id"]

    # Create API key
    key_data = await OrgApiKeyManager.create_api_key(
        organization_id=org_id,
        created_by=user_id,
        description="Test registration key",
        expiry_days=7
    )

    assert "key" in key_data
    assert key_data["key"].startswith("wpai_org_")
    assert f"wpai_org_{org_id}_" in key_data["key"]
    assert key_data["organization_id"] == org_id
    assert key_data["is_active"] is True

    # Verify key was stored in database
    stored_key = await db.fetchone(
        "SELECT * FROM articulate_org_api_keys WHERE id = %s",
        (key_data["id"],)
    )
    assert stored_key is not None
    assert stored_key["key_hash"] is not None
    assert stored_key["key_prefix"] == key_data["key"][:12]
    assert stored_key["used_at"] is None

    # Cleanup
    await db.execute("DELETE FROM articulate_org_api_keys WHERE id = %s", (key_data["id"],))


@pytest.mark.asyncio
async def test_api_key_permissions(test_organization, test_user):
    """Test that non-admins cannot create API keys."""
    org_id = test_organization["id"]

    # Create a member user (not admin)
    member_user = await UserManager.register_user(
        email="member@example.com",
        password="memberpass",
        name="Member User"
    )

    # Add as member (not owner/admin)
    await db.insert(
        """
        INSERT INTO articulate_organization_members (organization_id, user_id, role)
        VALUES (%s, %s, %s)
        """,
        (org_id, member_user["id"], "member")
    )

    # Try to create API key as member (should fail)
    with pytest.raises(ValueError, match="Only owners and admins can create API keys"):
        await OrgApiKeyManager.create_api_key(
            organization_id=org_id,
            created_by=member_user["id"],
            description="Should fail"
        )

    # Cleanup
    await db.execute("DELETE FROM articulate_users_auth WHERE email = %s", ("member@example.com",))


@pytest.mark.asyncio
async def test_validate_and_consume_key(test_organization, test_user):
    """Test API key validation and single-use consumption."""
    org_id = test_organization["id"]
    user_id = test_user["id"]

    # Create API key
    key_data = await OrgApiKeyManager.create_api_key(
        organization_id=org_id,
        created_by=user_id,
        description="Single-use test"
    )

    full_key = key_data["key"]

    # Validate and consume the key (first use - should succeed)
    org_data = await OrgApiKeyManager.validate_and_consume_key(full_key)

    assert org_data is not None
    assert org_data["organization_id"] == org_id
    assert org_data["organization_name"] == test_organization["name"]
    assert org_data["organization_slug"] == test_organization["slug"]

    # Verify key is marked as used
    used_key = await db.fetchone(
        "SELECT * FROM articulate_org_api_keys WHERE id = %s",
        (key_data["id"],)
    )
    assert used_key["used_at"] is not None

    # Try to use the same key again (should fail)
    org_data_retry = await OrgApiKeyManager.validate_and_consume_key(full_key)
    assert org_data_retry is None  # Already used

    # Cleanup
    await db.execute("DELETE FROM articulate_org_api_keys WHERE id = %s", (key_data["id"],))


@pytest.mark.asyncio
async def test_expired_key_rejected(test_organization, test_user):
    """Test that expired keys are rejected."""
    org_id = test_organization["id"]
    user_id = test_user["id"]

    # Create API key with 0 days expiry (immediately expired)
    key_data = await OrgApiKeyManager.create_api_key(
        organization_id=org_id,
        created_by=user_id,
        description="Expired key test",
        expiry_days=0
    )

    full_key = key_data["key"]

    # Set expiry to past
    await db.execute(
        "UPDATE articulate_org_api_keys SET expires_at = %s WHERE id = %s",
        (datetime.now(timezone.utc) - timedelta(days=1), key_data["id"])
    )

    # Try to validate expired key (should fail)
    org_data = await OrgApiKeyManager.validate_and_consume_key(full_key)
    assert org_data is None  # Expired

    # Cleanup
    await db.execute("DELETE FROM articulate_org_api_keys WHERE id = %s", (key_data["id"],))


@pytest.mark.asyncio
async def test_revoke_api_key(test_organization, test_user):
    """Test revoking an API key."""
    org_id = test_organization["id"]
    user_id = test_user["id"]

    # Create API key
    key_data = await OrgApiKeyManager.create_api_key(
        organization_id=org_id,
        created_by=user_id,
        description="To be revoked"
    )

    key_id = key_data["id"]

    # Revoke the key
    result = await OrgApiKeyManager.revoke_key(key_id, org_id, user_id)
    assert result is True

    # Verify key is inactive
    revoked_key = await db.fetchone(
        "SELECT * FROM articulate_org_api_keys WHERE id = %s",
        (key_id,)
    )
    assert revoked_key["is_active"] == 0

    # Try to use revoked key (should fail)
    org_data = await OrgApiKeyManager.validate_and_consume_key(key_data["key"])
    assert org_data is None  # Revoked

    # Cleanup
    await db.execute("DELETE FROM articulate_org_api_keys WHERE id = %s", (key_id,))


@pytest.mark.asyncio
async def test_list_api_keys(test_organization, test_user):
    """Test listing organization API keys."""
    org_id = test_organization["id"]
    user_id = test_user["id"]

    # Create multiple API keys
    key1 = await OrgApiKeyManager.create_api_key(
        organization_id=org_id,
        created_by=user_id,
        description="Key 1"
    )

    key2 = await OrgApiKeyManager.create_api_key(
        organization_id=org_id,
        created_by=user_id,
        description="Key 2"
    )

    # List keys
    keys = await OrgApiKeyManager.list_keys(org_id, user_id)

    assert len(keys) >= 2
    assert any(k["id"] == key1["id"] for k in keys)
    assert any(k["id"] == key2["id"] for k in keys)

    # Verify full key is not in list
    for key in keys:
        assert "key" not in key
        assert "key_hash" not in key
        assert "key_prefix" in key

    # Cleanup
    await db.execute("DELETE FROM articulate_org_api_keys WHERE id IN (%s, %s)", (key1["id"], key2["id"]))


@pytest.mark.asyncio
async def test_org_connection_creation(test_organization, test_user):
    """Test creating an organization-owned connection."""
    org_id = test_organization["id"]

    # Create org connection
    connection = await connection_manager.add_org_connection(
        organization_id=org_id,
        name="Test WP Site",
        wp_url="http://test-wp.example.com",
        wp_graphql_endpoint="http://test-wp.example.com/graphql",
        wp_user="admin",
        wp_app_password="test_password_123"
    )

    assert connection["id"] > 0
    assert connection["organization_id"] == org_id
    assert connection["name"] == "Test WP Site"
    assert connection["wp_url"] == "http://test-wp.example.com"
    assert "wp_app_password" not in connection  # Shouldn't be in return

    # Verify in database
    stored_conn = await db.fetchone(
        "SELECT * FROM articulate_wordpress_connections WHERE id = %s",
        (connection["id"],)
    )
    assert stored_conn is not None
    assert stored_conn["organization_id"] == org_id
    assert stored_conn["wp_app_password"] is not None  # Encrypted password stored

    # Get org connections
    org_connections = await connection_manager.get_org_connections(org_id)
    assert len(org_connections) > 0
    assert any(c["id"] == connection["id"] for c in org_connections)

    # Cleanup
    await db.execute("DELETE FROM articulate_wordpress_connections WHERE id = %s", (connection["id"],))


@pytest.mark.asyncio
async def test_full_registration_flow(test_organization, test_user):
    """Test the complete WordPress site registration flow."""
    org_id = test_organization["id"]
    user_id = test_user["id"]

    # Step 1: Create API key
    key_data = await OrgApiKeyManager.create_api_key(
        organization_id=org_id,
        created_by=user_id,
        description="Full flow test"
    )

    api_key = key_data["key"]

    # Step 2: Validate and consume key
    org_data = await OrgApiKeyManager.validate_and_consume_key(api_key)
    assert org_data is not None

    # Step 3: Create organization connection (simulating plugin registration)
    connection = await connection_manager.add_org_connection(
        organization_id=org_data["organization_id"],
        name="Plugin Test Site",
        wp_url="http://plugin-test.example.com",
        wp_graphql_endpoint="http://plugin-test.example.com/graphql",
        wp_user="admin",
        wp_app_password="generated_app_pass_123"
    )

    assert connection["id"] > 0
    assert connection["organization_id"] == org_id

    # Step 4: Verify key is consumed
    retry_result = await OrgApiKeyManager.validate_and_consume_key(api_key)
    assert retry_result is None  # Already used

    # Step 5: Verify connection exists in org
    org_connections = await connection_manager.get_org_connections(org_id)
    assert any(c["id"] == connection["id"] for c in org_connections)

    # Cleanup
    await db.execute("DELETE FROM articulate_wordpress_connections WHERE id = %s", (connection["id"],))
    await db.execute("DELETE FROM articulate_org_api_keys WHERE id = %s", (key_data["id"],))

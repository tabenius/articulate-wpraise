"""Integration tests for ConnectionManager."""

import pytest

from wp_mcp.connection_manager import connection_manager
from wp_mcp.database import db
from wp_mcp.user_manager import UserManager


@pytest.fixture
async def setup_db():
    """Setup database connection for tests."""
    await db.connect()
    yield
    await db.disconnect()


@pytest.fixture
async def test_user(setup_db):
    """Create a test user."""
    user = await UserManager.register_user(
        email="conntest@example.com",
        password="pass123",
        name="Connection Test User"
    )
    yield user
    # Cleanup
    await db.execute("DELETE FROM wp_users_auth WHERE id = %s", (user["id"],))


@pytest.mark.asyncio
async def test_add_connection(test_user):
    """Test adding a WordPress connection."""
    connection = await connection_manager.add_connection(
        user_id=test_user["id"],
        name="Test Blog",
        wp_url="https://example.com",
        wp_graphql_endpoint="https://example.com/graphql",
        wp_user="admin",
        wp_app_password="test_password_123"
    )
    
    assert connection["id"] > 0
    assert connection["name"] == "Test Blog"
    assert connection["wp_url"] == "https://example.com"
    assert connection["is_active"] is True  # First connection should be active
    assert "wp_app_password" not in connection  # Password not returned
    
    # Cleanup
    await db.execute("DELETE FROM wp_wordpress_connections WHERE id = %s", (connection["id"],))


@pytest.mark.asyncio
async def test_connection_password_encryption(test_user):
    """Test that WordPress app passwords are encrypted."""
    connection = await connection_manager.add_connection(
        user_id=test_user["id"],
        name="Encryption Test",
        wp_url="https://example.com",
        wp_graphql_endpoint="https://example.com/graphql",
        wp_user="admin",
        wp_app_password="my_secret_password"
    )
    
    # Check encrypted password in database
    stored = await db.fetchone(
        "SELECT wp_app_password FROM wp_wordpress_connections WHERE id = %s",
        (connection["id"],)
    )
    assert stored["wp_app_password"] != "my_secret_password"  # Should be encrypted
    assert stored["wp_app_password"].startswith("gAAAAA")  # Fernet encryption
    
    # Verify decryption works
    decrypted_conn = await connection_manager.get_connection(
        connection["id"],
        test_user["id"]
    )
    assert decrypted_conn["wp_app_password"] == "my_secret_password"
    
    # Cleanup
    await db.execute("DELETE FROM wp_wordpress_connections WHERE id = %s", (connection["id"],))


@pytest.mark.asyncio
async def test_get_connections(test_user):
    """Test retrieving all user connections."""
    # Add multiple connections
    conn1 = await connection_manager.add_connection(
        user_id=test_user["id"],
        name="Blog 1",
        wp_url="https://blog1.com",
        wp_graphql_endpoint="https://blog1.com/graphql",
        wp_user="admin",
        wp_app_password="pass1"
    )
    conn2 = await connection_manager.add_connection(
        user_id=test_user["id"],
        name="Blog 2",
        wp_url="https://blog2.com",
        wp_graphql_endpoint="https://blog2.com/graphql",
        wp_user="editor",
        wp_app_password="pass2"
    )
    
    # Get all connections
    connections = await connection_manager.get_connections(test_user["id"])
    
    assert len(connections) >= 2
    names = [c["name"] for c in connections]
    assert "Blog 1" in names
    assert "Blog 2" in names
    
    # Verify passwords are not included in list
    for conn in connections:
        assert "wp_app_password" not in conn
    
    # Cleanup
    await db.execute("DELETE FROM wp_wordpress_connections WHERE id IN (%s, %s)", (conn1["id"], conn2["id"]))


@pytest.mark.asyncio
async def test_active_connection(test_user):
    """Test getting and setting active connection."""
    # Add two connections
    conn1 = await connection_manager.add_connection(
        user_id=test_user["id"],
        name="First",
        wp_url="https://first.com",
        wp_graphql_endpoint="https://first.com/graphql",
        wp_user="admin",
        wp_app_password="pass1"
    )
    conn2 = await connection_manager.add_connection(
        user_id=test_user["id"],
        name="Second",
        wp_url="https://second.com",
        wp_graphql_endpoint="https://second.com/graphql",
        wp_user="admin",
        wp_app_password="pass2"
    )
    
    # First connection should be active
    active = await connection_manager.get_active_connection(test_user["id"])
    assert active["id"] == conn1["id"]
    assert active["name"] == "First"
    
    # Switch to second connection
    await connection_manager.set_active_connection(conn2["id"], test_user["id"])
    
    # Verify switch
    active = await connection_manager.get_active_connection(test_user["id"])
    assert active["id"] == conn2["id"]
    assert active["name"] == "Second"
    
    # Cleanup
    await db.execute("DELETE FROM wp_wordpress_connections WHERE id IN (%s, %s)", (conn1["id"], conn2["id"]))


@pytest.mark.asyncio
async def test_url_validation(test_user):
    """Test URL validation prevents SSRF."""
    # Test private IP rejection
    with pytest.raises(ValueError, match="private IP"):
        await connection_manager.add_connection(
            user_id=test_user["id"],
            name="Private IP",
            wp_url="http://192.168.1.1",
            wp_graphql_endpoint="http://192.168.1.1/graphql",
            wp_user="admin",
            wp_app_password="pass"
        )
    
    # Test metadata endpoint rejection
    with pytest.raises(ValueError, match="metadata"):
        await connection_manager.add_connection(
            user_id=test_user["id"],
            name="Metadata",
            wp_url="http://169.254.169.254/latest",
            wp_graphql_endpoint="http://169.254.169.254/graphql",
            wp_user="admin",
            wp_app_password="pass"
        )
    
    # Test localhost is allowed
    conn = await connection_manager.add_connection(
        user_id=test_user["id"],
        name="Localhost",
        wp_url="http://localhost:8080",
        wp_graphql_endpoint="http://localhost:8080/graphql",
        wp_user="admin",
        wp_app_password="pass"
    )
    assert conn["id"] > 0
    
    # Cleanup
    await db.execute("DELETE FROM wp_wordpress_connections WHERE id = %s", (conn["id"],))


@pytest.mark.asyncio
async def test_delete_connection(test_user):
    """Test deleting a connection."""
    connection = await connection_manager.add_connection(
        user_id=test_user["id"],
        name="To Delete",
        wp_url="https://delete.com",
        wp_graphql_endpoint="https://delete.com/graphql",
        wp_user="admin",
        wp_app_password="pass"
    )
    
    # Delete connection
    success = await connection_manager.delete_connection(connection["id"], test_user["id"])
    assert success is True
    
    # Verify deletion
    conn = await connection_manager.get_connection(connection["id"], test_user["id"])
    assert conn is None

"""Integration tests for UserManager."""

import pytest
from datetime import datetime, timedelta, timezone

from wp_mcp.database import db
from wp_mcp.user_manager import UserManager


@pytest.fixture
async def setup_db():
    """Setup database connection for tests."""
    await db.connect()
    yield
    await db.disconnect()


@pytest.mark.asyncio
async def test_user_registration(setup_db):
    """Test user registration with password hashing."""
    # Cleanup any existing user from previous runs
    await db.execute("DELETE FROM wp_users_auth WHERE email = %s", ("test@example.com",))

    # Register a new user
    user = await UserManager.register_user(
        email="test@example.com",
        password="securepassword123",
        name="Test User"
    )
    
    assert user["id"] > 0
    assert user["email"] == "test@example.com"
    assert user["name"] == "Test User"
    assert "password" not in user  # Password should not be returned
    
    # Verify user was stored in database
    stored_user = await db.fetchone(
        "SELECT * FROM wp_users_auth WHERE email = %s",
        ("test@example.com",)
    )
    assert stored_user is not None
    assert stored_user["password_hash"].startswith("$2b$")  # bcrypt hash
    
    # Cleanup
    await db.execute("DELETE FROM wp_users_auth WHERE email = %s", ("test@example.com",))


@pytest.mark.asyncio
async def test_duplicate_registration(setup_db):
    """Test that duplicate email registration fails."""
    # Cleanup any existing user from previous runs
    await db.execute("DELETE FROM wp_users_auth WHERE email = %s", ("duplicate@test.com",))

    # Register first user
    await UserManager.register_user("duplicate@test.com", "password123", "User 1")
    
    # Try to register with same email
    with pytest.raises(ValueError, match="already exists"):
        await UserManager.register_user("duplicate@test.com", "password456", "User 2")
    
    # Cleanup
    await db.execute("DELETE FROM wp_users_auth WHERE email = %s", ("duplicate@test.com",))


@pytest.mark.asyncio
async def test_authentication_success(setup_db):
    """Test successful authentication."""
    # Register user
    await UserManager.register_user("auth@test.com", "mypassword", "Auth User")
    
    # Authenticate
    result = await UserManager.authenticate("auth@test.com", "mypassword")
    
    assert result is not None
    assert result["user"]["email"] == "auth@test.com"
    assert "session_id" in result
    assert len(result["session_id"]) == 43  # 32 bytes base64 encoded
    assert "expires_at" in result
    
    # Verify session was created
    session = await db.fetchone(
        "SELECT * FROM wp_sessions WHERE id = %s",
        (result["session_id"],)
    )
    assert session is not None
    assert session["user_id"] == result["user"]["id"]
    
    # Cleanup
    await db.execute("DELETE FROM wp_sessions WHERE id = %s", (result["session_id"],))
    await db.execute("DELETE FROM wp_users_auth WHERE email = %s", ("auth@test.com",))


@pytest.mark.asyncio
async def test_authentication_failure(setup_db):
    """Test failed authentication with wrong password."""
    # Register user
    await UserManager.register_user("wrong@test.com", "correctpass", "User")
    
    # Try with wrong password
    result = await UserManager.authenticate("wrong@test.com", "wrongpass")
    assert result is None
    
    # Try with non-existent email
    result = await UserManager.authenticate("nonexistent@test.com", "anypass")
    assert result is None
    
    # Cleanup
    await db.execute("DELETE FROM wp_users_auth WHERE email = %s", ("wrong@test.com",))


@pytest.mark.asyncio
async def test_get_user_from_session(setup_db):
    """Test retrieving user from valid session."""
    # Register and authenticate
    await UserManager.register_user("session@test.com", "password123", "Session User")
    auth_result = await UserManager.authenticate("session@test.com", "password123")
    session_id = auth_result["session_id"]
    
    # Get user from session
    user = await UserManager.get_user_from_session(session_id)
    
    assert user is not None
    assert user["email"] == "session@test.com"
    assert user["name"] == "Session User"
    
    # Cleanup
    await db.execute("DELETE FROM wp_sessions WHERE id = %s", (session_id,))
    await db.execute("DELETE FROM wp_users_auth WHERE email = %s", ("session@test.com",))


@pytest.mark.asyncio
async def test_expired_session(setup_db):
    """Test that expired sessions are rejected."""
    # Register and authenticate
    await UserManager.register_user("expired@test.com", "password123", "User")
    auth_result = await UserManager.authenticate("expired@test.com", "password123")
    session_id = auth_result["session_id"]
    
    # Manually expire the session
    expired_time = datetime.now(timezone.utc) - timedelta(days=1)
    await db.execute(
        "UPDATE wp_sessions SET expires_at = %s WHERE id = %s",
        (expired_time, session_id)
    )
    
    # Try to get user from expired session
    user = await UserManager.get_user_from_session(session_id)
    assert user is None
    
    # Verify session was deleted
    session = await db.fetchone(
        "SELECT * FROM wp_sessions WHERE id = %s",
        (session_id,)
    )
    assert session is None
    
    # Cleanup
    await db.execute("DELETE FROM wp_users_auth WHERE email = %s", ("expired@test.com",))


@pytest.mark.asyncio
async def test_logout(setup_db):
    """Test logout deletes session."""
    # Register and authenticate
    await UserManager.register_user("logout@test.com", "password123", "User")
    auth_result = await UserManager.authenticate("logout@test.com", "password123")
    session_id = auth_result["session_id"]
    
    # Logout
    success = await UserManager.logout(session_id)
    assert success is True
    
    # Verify session was deleted
    session = await db.fetchone(
        "SELECT * FROM wp_sessions WHERE id = %s",
        (session_id,)
    )
    assert session is None
    
    # Try to logout again (should return False)
    success = await UserManager.logout(session_id)
    assert success is False
    
    # Cleanup
    await db.execute("DELETE FROM wp_users_auth WHERE email = %s", ("logout@test.com",))

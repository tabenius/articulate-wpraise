"""Test script for user management and WordPress connections."""

import asyncio
from wp_mcp.user_manager import UserManager
from wp_mcp.connection_manager import connection_manager
from wp_mcp.database import db


async def test_user_management():
    """Test user registration, authentication, and connection management."""

    print("=" * 60)
    print("Testing User Management & WordPress Connections")
    print("=" * 60)

    # Connect to database
    await db.connect()
    print("✓ Database connected")

    # Test 1: Register a user
    print("\n[Test 1] Registering user...")
    try:
        user = await UserManager.register_user(
            email="test@example.com",
            password="securepass123",
            name="Test User"
        )
        print(f"✓ User registered: {user['email']} (ID: {user['id']})")
        user_id = user['id']
    except ValueError as e:
        print(f"✗ Registration failed: {e}")
        # User might already exist, try to authenticate
        print("\n[Test 1b] User exists, authenticating...")
        auth_result = await UserManager.authenticate(
            email="test@example.com",
            password="securepass123"
        )
        if auth_result:
            print(f"✓ User authenticated: {auth_result['user']['email']}")
            user_id = auth_result['user']['id']
        else:
            print("✗ Authentication failed")
            return

    # Test 2: Authenticate user
    print("\n[Test 2] Authenticating user...")
    auth_result = await UserManager.authenticate(
        email="test@example.com",
        password="securepass123"
    )
    if auth_result:
        print(f"✓ Authentication successful")
        print(f"  Session ID: {auth_result['session_id'][:20]}...")
        print(f"  Expires: {auth_result['expires_at']}")
        session_id = auth_result['session_id']
    else:
        print("✗ Authentication failed")
        return

    # Test 3: Get user from session
    print("\n[Test 3] Getting user from session...")
    user = await UserManager.get_user_from_session(session_id)
    if user:
        print(f"✓ User retrieved from session: {user['email']}")
    else:
        print("✗ Failed to get user from session")
        return

    # Test 4: Add WordPress connection
    print("\n[Test 4] Adding WordPress connection...")
    try:
        connection = await connection_manager.add_connection(
            user_id=user_id,
            name="My Personal Blog",
            wp_url="http://localhost:8080",
            wp_graphql_endpoint="http://localhost:8080/graphql",
            wp_user="admin",
            wp_app_password="test_password_123"
        )
        print(f"✓ Connection added: {connection['name']} (ID: {connection['id']})")
        print(f"  Active: {connection['is_active']}")
        connection_id = connection['id']
    except ValueError as e:
        print(f"✗ Failed to add connection: {e}")
        # Try to get existing connections
        connections = await connection_manager.get_connections(user_id)
        if connections:
            print(f"  Found {len(connections)} existing connections")
            connection_id = connections[0]['id']
        else:
            return

    # Test 5: Get all connections
    print("\n[Test 5] Getting all connections...")
    connections = await connection_manager.get_connections(user_id)
    print(f"✓ Found {len(connections)} connections:")
    for conn in connections:
        print(f"  - {conn['name']} ({'active' if conn['is_active'] else 'inactive'})")

    # Test 6: Get active connection
    print("\n[Test 6] Getting active connection...")
    active_conn = await connection_manager.get_active_connection(user_id)
    if active_conn:
        print(f"✓ Active connection: {active_conn['name']}")
        print(f"  URL: {active_conn['wp_url']}")
        print(f"  GraphQL: {active_conn['wp_graphql_endpoint']}")
        print(f"  User: {active_conn['wp_user']}")
        # Check password was decrypted
        print(f"  Password decrypted: {'Yes' if active_conn.get('wp_app_password') else 'No'}")
    else:
        print("✗ No active connection found")

    # Test 7: Add second connection
    print("\n[Test 7] Adding second connection...")
    try:
        connection2 = await connection_manager.add_connection(
            user_id=user_id,
            name="Client Site",
            wp_url="http://example.com",
            wp_graphql_endpoint="http://example.com/graphql",
            wp_user="editor",
            wp_app_password="client_password_456"
        )
        print(f"✓ Second connection added: {connection2['name']}")
        print(f"  Active: {connection2['is_active']}")
        connection2_id = connection2['id']

        # Test 8: Switch active connection
        print("\n[Test 8] Switching active connection...")
        await connection_manager.set_active_connection(connection2_id, user_id)
        print(f"✓ Switched to: {connection2['name']}")

        # Verify switch
        active_conn = await connection_manager.get_active_connection(user_id)
        if active_conn and active_conn['id'] == connection2_id:
            print(f"✓ Confirmed active connection is now: {active_conn['name']}")
        else:
            print("✗ Active connection not switched correctly")

    except ValueError as e:
        print(f"  Connection already exists: {e}")

    # Test 9: Logout
    print("\n[Test 9] Logging out...")
    logout_success = await UserManager.logout(session_id)
    if logout_success:
        print("✓ User logged out successfully")

        # Verify session is invalid
        user = await UserManager.get_user_from_session(session_id)
        if user is None:
            print("✓ Session invalidated correctly")
        else:
            print("✗ Session still valid after logout")
    else:
        print("✗ Logout failed")

    # Cleanup
    await db.disconnect()
    print("\n" + "=" * 60)
    print("✓ All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_user_management())

"""
Comprehensive pytest-based test suite for WP-AI MCP Server.

Tests all endpoints with proper setup/teardown and data cleanup.
"""

import pytest
import requests
import json
import io
from pathlib import Path
from typing import Dict, Optional

# Configuration
BASE_URL = "http://localhost:8000"
TEST_TIMEOUT = 30


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def base_url():
    """Base URL for API requests."""
    return BASE_URL


@pytest.fixture(scope="session")
def test_user_credentials():
    """Test user credentials."""
    import time
    return {
        "email": f"test-{int(time.time())}@example.com",
        "password": "SecureTestPass123!",
        "name": "Pytest Test User"
    }


@pytest.fixture(scope="session")
def registered_user(base_url, test_user_credentials):
    """Register a test user and return user info."""
    response = requests.post(
        f"{base_url}/register",
        json=test_user_credentials,
        timeout=TEST_TIMEOUT
    )
    assert response.status_code == 201, f"Registration failed: {response.text}"
    user_data = response.json()
    assert "id" in user_data
    assert user_data["email"] == test_user_credentials["email"]
    return {**user_data, **test_user_credentials}


@pytest.fixture(scope="session")
def auth_session(base_url, registered_user):
    """Login and return session with auth headers."""
    response = requests.post(
        f"{base_url}/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"]
        },
        timeout=TEST_TIMEOUT
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    session_data = response.json()
    assert "session_id" in session_data

    return {
        "session_id": session_data["session_id"],
        "user": registered_user,
        "headers": {
            "X-Session-ID": session_data["session_id"],
            "Content-Type": "application/json"
        }
    }


@pytest.fixture
def second_user(base_url):
    """Create a second test user for invite/organization tests."""
    import time
    credentials = {
        "email": f"test2-{int(time.time())}@example.com",
        "password": "SecureTestPass123!",
        "name": "Second Test User"
    }

    response = requests.post(
        f"{base_url}/register",
        json=credentials,
        timeout=TEST_TIMEOUT
    )
    assert response.status_code == 201
    user_data = response.json()

    # Login
    response = requests.post(
        f"{base_url}/login",
        json={"email": credentials["email"], "password": credentials["password"]},
        timeout=TEST_TIMEOUT
    )
    session_data = response.json()

    yield {
        **user_data,
        **credentials,
        "session_id": session_data["session_id"],
        "headers": {
            "X-Session-ID": session_data["session_id"],
            "Content-Type": "application/json"
        }
    }

    # Cleanup: Delete second user
    requests.delete(
        f"{base_url}/profile",
        headers={"X-Session-ID": session_data["session_id"], "Content-Type": "application/json"},
        json={"password": credentials["password"]},
        timeout=TEST_TIMEOUT
    )


# Cleanup tracking
created_resources = {
    "organizations": [],
    "connections": [],
    "invites": []
}


def track_resource(resource_type: str, resource_id: int):
    """Track created resource for cleanup."""
    created_resources[resource_type].append(resource_id)


# =============================================================================
# Health Check Tests
# =============================================================================

class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_check(self, base_url):
        """Test /health endpoint."""
        response = requests.get(f"{base_url}/health", timeout=TEST_TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data.get("alive") is True

    def test_health_ready(self, base_url):
        """Test /health/ready endpoint."""
        response = requests.get(f"{base_url}/health/ready", timeout=TEST_TIMEOUT)
        assert response.status_code in [200, 503]


# =============================================================================
# Authentication Tests
# =============================================================================

class TestAuthentication:
    """Test authentication endpoints."""

    def test_register_user(self, registered_user):
        """Test user registration (via fixture)."""
        assert registered_user["id"] > 0
        assert "@" in registered_user["email"]

    def test_login(self, auth_session):
        """Test user login (via fixture)."""
        assert len(auth_session["session_id"]) > 0

    def test_get_me(self, base_url, auth_session):
        """Test /me endpoint."""
        response = requests.get(
            f"{base_url}/me",
            headers=auth_session["headers"],
            timeout=TEST_TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == auth_session["user"]["email"]

    def test_invalid_login(self, base_url):
        """Test login with invalid credentials."""
        response = requests.post(
            f"{base_url}/login",
            json={"email": "invalid@example.com", "password": "wrongpass"},
            timeout=TEST_TIMEOUT
        )
        assert response.status_code in [400, 401]


# =============================================================================
# Profile Tests
# =============================================================================

class TestProfile:
    """Test profile management endpoints."""

    def test_get_profile(self, base_url, auth_session):
        """Test GET /profile."""
        response = requests.get(
            f"{base_url}/profile",
            headers=auth_session["headers"],
            timeout=TEST_TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == auth_session["user"]["email"]

    def test_update_profile(self, base_url, auth_session):
        """Test PUT /profile."""
        import time
        username = f"testuser{int(time.time())}"

        response = requests.put(
            f"{base_url}/profile",
            headers=auth_session["headers"],
            json={
                "username": username,
                "name": "Updated Name",
                "bio": "Test bio for pytest"
            },
            timeout=TEST_TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == username
        assert data["bio"] == "Test bio for pytest"

    def test_get_profile_by_username(self, base_url, auth_session):
        """Test GET /profile/{username}."""
        # First set a username
        import time
        username = f"pubuser{int(time.time())}"

        requests.put(
            f"{base_url}/profile",
            headers=auth_session["headers"],
            json={"username": username},
            timeout=TEST_TIMEOUT
        )

        # Then retrieve it publicly
        response = requests.get(
            f"{base_url}/profile/{username}",
            timeout=TEST_TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == username

    def test_profile_visibility_public(self, base_url, auth_session, second_user):
        """Test public profile visibility."""
        # Set main user's profile to public
        response = requests.put(
            f"{base_url}/profile",
            headers=auth_session["headers"],
            json={"visibility": "public", "username": "public_user_test"},
            timeout=TEST_TIMEOUT
        )
        assert response.status_code == 200

        # Second user should be able to view it
        response = requests.get(
            f"{base_url}/profile/public_user_test",
            headers=second_user["headers"],
            timeout=TEST_TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "public_user_test"
        assert data["visibility"] == "public"
        print("\n✅ Public profile visible to other users")

    def test_profile_visibility_private(self, base_url, auth_session, second_user):
        """Test private profile visibility."""
        # Set main user's profile to private
        response = requests.put(
            f"{base_url}/profile",
            headers=auth_session["headers"],
            json={"visibility": "private", "username": "private_user_test"},
            timeout=TEST_TIMEOUT
        )
        assert response.status_code == 200

        # Second user should NOT be able to view it
        response = requests.get(
            f"{base_url}/profile/private_user_test",
            headers=second_user["headers"],
            timeout=TEST_TIMEOUT
        )
        assert response.status_code == 404
        print("\n✅ Private profile not visible to other users")

        # But the owner should still be able to view it
        response = requests.get(
            f"{base_url}/profile/private_user_test",
            headers=auth_session["headers"],
            timeout=TEST_TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "private_user_test"
        assert data["visibility"] == "private"
        print("✅ Private profile visible to owner")

    def test_profile_visibility_invalid(self, base_url, auth_session):
        """Test invalid visibility value."""
        response = requests.put(
            f"{base_url}/profile",
            headers=auth_session["headers"],
            json={"visibility": "invalid_value"},
            timeout=TEST_TIMEOUT
        )
        assert response.status_code == 400
        print("\n✅ Invalid visibility value rejected")


# =============================================================================
# Organization Tests
# =============================================================================

class TestOrganizations:
    """Test organization management endpoints."""

    def test_create_organization(self, base_url, auth_session):
        """Test POST /organizations."""
        import time
        slug = f"test-org-{int(time.time())}"

        response = requests.post(
            f"{base_url}/organizations",
            headers=auth_session["headers"],
            json={
                "name": "Test Organization",
                "slug": slug,
                "bio": "Organization for pytest testing"
            },
            timeout=TEST_TIMEOUT
        )
        assert response.status_code == 201
        data = response.json()
        assert data["slug"] == slug
        assert data["owner_id"] == auth_session["user"]["id"]

        track_resource("organizations", data["id"])
        return data

    def test_list_organizations(self, base_url, auth_session):
        """Test GET /organizations."""
        # Create an org first
        self.test_create_organization(base_url, auth_session)

        response = requests.get(
            f"{base_url}/organizations",
            headers=auth_session["headers"],
            timeout=TEST_TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_get_organization(self, base_url, auth_session):
        """Test GET /organizations/{id}."""
        org = self.test_create_organization(base_url, auth_session)

        response = requests.get(
            f"{base_url}/organizations/{org['id']}",
            timeout=TEST_TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == org["id"]

    def test_update_organization(self, base_url, auth_session):
        """Test PUT /organizations/{id}."""
        org = self.test_create_organization(base_url, auth_session)

        response = requests.put(
            f"{base_url}/organizations/{org['id']}",
            headers=auth_session["headers"],
            json={
                "name": "Updated Organization Name",
                "bio": "Updated bio"
            },
            timeout=TEST_TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Organization Name"

    def test_get_members(self, base_url, auth_session):
        """Test GET /organizations/{id}/members."""
        org = self.test_create_organization(base_url, auth_session)

        response = requests.get(
            f"{base_url}/organizations/{org['id']}/members",
            timeout=TEST_TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Owner should be a member
        assert len(data) >= 1
        assert data[0]["role"] == "owner"

    def test_change_member_role(self, base_url, auth_session, second_user):
        """Test PUT /organizations/{id}/members/{member_id} to change role."""
        # Create organization
        org = self.test_create_organization(base_url, auth_session)

        # Create invite for second user
        invite_response = requests.post(
            f"{base_url}/organizations/{org['id']}/invites",
            headers=auth_session["headers"],
            json={"email": second_user["user"]["email"], "role": "member"},
            timeout=TEST_TIMEOUT
        )
        assert invite_response.status_code == 201
        invite = invite_response.json()

        # Accept invite as second user
        requests.post(
            f"{base_url}/invites/accept",
            headers=second_user["headers"],
            json={"token": invite["token"]},
            timeout=TEST_TIMEOUT
        )

        # Get members to find second user's member ID
        members_response = requests.get(
            f"{base_url}/organizations/{org['id']}/members",
            timeout=TEST_TIMEOUT
        )
        members = members_response.json()
        second_member = next(m for m in members if m["user_id"] == second_user["user"]["id"])
        assert second_member["role"] == "member"

        # Change role to admin (owner can do this)
        response = requests.put(
            f"{base_url}/organizations/{org['id']}/members/{second_member['user_id']}",
            headers=auth_session["headers"],
            json={"role": "admin"},
            timeout=TEST_TIMEOUT
        )
        assert response.status_code == 200
        print(f"\n✅ Role changed from member to admin")

        # Verify role change
        members_response = requests.get(
            f"{base_url}/organizations/{org['id']}/members",
            timeout=TEST_TIMEOUT
        )
        members = members_response.json()
        updated_member = next(m for m in members if m["user_id"] == second_user["user"]["id"])
        assert updated_member["role"] == "admin"

    def test_change_role_permissions(self, base_url, auth_session, second_user):
        """Test that only owners/admins can change roles."""
        # Create organization
        org = self.test_create_organization(base_url, auth_session)

        # Create and accept invite as member
        invite_response = requests.post(
            f"{base_url}/organizations/{org['id']}/invites",
            headers=auth_session["headers"],
            json={"email": second_user["user"]["email"], "role": "viewer"},
            timeout=TEST_TIMEOUT
        )
        invite = invite_response.json()

        requests.post(
            f"{base_url}/invites/accept",
            headers=second_user["headers"],
            json={"token": invite["token"]},
            timeout=TEST_TIMEOUT
        )

        # Get owner's member ID
        members_response = requests.get(
            f"{base_url}/organizations/{org['id']}/members",
            timeout=TEST_TIMEOUT
        )
        members = members_response.json()
        owner_member = next(m for m in members if m["role"] == "owner")

        # Try to change owner's role as viewer (should fail)
        response = requests.put(
            f"{base_url}/organizations/{org['id']}/members/{owner_member['user_id']}",
            headers=second_user["headers"],
            json={"role": "viewer"},
            timeout=TEST_TIMEOUT
        )
        assert response.status_code in [403, 400]
        print("\n✅ Viewer cannot change roles")

    def test_transfer_ownership(self, base_url, auth_session, second_user):
        """Test POST /organizations/{id}/transfer to transfer ownership."""
        # Create organization
        org = self.test_create_organization(base_url, auth_session)

        # Invite second user as admin
        invite_response = requests.post(
            f"{base_url}/organizations/{org['id']}/invites",
            headers=auth_session["headers"],
            json={"email": second_user["user"]["email"], "role": "admin"},
            timeout=TEST_TIMEOUT
        )
        invite = invite_response.json()

        # Accept invite
        requests.post(
            f"{base_url}/invites/accept",
            headers=second_user["headers"],
            json={"token": invite["token"]},
            timeout=TEST_TIMEOUT
        )

        # Transfer ownership to second user
        response = requests.post(
            f"{base_url}/organizations/{org['id']}/transfer",
            headers=auth_session["headers"],
            json={
                "new_owner_id": second_user["user"]["id"],
                "password": auth_session["user"]["password"],
            },
            timeout=TEST_TIMEOUT
        )
        assert response.status_code == 200
        print("\n✅ Ownership transferred successfully")

        # Verify organization owner changed
        org_response = requests.get(
            f"{base_url}/organizations/{org['id']}",
            timeout=TEST_TIMEOUT
        )
        updated_org = org_response.json()
        assert updated_org["owner_id"] == second_user["user"]["id"]

        # Verify old owner is now admin
        members_response = requests.get(
            f"{base_url}/organizations/{org['id']}/members",
            timeout=TEST_TIMEOUT
        )
        members = members_response.json()
        old_owner = next(m for m in members if m["user_id"] == auth_session["user"]["id"])
        assert old_owner["role"] == "admin"

        # Verify new owner has owner role
        new_owner = next(m for m in members if m["user_id"] == second_user["user"]["id"])
        assert new_owner["role"] == "owner"
        print("✅ Roles updated correctly after transfer")

    def test_transfer_ownership_validation(self, base_url, auth_session, second_user):
        """Test ownership transfer validation."""
        org = self.test_create_organization(base_url, auth_session)

        # Try to transfer to non-admin (should fail)
        invite_response = requests.post(
            f"{base_url}/organizations/{org['id']}/invites",
            headers=auth_session["headers"],
            json={"email": second_user["user"]["email"], "role": "member"},
            timeout=TEST_TIMEOUT
        )
        invite = invite_response.json()

        requests.post(
            f"{base_url}/invites/accept",
            headers=second_user["headers"],
            json={"token": invite["token"]},
            timeout=TEST_TIMEOUT
        )

        response = requests.post(
            f"{base_url}/organizations/{org['id']}/transfer",
            headers=auth_session["headers"],
            json={
                "new_owner_id": second_user["user"]["id"],
                "password": auth_session["user"]["password"],
            },
            timeout=TEST_TIMEOUT
        )
        assert response.status_code == 400
        print("\n✅ Cannot transfer to non-admin")

        # Try with wrong password (should fail)
        response = requests.post(
            f"{base_url}/organizations/{org['id']}/transfer",
            headers=auth_session["headers"],
            json={
                "new_owner_id": second_user["user"]["id"],
                "password": "wrong_password",
            },
            timeout=TEST_TIMEOUT
        )
        assert response.status_code == 400
        print("✅ Wrong password rejected")


# =============================================================================
# Invite Tests
# =============================================================================

class TestInvites:
    """Test organization invite system."""

    def test_create_invite(self, base_url, auth_session, second_user):
        """Test POST /organizations/{id}/invites."""
        # Create an organization
        org_test = TestOrganizations()
        org = org_test.test_create_organization(base_url, auth_session)

        response = requests.post(
            f"{base_url}/organizations/{org['id']}/invites",
            headers=auth_session["headers"],
            json={
                "email": second_user["email"],
                "role": "member"
            },
            timeout=TEST_TIMEOUT
        )
        assert response.status_code == 201
        data = response.json()
        assert data["invitee_email"] == second_user["email"]
        assert "token" in data

        track_resource("invites", data["id"])
        return data

    def test_get_user_invites(self, base_url, auth_session, second_user):
        """Test GET /invites."""
        # Create an invite for second user
        self.test_create_invite(base_url, auth_session, second_user)

        # Check second user's invites
        response = requests.get(
            f"{base_url}/invites",
            headers=second_user["headers"],
            timeout=TEST_TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_accept_invite(self, base_url, auth_session, second_user):
        """Test POST /invites/accept."""
        invite = self.test_create_invite(base_url, auth_session, second_user)

        response = requests.post(
            f"{base_url}/invites/accept",
            headers=second_user["headers"],
            json={"token": invite["token"]},
            timeout=TEST_TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data  # Organization data


class TestImageCompression:
    """Test image compression features."""

    @staticmethod
    def create_test_image(format="PNG", size=(100, 100), color=(255, 0, 0)):
        """Create a test image in memory."""
        from PIL import Image
        img = Image.new("RGB", size, color)
        buffer = io.BytesIO()
        img.save(buffer, format=format)
        buffer.seek(0)
        return buffer

    def test_upload_with_compression_webp(self, base_url, auth_session):
        """Test POST /upload with WebP compression."""
        headers = auth_session["headers"].copy()

        # Create test image
        test_image = self.create_test_image(format="PNG", size=(200, 200))

        files = {"file": ("test.png", test_image, "image/png")}
        data = {
            "type": "avatar",
            "compress": "true",
            "format": "webp",
            "quality": "85"
        }

        response = requests.post(
            f"{base_url}/upload",
            headers=headers,
            files=files,
            data=data,
            timeout=TEST_TIMEOUT
        )
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert "url" in result
        assert "metadata" in result
        assert result["metadata"]["format"] == "webp"
        assert result["metadata"]["quality"] == 85
        print(f"\n✅ WebP compression: {result['metadata']['compression_ratio']:.1f}% reduction")

    def test_upload_with_compression_avif(self, base_url, auth_session):
        """Test POST /upload with AVIF compression."""
        headers = auth_session["headers"].copy()

        test_image = self.create_test_image(format="PNG", size=(200, 200))

        files = {"file": ("test.png", test_image, "image/png")}
        data = {
            "type": "avatar",
            "compress": "true",
            "format": "avif",
            "quality": "80"
        }

        response = requests.post(
            f"{base_url}/upload",
            headers=headers,
            files=files,
            data=data,
            timeout=TEST_TIMEOUT
        )
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert result["metadata"]["format"] == "avif"
        assert result["metadata"]["quality"] == 80
        print(f"\n✅ AVIF compression: {result['metadata']['compression_ratio']:.1f}% reduction")

    def test_upload_with_resize(self, base_url, auth_session):
        """Test POST /upload with resizing."""
        headers = auth_session["headers"].copy()

        # Create large image
        test_image = self.create_test_image(format="PNG", size=(1000, 1000))

        files = {"file": ("test.png", test_image, "image/png")}
        data = {
            "type": "avatar",
            "compress": "true",
            "format": "webp",
            "max_width": "512",
            "max_height": "512"
        }

        response = requests.post(
            f"{base_url}/upload",
            headers=headers,
            files=files,
            data=data,
            timeout=TEST_TIMEOUT
        )
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert result["metadata"]["dimensions"]["width"] <= 512
        assert result["metadata"]["dimensions"]["height"] <= 512
        print(f"\n✅ Image resized: {result['metadata']['dimensions']['width']}x{result['metadata']['dimensions']['height']}")

    def test_upload_without_compression(self, base_url, auth_session):
        """Test POST /upload without compression."""
        headers = auth_session["headers"].copy()

        test_image = self.create_test_image(format="PNG", size=(100, 100))

        files = {"file": ("test.png", test_image, "image/png")}
        data = {"type": "avatar", "compress": "false"}

        response = requests.post(
            f"{base_url}/upload",
            headers=headers,
            files=files,
            data=data,
            timeout=TEST_TIMEOUT
        )
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        # No metadata when not compressing
        assert "metadata" not in result or result["metadata"] is None
        print("\n✅ Upload without compression successful")

    def test_upload_invalid_format(self, base_url, auth_session):
        """Test POST /upload with invalid format."""
        headers = auth_session["headers"].copy()

        test_image = self.create_test_image(format="PNG")

        files = {"file": ("test.png", test_image, "image/png")}
        data = {
            "type": "avatar",
            "compress": "true",
            "format": "invalid_format"
        }

        response = requests.post(
            f"{base_url}/upload",
            headers=headers,
            files=files,
            data=data,
            timeout=TEST_TIMEOUT
        )
        # Should either reject or use default format
        assert response.status_code in [200, 400]
        print("\n✅ Invalid format handling tested")

    def test_image_compressor_class(self):
        """Test ImageCompressor class methods directly."""
        from wp_mcp.image_compressor import ImageCompressor

        # Check availability
        assert ImageCompressor.is_available()

        # Create test image data
        test_image = self.create_test_image(format="PNG", size=(200, 200))
        image_data = test_image.getvalue()

        # Test compression
        compressed_data, metadata = ImageCompressor.compress_image(
            image_data,
            output_format="webp",
            quality=85,
            max_width=100,
            max_height=100
        )

        assert len(compressed_data) > 0
        assert metadata["format"] == "webp"
        assert metadata["quality"] == 85
        assert metadata["dimensions"]["width"] <= 100
        assert metadata["dimensions"]["height"] <= 100
        assert metadata["compression_ratio"] > 0
        print(f"\n✅ ImageCompressor class: {metadata['compression_ratio']:.1f}% reduction")

    def test_image_info(self):
        """Test get_image_info method."""
        from wp_mcp.image_compressor import ImageCompressor

        test_image = self.create_test_image(format="PNG", size=(150, 200))
        image_data = test_image.getvalue()

        info = ImageCompressor.get_image_info(image_data)

        assert info["format"] == "PNG"
        assert info["width"] == 150
        assert info["height"] == 200
        assert info["size"] > 0
        print(f"\n✅ Image info: {info['width']}x{info['height']}, {info['format']}, {info['size']} bytes")

    def test_compression_formats(self):
        """Test all supported compression formats."""
        from wp_mcp.image_compressor import ImageCompressor

        test_image = self.create_test_image(format="PNG", size=(100, 100))
        image_data = test_image.getvalue()

        formats = ["webp", "avif", "jpeg", "png"]

        for fmt in formats:
            compressed_data, metadata = ImageCompressor.compress_image(
                image_data,
                output_format=fmt
            )
            assert len(compressed_data) > 0
            assert metadata["format"] == fmt
            print(f"✅ {fmt.upper()}: {metadata['compression_ratio']:.1f}% reduction")

    def test_large_file_upload(self, base_url, auth_session):
        """Test upload with larger file to verify progress handling."""
        headers = auth_session["headers"].copy()

        # Create larger test image (500x500)
        test_image = self.create_test_image(format="PNG", size=(500, 500))

        files = {"file": ("large_test.png", test_image, "image/png")}
        data = {
            "type": "banner",
            "compress": "true",
            "format": "webp",
            "quality": "85"
        }

        response = requests.post(
            f"{base_url}/upload",
            headers=headers,
            files=files,
            data=data,
            timeout=TEST_TIMEOUT
        )
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        print(f"\n✅ Large file upload successful: {result['metadata']['compression_ratio']:.1f}% reduction")

    def test_cropped_image_upload(self, base_url, auth_session):
        """Test upload of a cropped (square) image."""
        from PIL import Image

        headers = auth_session["headers"].copy()

        # Create a cropped square image (simulate client-side cropping)
        img = Image.new("RGB", (300, 300), (0, 128, 255))
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        files = {"file": ("cropped.png", buffer, "image/png")}
        data = {
            "type": "avatar",
            "compress": "true",
            "format": "webp",
            "quality": "85"
        }

        response = requests.post(
            f"{base_url}/upload",
            headers=headers,
            files=files,
            data=data,
            timeout=TEST_TIMEOUT
        )
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert result["metadata"]["dimensions"]["width"] <= 512
        assert result["metadata"]["dimensions"]["height"] <= 512
        print(f"\n✅ Cropped image upload: {result['metadata']['dimensions']['width']}x{result['metadata']['dimensions']['height']}")


# =============================================================================
# Cleanup
# =============================================================================

def test_cleanup(base_url, auth_session):
    """Cleanup: Delete all created resources."""
    headers = auth_session["headers"]

    # Delete organizations (will cascade delete members and invites)
    for org_id in created_resources["organizations"]:
        try:
            requests.delete(
                f"{base_url}/organizations/{org_id}",
                headers=headers,
                timeout=TEST_TIMEOUT
            )
        except:
            pass

    print(f"\n✅ Cleaned up {len(created_resources['organizations'])} organizations")


def test_final_user_deletion(base_url, auth_session):
    """Final cleanup: Delete the test user account."""
    response = requests.delete(
        f"{base_url}/profile",
        headers=auth_session["headers"],
        json={"password": auth_session["user"]["password"]},
        timeout=TEST_TIMEOUT
    )
    assert response.status_code == 200
    print("\n✅ Test user account deleted")

"""Organization management."""

from __future__ import annotations

import logging
import re
from typing import Optional

from wp_mcp.database import db

logger = logging.getLogger(__name__)


class OrganizationManager:
    """Manage organizations."""

    @staticmethod
    async def create_organization(
        owner_id: int,
        name: str,
        slug: Optional[str] = None,
        avatar: Optional[str] = None,
        banner: Optional[str] = None,
        bio: Optional[str] = None,
    ) -> dict:
        """Create a new organization.

        Args:
            owner_id: Owner user ID
            name: Organization name
            slug: URL-safe slug (auto-generated from name if not provided)
            avatar: Avatar URL
            banner: Banner URL
            bio: Bio text

        Returns:
            Created organization dict

        Raises:
            ValueError: If validation fails
        """
        # Validate name
        if not name or len(name) < 3 or len(name) > 255:
            raise ValueError("Organization name must be 3-255 characters")

        # Generate slug if not provided
        if not slug:
            slug = re.sub(r"[^a-z0-9-]", "", name.lower().replace(" ", "-"))
            slug = re.sub(r"-+", "-", slug).strip("-")

        # Validate slug
        if not slug or len(slug) < 3 or len(slug) > 100:
            raise ValueError("Slug must be 3-100 characters")
        if not re.match(r"^[a-z0-9-]+$", slug):
            raise ValueError("Slug can only contain lowercase letters, numbers, and dashes")

        # Check if slug is already taken
        existing = await db.fetchone(
            "SELECT id FROM wp_organizations WHERE slug = %s", (slug,)
        )
        if existing:
            raise ValueError("Organization slug already taken")

        # Validate bio
        if bio and len(bio) > 500:
            raise ValueError("Bio cannot exceed 500 characters")

        # Create organization
        org_id = await db.insert(
            """
            INSERT INTO wp_organizations (owner_id, name, slug, avatar, banner, bio)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (owner_id, name, slug, avatar, banner, bio),
        )

        # Add owner as member with owner role
        await db.insert(
            """
            INSERT INTO wp_organization_members (organization_id, user_id, role)
            VALUES (%s, %s, 'owner')
            """,
            (org_id, owner_id),
        )

        logger.info(f"Organization created: {name} (ID: {org_id}) by user {owner_id}")

        org = await OrganizationManager.get_organization(org_id)
        assert org is not None, "Organization should exist after creation"
        return org

    @staticmethod
    async def get_organization(org_id: int) -> Optional[dict]:
        """Get organization details.

        Args:
            org_id: Organization ID

        Returns:
            Organization dict with member count
        """
        org = await db.fetchone(
            """
            SELECT o.*, COUNT(DISTINCT m.user_id) as member_count
            FROM wp_organizations o
            LEFT JOIN wp_organization_members m ON m.organization_id = o.id
            WHERE o.id = %s
            GROUP BY o.id
            """,
            (org_id,),
        )
        return org

    @staticmethod
    async def get_organizations_for_user(user_id: int) -> list[dict]:
        """Get all organizations a user belongs to.

        Args:
            user_id: User ID

        Returns:
            List of organizations with user's role
        """
        orgs = await db.fetchall(
            """
            SELECT o.*, m.role as user_role, COUNT(DISTINCT m2.user_id) as member_count
            FROM wp_organizations o
            INNER JOIN wp_organization_members m ON m.organization_id = o.id
            LEFT JOIN wp_organization_members m2 ON m2.organization_id = o.id
            WHERE m.user_id = %s
            GROUP BY o.id, m.role
            ORDER BY o.created_at DESC
            """,
            (user_id,),
        )
        return orgs

    @staticmethod
    async def update_organization(
        org_id: int,
        user_id: int,
        name: Optional[str] = None,
        avatar: Optional[str] = None,
        banner: Optional[str] = None,
        bio: Optional[str] = None,
    ) -> dict:
        """Update organization.

        Args:
            org_id: Organization ID
            user_id: User ID (must be owner or admin)
            name: New name
            avatar: New avatar URL
            banner: New banner URL
            bio: New bio

        Returns:
            Updated organization dict

        Raises:
            ValueError: If validation fails or unauthorized
        """
        # Check if user has permission (owner or admin)
        member = await db.fetchone(
            """
            SELECT role FROM wp_organization_members
            WHERE organization_id = %s AND user_id = %s
            """,
            (org_id, user_id),
        )
        if not member or member["role"] not in ("owner", "admin"):
            raise ValueError("Unauthorized: Only owners and admins can update organization")

        # Validate name
        if name is not None and (len(name) < 3 or len(name) > 255):
            raise ValueError("Organization name must be 3-255 characters")

        # Validate bio
        if bio is not None and len(bio) > 500:
            raise ValueError("Bio cannot exceed 500 characters")

        # Build update query
        updates: list[str] = []
        params: list[str | int] = []

        if name is not None:
            updates.append("name = %s")
            params.append(name)
        if avatar is not None:
            updates.append("avatar = %s")
            params.append(avatar)
        if banner is not None:
            updates.append("banner = %s")
            params.append(banner)
        if bio is not None:
            updates.append("bio = %s")
            params.append(bio)

        if not updates:
            org = await OrganizationManager.get_organization(org_id)
            assert org is not None, "Organization should exist"
            return org

        params.append(org_id)
        query = f"UPDATE wp_organizations SET {', '.join(updates)} WHERE id = %s"

        await db.execute(query, tuple(params))
        logger.info(f"Organization {org_id} updated by user {user_id}")

        org = await OrganizationManager.get_organization(org_id)
        assert org is not None, "Organization should exist after update"
        return org

    @staticmethod
    async def delete_organization(org_id: int, user_id: int) -> bool:
        """Delete organization.

        Args:
            org_id: Organization ID
            user_id: User ID (must be owner)

        Returns:
            True if deleted

        Raises:
            ValueError: If unauthorized
        """
        # Check if user is owner
        member = await db.fetchone(
            """
            SELECT role FROM wp_organization_members
            WHERE organization_id = %s AND user_id = %s
            """,
            (org_id, user_id),
        )
        if not member or member["role"] != "owner":
            raise ValueError("Unauthorized: Only the owner can delete the organization")

        # Delete organization (cascade will delete members and invites)
        await db.execute("DELETE FROM wp_organizations WHERE id = %s", (org_id,))
        logger.info(f"Organization {org_id} deleted by user {user_id}")

        return True

    @staticmethod
    async def get_members(org_id: int) -> list[dict]:
        """Get organization members.

        Args:
            org_id: Organization ID

        Returns:
            List of members with user details
        """
        members = await db.fetchall(
            """
            SELECT m.*, u.email, u.username, u.name, u.avatar
            FROM wp_organization_members m
            INNER JOIN wp_users_auth u ON u.id = m.user_id
            WHERE m.organization_id = %s
            ORDER BY
                CASE m.role
                    WHEN 'owner' THEN 1
                    WHEN 'admin' THEN 2
                    WHEN 'member' THEN 3
                    WHEN 'viewer' THEN 4
                END,
                m.joined_at ASC
            """,
            (org_id,),
        )
        return members

    @staticmethod
    async def update_member_role(
        org_id: int, target_user_id: int, new_role: str, requester_user_id: int
    ) -> bool:
        """Update a member's role.

        Args:
            org_id: Organization ID
            target_user_id: User whose role to update
            new_role: New role (admin, member, viewer)
            requester_user_id: User making the request (must be owner or admin)

        Returns:
            True if updated

        Raises:
            ValueError: If validation fails or unauthorized
        """
        # Check requester permission
        requester = await db.fetchone(
            """
            SELECT role FROM wp_organization_members
            WHERE organization_id = %s AND user_id = %s
            """,
            (org_id, requester_user_id),
        )
        if not requester or requester["role"] not in ("owner", "admin"):
            raise ValueError("Unauthorized: Only owners and admins can update roles")

        # Can't change owner role
        if new_role == "owner":
            raise ValueError("Cannot assign owner role. Transfer ownership instead.")

        # Validate role
        if new_role not in ("admin", "member", "viewer"):
            raise ValueError("Invalid role. Must be: admin, member, or viewer")

        # Update role
        rows_affected = await db.execute(
            """
            UPDATE wp_organization_members
            SET role = %s
            WHERE organization_id = %s AND user_id = %s AND role != 'owner'
            """,
            (new_role, org_id, target_user_id),
        )

        if rows_affected == 0:
            raise ValueError("Member not found or cannot modify owner role")

        logger.info(
            f"User {target_user_id} role updated to {new_role} in org {org_id} by {requester_user_id}"
        )
        return True

    @staticmethod
    async def remove_member(
        org_id: int, target_user_id: int, requester_user_id: int
    ) -> bool:
        """Remove a member from organization.

        Args:
            org_id: Organization ID
            target_user_id: User to remove
            requester_user_id: User making the request (must be owner or admin)

        Returns:
            True if removed

        Raises:
            ValueError: If validation fails or unauthorized
        """
        # Check requester permission
        requester = await db.fetchone(
            """
            SELECT role FROM wp_organization_members
            WHERE organization_id = %s AND user_id = %s
            """,
            (org_id, requester_user_id),
        )
        if not requester or requester["role"] not in ("owner", "admin"):
            raise ValueError("Unauthorized: Only owners and admins can remove members")

        # Can't remove owner
        target = await db.fetchone(
            """
            SELECT role FROM wp_organization_members
            WHERE organization_id = %s AND user_id = %s
            """,
            (org_id, target_user_id),
        )
        if not target:
            raise ValueError("Member not found")
        if target["role"] == "owner":
            raise ValueError("Cannot remove the owner")

        # Remove member
        await db.execute(
            """
            DELETE FROM wp_organization_members
            WHERE organization_id = %s AND user_id = %s
            """,
            (org_id, target_user_id),
        )

        logger.info(
            f"User {target_user_id} removed from org {org_id} by {requester_user_id}"
        )
        return True

    @staticmethod
    async def transfer_ownership(
        org_id: int,
        current_owner_id: int,
        new_owner_id: int,
        password: str,
    ) -> bool:
        """Transfer organization ownership to another admin.

        Args:
            org_id: Organization ID
            current_owner_id: Current owner user ID
            new_owner_id: New owner user ID (must be an existing admin)
            password: Current owner's password for confirmation

        Returns:
            True if successful

        Raises:
            ValueError: If validation fails or unauthorized
        """
        # Verify current owner
        org = await db.fetchone(
            "SELECT owner_id FROM wp_organizations WHERE id = %s",
            (org_id,),
        )
        if not org or org["owner_id"] != current_owner_id:
            raise ValueError("Only the owner can transfer ownership")

        # Verify password
        import bcrypt
        user = await db.fetchone(
            "SELECT password_hash FROM wp_users_auth WHERE id = %s",
            (current_owner_id,),
        )
        if not user:
            raise ValueError("User not found")

        if not bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
            raise ValueError("Invalid password")

        # Verify new owner is an admin
        new_owner_member = await db.fetchone(
            """
            SELECT role FROM wp_organization_members
            WHERE organization_id = %s AND user_id = %s
            """,
            (org_id, new_owner_id),
        )
        if not new_owner_member:
            raise ValueError("New owner must be a member of the organization")
        if new_owner_member["role"] not in ["admin", "owner"]:
            raise ValueError("New owner must be an admin")

        # Perform transfer in transaction
        # 1. Update organization owner_id
        await db.execute(
            "UPDATE wp_organizations SET owner_id = %s WHERE id = %s",
            (new_owner_id, org_id),
        )

        # 2. Change current owner to admin
        await db.execute(
            """
            UPDATE wp_organization_members
            SET role = 'admin'
            WHERE organization_id = %s AND user_id = %s
            """,
            (org_id, current_owner_id),
        )

        # 3. Change new owner to owner role
        await db.execute(
            """
            UPDATE wp_organization_members
            SET role = 'owner'
            WHERE organization_id = %s AND user_id = %s
            """,
            (org_id, new_owner_id),
        )

        logger.info(
            f"Ownership of org {org_id} transferred from {current_owner_id} to {new_owner_id}"
        )
        return True

    @staticmethod
    async def search_organizations(
        query: Optional[str] = None,
        visibility: str = "public",
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """Search for organizations.

        Args:
            query: Search query (matches name or slug)
            visibility: Filter by visibility (public/private/all)
            limit: Maximum results to return
            offset: Results to skip

        Returns:
            List of organization dicts with member count
        """
        conditions = []
        params = []

        # Visibility filter
        if visibility != "all":
            conditions.append("o.visibility = %s")
            params.append(visibility)

        # Search query
        if query:
            conditions.append("(o.name LIKE %s OR o.slug LIKE %s)")
            search_term = f"%{query}%"
            params.extend([search_term, search_term])

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Get organizations with member count
        orgs = await db.fetchall(
            f"""
            SELECT
                o.id,
                o.name,
                o.slug,
                o.owner_id,
                o.avatar,
                o.banner,
                o.bio,
                o.visibility,
                o.created_at,
                COUNT(DISTINCT m.user_id) as member_count
            FROM wp_organizations o
            LEFT JOIN wp_organization_members m ON m.organization_id = o.id
            {where_clause}
            GROUP BY o.id
            ORDER BY o.created_at DESC
            LIMIT %s OFFSET %s
            """,
            tuple(params + [limit, offset]),
        )

        return orgs

    @staticmethod
    async def request_to_join(org_id: int, user_id: int) -> dict:
        """Request to join a public organization.

        Args:
            org_id: Organization ID
            user_id: User requesting to join

        Returns:
            Created invite dict

        Raises:
            ValueError: If validation fails
        """
        # Check if organization is public
        org = await db.fetchone(
            "SELECT visibility, owner_id FROM wp_organizations WHERE id = %s",
            (org_id,),
        )
        if not org:
            raise ValueError("Organization not found")

        if org["visibility"] != "public":
            raise ValueError("This organization is private")

        # Check if already a member
        existing = await db.fetchone(
            """
            SELECT id FROM wp_organization_members
            WHERE organization_id = %s AND user_id = %s
            """,
            (org_id, user_id),
        )
        if existing:
            raise ValueError("Already a member of this organization")

        # Check if already has a pending invite/request
        user = await db.fetchone(
            "SELECT email FROM wp_users_auth WHERE id = %s",
            (user_id,),
        )
        assert user is not None, "User should exist"
        existing_invite = await db.fetchone(
            """
            SELECT id FROM wp_organization_invites
            WHERE organization_id = %s AND invitee_email = %s AND status = 'pending'
            """,
            (org_id, user["email"]),
        )
        if existing_invite:
            raise ValueError("Already have a pending request")

        # Create invite/request (sent to owner, but can be auto-accepted for public orgs)
        # For now, auto-accept join requests for public orgs
        await db.insert(
            """
            INSERT INTO wp_organization_members (organization_id, user_id, role)
            VALUES (%s, %s, 'member')
            """,
            (org_id, user_id),
        )

        logger.info(f"User {user_id} joined public org {org_id}")

        # Log activity
        from wp_mcp.activity_manager import ActivityManager
        org_info = await db.fetchone("SELECT name FROM wp_organizations WHERE id = %s", (org_id,))
        await ActivityManager.log_activity(
            user_id,
            ActivityManager.ORGANIZATION_JOINED,
            org_id,
            {"organization_name": org_info["name"] if org_info else None}
        )

        org_result = await OrganizationManager.get_organization(org_id)
        assert org_result is not None, "Organization should exist after join"
        return org_result

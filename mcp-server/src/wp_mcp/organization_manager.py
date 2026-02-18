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

        return await OrganizationManager.get_organization(org_id)

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
        updates = []
        params = []

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
            return await OrganizationManager.get_organization(org_id)

        params.append(org_id)
        query = f"UPDATE wp_organizations SET {', '.join(updates)} WHERE id = %s"

        await db.execute(query, tuple(params))
        logger.info(f"Organization {org_id} updated by user {user_id}")

        return await OrganizationManager.get_organization(org_id)

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

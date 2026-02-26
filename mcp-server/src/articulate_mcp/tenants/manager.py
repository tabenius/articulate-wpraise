"""Tenant lifecycle management — orchestrates crypto, composer, Docker ops, and DB."""

import os
import re
import uuid
import logging
from typing import Any

from articulate_mcp.database import db as default_db
from articulate_mcp.tenants.crypto import TenantCrypto
from articulate_mcp.tenants.composer import TenantComposer
from articulate_mcp.tenants.docker_ops import TenantDockerOps
from articulate_mcp.tenants.routing import RESERVED_SUBDOMAINS, VIEWS

logger = logging.getLogger(__name__)

NAME_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")


class TenantManager:
    """Orchestrates tenant creation, updates, and deletion."""

    def __init__(
        self,
        encryption_key: str,
        base_domain: str = "ragbaz.xyz",
        template_dir: str | None = None,
        compose_output_dir: str | None = None,
    ):
        self.base_domain = base_domain
        self.crypto = TenantCrypto(encryption_key)
        self.composer = TenantComposer(template_dir=template_dir)
        self.docker_ops = TenantDockerOps(compose_dir=compose_output_dir)
        self.compose_output_dir = compose_output_dir
        self.db = default_db

    def _validate_name(self, name: str) -> None:
        if not NAME_RE.match(name):
            raise ValueError(f"Name must be DNS-safe (lowercase alphanumeric and hyphens): {name}")
        if name in RESERVED_SUBDOMAINS:
            raise ValueError(f"Name '{name}' is reserved")

    async def create_tenant(self, name: str, owner_user_id: int) -> dict[str, Any]:
        """Create and provision a new tenant.

        1. Validate name
        2. Generate secrets
        3. Insert DB records
        4. Render docker-compose
        5. Start Docker project
        """
        self._validate_name(name)

        # Check uniqueness
        existing = await self.db.fetchone(
            "SELECT id FROM tenants WHERE name = %s", (name,)
        )
        if existing:
            raise ValueError(f"Tenant name '{name}' already exists")

        tenant_id = uuid.uuid4().hex[:32]
        domain = f"{name}.{self.base_domain}"

        # Generate and encrypt secrets
        secrets = self.crypto.generate_secrets()
        encrypted = self.crypto.encrypt_secrets(secrets)

        # Insert tenant record
        await self.db.execute(
            """INSERT INTO tenants (id, name, slug, domain, default_view, docker_project,
                   owner_user_id, wp_url, wp_graphql_endpoint, wp_admin_user,
                   status, created_at)
               VALUES (%s, %s, %s, %s, 'wordpress', %s, %s, %s, %s, 'admin', 'provisioning', NOW())""",
            (
                tenant_id, name, name, domain, f"tenant_{tenant_id}",
                owner_user_id,
                f"http://tenant_{tenant_id}_wordpress:80",
                f"http://tenant_{tenant_id}_wordpress:80/graphql",
            ),
        )

        # Insert secrets
        await self.db.execute(
            """INSERT INTO tenant_secrets (tenant_id, db_password, db_root_password, wp_admin_password)
               VALUES (%s, %s, %s, %s)""",
            (tenant_id, encrypted["db_password"], encrypted["db_root_password"], encrypted["wp_admin_password"]),
        )

        # Insert tenant_users (owner)
        await self.db.execute(
            "INSERT INTO tenant_users (tenant_id, user_id, role) VALUES (%s, %s, 'owner')",
            (tenant_id, owner_user_id),
        )

        # Render and save docker-compose
        rendered = self.composer.render(
            tenant_id=tenant_id,
            tenant_name=name,
            db_password=secrets["db_password"],
            db_root_password=secrets["db_root_password"],
        )
        compose_path = self.composer.save(rendered, tenant_name=name, output_dir=self.compose_output_dir)

        # Start Docker project
        try:
            self.docker_ops.up(tenant_id, compose_path)
            await self.db.execute(
                "UPDATE tenants SET status = 'running' WHERE id = %s", (tenant_id,)
            )
        except Exception as e:
            logger.error("Failed to start tenant %s: %s", tenant_id, e)
            await self.db.execute(
                "UPDATE tenants SET status = 'error' WHERE id = %s", (tenant_id,)
            )
            raise

        return {
            "tenant_id": tenant_id,
            "name": name,
            "domain": domain,
            "default_view": "wordpress",
            "status": "running",
        }

    async def delete_tenant(self, tenant_id: str) -> bool:
        """Stop containers, remove volumes, delete DB records."""
        tenant = await self.db.fetchone(
            "SELECT id, name FROM tenants WHERE id = %s", (tenant_id,)
        )
        if not tenant:
            return False

        try:
            self.docker_ops.down(tenant_id, volumes=True)
        except Exception as e:
            logger.error("Failed to stop tenant %s containers: %s", tenant_id, e)

        await self.db.execute("DELETE FROM tenants WHERE id = %s", (tenant_id,))
        return True

    async def get_tenant(self, tenant_id: str) -> dict[str, Any] | None:
        return await self.db.fetchone(
            """SELECT id, name, domain, default_view, status, created_at, updated_at
               FROM tenants WHERE id = %s""",
            (tenant_id,),
        )

    async def list_tenants(self, owner_user_id: int) -> list[dict[str, Any]]:
        return await self.db.fetchall(
            """SELECT t.id, t.name, t.domain, t.default_view, t.status, tu.role, t.created_at
               FROM tenants t
               JOIN tenant_users tu ON t.id = tu.tenant_id
               WHERE tu.user_id = %s AND t.status != 'deleted'
               ORDER BY t.created_at DESC""",
            (owner_user_id,),
        )

    async def set_default_view(self, tenant_id: str, view: str) -> bool:
        if view not in VIEWS:
            raise ValueError(f"Invalid view: {view}. Must be one of: {VIEWS}")
        result = await self.db.execute(
            "UPDATE tenants SET default_view = %s WHERE id = %s",
            (view, tenant_id),
        )
        return result > 0

    async def add_custom_domain(self, tenant_id: str, external_domain: str, target_view: str) -> int:
        if target_view not in VIEWS:
            raise ValueError(f"Invalid view: {target_view}")
        return await self.db.insert(
            """INSERT INTO tenant_domains (tenant_id, external_domain, target_view)
               VALUES (%s, %s, %s)""",
            (tenant_id, external_domain, target_view),
        )

    async def remove_custom_domain(self, domain_id: int) -> bool:
        result = await self.db.execute(
            "DELETE FROM tenant_domains WHERE id = %s", (domain_id,)
        )
        return result > 0

    async def verify_custom_domain(self, domain_id: int) -> bool:
        """Mark a custom domain as verified. Actual DNS check is done by caller."""
        result = await self.db.execute(
            "UPDATE tenant_domains SET verified = TRUE WHERE id = %s", (domain_id,)
        )
        return result > 0

# Multi-Tenant Views Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Evolve Articulate into a multi-tenant platform where each tenant gets an isolated WordPress + Faust + Astro stack, routed via subdomains on ragbaz.cc with support for custom external domains.

**Architecture:** Shared control plane (webedit, MCP server, Celery, Redis, shared MariaDB) manages per-tenant Docker Compose projects (WordPress + MariaDB + Faust + Astro). Caddy uses wildcard `*.ragbaz.cc` with dynamic upstream resolution via a route resolver endpoint on the MCP server. Custom external domains use on-demand TLS.

**Tech Stack:** Python 3.12, python-on-whales (Docker SDK), Jinja2 templates, Caddy dynamic upstreams, Faust.js, Astro SSR, aiomysql, Fernet encryption, Celery

---

## Task 1: Database Migration — Evolve Tenant Schema

The existing migration 001 creates `tenants`, `tenant_users`, `tenant_usage`. We need a new migration that adds columns for Docker-provisioned tenants and creates `tenant_secrets` and `tenant_domains` tables.

**Files:**
- Create: `mcp-server/migrations/002_tenant_views_and_domains.sql`

**Step 1: Write the migration SQL**

```sql
-- 002_tenant_views_and_domains.sql
-- Add Docker provisioning support, views, and custom domain mapping

-- Add new columns to tenants table
ALTER TABLE tenants
    ADD COLUMN domain VARCHAR(255) AFTER slug,
    ADD COLUMN default_view ENUM('wordpress','faust','astro') NOT NULL DEFAULT 'wordpress' AFTER domain,
    ADD COLUMN docker_project VARCHAR(100) AFTER default_view,
    ADD INDEX idx_name (name),
    ADD INDEX idx_domain (domain);

-- Update status enum to include provisioning states
ALTER TABLE tenants
    MODIFY COLUMN status ENUM('provisioning','running','stopped','error','active','suspended','deleted') DEFAULT 'provisioning';

-- Tenant secrets (encrypted, for Docker-provisioned instances)
CREATE TABLE IF NOT EXISTS tenant_secrets (
    tenant_id VARCHAR(36) PRIMARY KEY,
    db_password VARBINARY(512) NOT NULL,
    db_root_password VARBINARY(512) NOT NULL,
    wp_admin_password VARBINARY(512) NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Custom domain mappings
CREATE TABLE IF NOT EXISTS tenant_domains (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    external_domain VARCHAR(255) NOT NULL UNIQUE,
    target_view ENUM('wordpress','faust','astro') NOT NULL,
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    INDEX idx_tenant (tenant_id),
    INDEX idx_domain (external_domain)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Step 2: Run the migration**

```bash
docker compose -f docker-compose.production.yml exec mcp-server python -m scripts.run_migrations
```

If the migration runner doesn't support running from inside the container, run it directly:

```bash
cd mcp-server && python scripts/run-migrations.py
```

**Step 3: Commit**

```bash
git add mcp-server/migrations/002_tenant_views_and_domains.sql
git commit -m "feat: add migration for tenant views and custom domains"
```

---

## Task 2: Tenant Crypto Module

Extract and improve secret generation from `spawn.py`. Random secrets, Fernet encryption.

**Files:**
- Create: `mcp-server/src/wp_mcp/tenants/__init__.py`
- Create: `mcp-server/src/wp_mcp/tenants/crypto.py`
- Test: `mcp-server/tests/test_tenant_crypto.py`

**Step 1: Create the tenants package**

```python
# mcp-server/src/wp_mcp/tenants/__init__.py
"""Multi-tenant infrastructure management."""
```

**Step 2: Write the failing test**

```python
# mcp-server/tests/test_tenant_crypto.py
import os
import pytest
from cryptography.fernet import Fernet


@pytest.fixture
def crypto():
    """Create a TenantCrypto instance with a test key."""
    os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    from wp_mcp.tenants.crypto import TenantCrypto
    return TenantCrypto(os.environ["ENCRYPTION_KEY"])


def test_generate_secrets_returns_all_fields(crypto):
    secrets = crypto.generate_secrets()
    assert "db_password" in secrets
    assert "db_root_password" in secrets
    assert "wp_admin_password" in secrets
    assert len(secrets["db_password"]) >= 24
    assert len(secrets["db_root_password"]) >= 24
    assert len(secrets["wp_admin_password"]) >= 24


def test_generate_secrets_are_unique(crypto):
    s1 = crypto.generate_secrets()
    s2 = crypto.generate_secrets()
    assert s1["db_password"] != s2["db_password"]


def test_encrypt_decrypt_roundtrip(crypto):
    original = "my-secret-password"
    encrypted = crypto.encrypt(original)
    assert encrypted != original
    decrypted = crypto.decrypt(encrypted)
    assert decrypted == original


def test_encrypt_secrets_returns_bytes(crypto):
    secrets = crypto.generate_secrets()
    encrypted = crypto.encrypt_secrets(secrets)
    assert isinstance(encrypted["db_password"], bytes)
    assert isinstance(encrypted["db_root_password"], bytes)
    assert isinstance(encrypted["wp_admin_password"], bytes)


def test_decrypt_secrets_roundtrip(crypto):
    secrets = crypto.generate_secrets()
    encrypted = crypto.encrypt_secrets(secrets)
    decrypted = crypto.decrypt_secrets(encrypted)
    assert decrypted == secrets
```

**Step 3: Run test to verify it fails**

```bash
cd mcp-server && python -m pytest tests/test_tenant_crypto.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'wp_mcp.tenants.crypto'`

**Step 4: Write the implementation**

```python
# mcp-server/src/wp_mcp/tenants/crypto.py
"""Secret generation and encryption for tenant provisioning."""

import secrets
import string
from cryptography.fernet import Fernet


class TenantCrypto:
    """Generates and encrypts tenant secrets."""

    def __init__(self, encryption_key: str):
        self.cipher = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)

    def _generate_password(self, length: int = 32) -> str:
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))

    def generate_secrets(self) -> dict[str, str]:
        return {
            "db_password": self._generate_password(),
            "db_root_password": self._generate_password(),
            "wp_admin_password": self._generate_password(),
        }

    def encrypt(self, value: str) -> bytes:
        return self.cipher.encrypt(value.encode())

    def decrypt(self, value: bytes) -> str:
        return self.cipher.decrypt(value).decode()

    def encrypt_secrets(self, secrets_dict: dict[str, str]) -> dict[str, bytes]:
        return {k: self.encrypt(v) for k, v in secrets_dict.items()}

    def decrypt_secrets(self, encrypted: dict[str, bytes]) -> dict[str, str]:
        return {k: self.decrypt(v) for k, v in encrypted.items()}
```

**Step 5: Run test to verify it passes**

```bash
cd mcp-server && python -m pytest tests/test_tenant_crypto.py -v
```

Expected: All PASS

**Step 6: Commit**

```bash
git add mcp-server/src/wp_mcp/tenants/ mcp-server/tests/test_tenant_crypto.py
git commit -m "feat: add tenant crypto module for secret generation and encryption"
```

---

## Task 3: Tenant Composer — Jinja2 Template Rendering

Renders per-tenant docker-compose YAML from the existing template. Replaces the core logic of `spawn.py`.

**Files:**
- Create: `mcp-server/src/wp_mcp/tenants/composer.py`
- Modify: `templates/docker-compose-tenant.yml` (update for views)
- Test: `mcp-server/tests/test_tenant_composer.py`

**Step 1: Update the Jinja2 template**

Replace `templates/docker-compose-tenant.yml` with the updated version that includes Faust and Astro properly, uses the new naming conventions, and fixes the issues in the existing template (duplicate `networks` key on redis, `h.hexdigits()` typo in spawn.py):

```yaml
# templates/docker-compose-tenant.yml
version: "3.9"

name: tenant_{{TENANT_ID}}

services:

  wordpress:
    image: wordpress:6.4-php8.2-apache
    container_name: tenant_{{TENANT_ID}}_wordpress
    restart: unless-stopped
    depends_on:
      mariadb:
        condition: service_healthy
    networks:
      - proxy_net
      - tenant_{{TENANT_ID}}_net
      - control_net
    volumes:
      - wp_data:/var/www/html
    environment:
      WORDPRESS_DB_HOST: mariadb:3306
      WORDPRESS_DB_NAME: wp
      WORDPRESS_DB_USER: wp
      WORDPRESS_DB_PASSWORD: "{{DB_PASSWORD}}"
      WORDPRESS_CONFIG_EXTRA: |
        define('WP_HOME', 'https://wordpress.{{TENANT_NAME}}.ragbaz.cc');
        define('WP_SITEURL', 'https://wordpress.{{TENANT_NAME}}.ragbaz.cc');
    mem_limit: 512m
    cpus: 1.0
    pids_limit: 200
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
    tmpfs:
      - /tmp
    labels:
      articulate.tenant: "{{TENANT_ID}}"
      articulate.tenant.name: "{{TENANT_NAME}}"
      articulate.service: wordpress

  mariadb:
    image: mariadb:10.11
    container_name: tenant_{{TENANT_ID}}_mariadb
    restart: unless-stopped
    networks:
      - tenant_{{TENANT_ID}}_net
    volumes:
      - db_data:/var/lib/mysql
    environment:
      MYSQL_ROOT_PASSWORD: "{{DB_ROOT_PASSWORD}}"
      MYSQL_DATABASE: wp
      MYSQL_USER: wp
      MYSQL_PASSWORD: "{{DB_PASSWORD}}"
    command:
      - --transaction-isolation=READ-COMMITTED
      - --binlog-format=ROW
      - --innodb-buffer-pool-size=128M
      - --max-connections=50
    mem_limit: 512m
    cpus: 1.0
    pids_limit: 200
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
    tmpfs:
      - /tmp
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 20s
      timeout: 5s
      retries: 5

  faust:
    image: articulate-faust:latest
    container_name: tenant_{{TENANT_ID}}_faust
    restart: unless-stopped
    depends_on:
      - wordpress
    networks:
      - proxy_net
      - tenant_{{TENANT_ID}}_net
    environment:
      NEXT_PUBLIC_WORDPRESS_URL: http://tenant_{{TENANT_ID}}_wordpress:80
      NEXT_PUBLIC_GRAPHQL_ENDPOINT: http://tenant_{{TENANT_ID}}_wordpress:80/graphql
      TENANT_NAME: "{{TENANT_NAME}}"
      SITE_URL: "https://faust.{{TENANT_NAME}}.ragbaz.cc"
    mem_limit: 256m
    cpus: 0.5
    labels:
      articulate.tenant: "{{TENANT_ID}}"
      articulate.service: faust

  astro:
    image: articulate-astro:latest
    container_name: tenant_{{TENANT_ID}}_astro
    restart: unless-stopped
    depends_on:
      - wordpress
    networks:
      - proxy_net
      - tenant_{{TENANT_ID}}_net
    environment:
      WORDPRESS_URL: http://tenant_{{TENANT_ID}}_wordpress:80
      WORDPRESS_GRAPHQL_URL: http://tenant_{{TENANT_ID}}_wordpress:80/graphql
      TENANT_NAME: "{{TENANT_NAME}}"
      SITE_URL: "https://astro.{{TENANT_NAME}}.ragbaz.cc"
    mem_limit: 256m
    cpus: 0.5
    labels:
      articulate.tenant: "{{TENANT_ID}}"
      articulate.service: astro

networks:
  proxy_net:
    external: true
  control_net:
    external: true
  tenant_{{TENANT_ID}}_net:
    driver: bridge
    internal: true

volumes:
  wp_data:
    name: tenant_{{TENANT_ID}}_wp_data
  db_data:
    name: tenant_{{TENANT_ID}}_db_data
```

**Step 2: Write the failing test**

```python
# mcp-server/tests/test_tenant_composer.py
import os
import yaml
import pytest


@pytest.fixture
def composer():
    from wp_mcp.tenants.composer import TenantComposer
    # Templates are in the project root /templates directory
    template_dir = os.path.join(os.path.dirname(__file__), "..", "..", "templates")
    return TenantComposer(template_dir=template_dir)


def test_render_returns_valid_yaml(composer):
    result = composer.render(
        tenant_id="abc123",
        tenant_name="testsite",
        db_password="secret1",
        db_root_password="secret2",
    )
    parsed = yaml.safe_load(result)
    assert parsed["name"] == "tenant_abc123"
    assert "wordpress" in parsed["services"]
    assert "mariadb" in parsed["services"]
    assert "faust" in parsed["services"]
    assert "astro" in parsed["services"]


def test_render_sets_container_names(composer):
    result = composer.render(
        tenant_id="abc123",
        tenant_name="testsite",
        db_password="s",
        db_root_password="s",
    )
    parsed = yaml.safe_load(result)
    assert parsed["services"]["wordpress"]["container_name"] == "tenant_abc123_wordpress"
    assert parsed["services"]["faust"]["container_name"] == "tenant_abc123_faust"
    assert parsed["services"]["astro"]["container_name"] == "tenant_abc123_astro"


def test_render_sets_tenant_network(composer):
    result = composer.render(
        tenant_id="abc123",
        tenant_name="testsite",
        db_password="s",
        db_root_password="s",
    )
    parsed = yaml.safe_load(result)
    assert "tenant_abc123_net" in parsed["networks"]
    assert parsed["networks"]["tenant_abc123_net"]["internal"] is True


def test_save_writes_file(composer, tmp_path):
    yml = composer.render(
        tenant_id="abc123",
        tenant_name="testsite",
        db_password="s",
        db_root_password="s",
    )
    path = composer.save(yml, tenant_name="testsite", output_dir=str(tmp_path))
    assert os.path.exists(path)
    assert "testsite" in path
    content = open(path).read()
    assert "tenant_abc123" in content
```

**Step 3: Run test to verify it fails**

```bash
cd mcp-server && python -m pytest tests/test_tenant_composer.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'wp_mcp.tenants.composer'`

**Step 4: Write the implementation**

```python
# mcp-server/src/wp_mcp/tenants/composer.py
"""Render per-tenant docker-compose YAML from Jinja2 templates."""

import os
from jinja2 import Environment, FileSystemLoader


class TenantComposer:
    """Renders docker-compose files for tenant stacks."""

    def __init__(self, template_dir: str | None = None):
        if template_dir is None:
            # Default: project root /templates
            template_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "templates")
        self.template_dir = os.path.abspath(template_dir)
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=False,
            keep_trailing_newline=True,
        )

    def render(
        self,
        tenant_id: str,
        tenant_name: str,
        db_password: str,
        db_root_password: str,
        template_name: str = "docker-compose-tenant.yml",
    ) -> str:
        template = self.env.get_template(template_name)
        return template.render(
            TENANT_ID=tenant_id,
            TENANT_NAME=tenant_name,
            DB_PASSWORD=db_password,
            DB_ROOT_PASSWORD=db_root_password,
        )

    def save(self, rendered: str, tenant_name: str, output_dir: str | None = None) -> str:
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(self.template_dir), "tenants")
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, f"docker-compose-{tenant_name}.yml")
        with open(path, "w") as f:
            f.write(rendered)
        return path
```

**Step 5: Run test to verify it passes**

```bash
cd mcp-server && python -m pytest tests/test_tenant_composer.py -v
```

Expected: All PASS

**Step 6: Commit**

```bash
git add templates/docker-compose-tenant.yml mcp-server/src/wp_mcp/tenants/composer.py mcp-server/tests/test_tenant_composer.py
git commit -m "feat: add tenant composer for Jinja2 docker-compose rendering"
```

---

## Task 4: Docker Operations Module

Wraps `python-on-whales` to manage per-tenant compose projects.

**Files:**
- Create: `mcp-server/src/wp_mcp/tenants/docker_ops.py`
- Test: `mcp-server/tests/test_docker_ops.py`

**Step 1: Add python-on-whales dependency**

In `mcp-server/pyproject.toml`, add to `[project.dependencies]`:

```
python-on-whales>=0.70.0
```

Install:

```bash
cd mcp-server && uv pip install -e ".[dev]"
```

**Step 2: Write the failing test**

```python
# mcp-server/tests/test_docker_ops.py
"""Tests for Docker operations module.

These tests mock the Docker client since we don't want to create
real containers during testing.
"""
from unittest.mock import MagicMock, patch, AsyncMock
import pytest


@pytest.fixture
def docker_ops():
    with patch("wp_mcp.tenants.docker_ops.DockerClient") as mock_docker:
        from wp_mcp.tenants.docker_ops import TenantDockerOps
        ops = TenantDockerOps(compose_dir="/tmp/tenants")
        ops.docker = mock_docker.return_value
        yield ops


def test_project_name(docker_ops):
    assert docker_ops.project_name("abc123") == "tenant_abc123"


def test_up_calls_compose(docker_ops):
    docker_ops.up("abc123", "/tmp/tenants/docker-compose-test.yml")
    docker_ops.docker.compose.up.assert_called_once()


def test_down_calls_compose(docker_ops):
    docker_ops.down("abc123")
    docker_ops.docker.compose.down.assert_called_once()


def test_status_returns_dict(docker_ops):
    mock_container = MagicMock()
    mock_container.name = "tenant_abc123_wordpress"
    mock_container.state.status = "running"
    docker_ops.docker.compose.ps.return_value = [mock_container]
    status = docker_ops.status("abc123")
    assert isinstance(status, dict)


def test_container_name(docker_ops):
    assert docker_ops.container_name("abc123", "wordpress") == "tenant_abc123_wordpress"
    assert docker_ops.container_name("abc123", "faust") == "tenant_abc123_faust"
```

**Step 3: Run test to verify it fails**

```bash
cd mcp-server && python -m pytest tests/test_docker_ops.py -v
```

Expected: FAIL

**Step 4: Write the implementation**

```python
# mcp-server/src/wp_mcp/tenants/docker_ops.py
"""Docker operations for tenant lifecycle management."""

import logging
from python_on_whales import DockerClient

logger = logging.getLogger(__name__)


class TenantDockerOps:
    """Manages Docker Compose projects for tenants."""

    def __init__(self, compose_dir: str | None = None):
        self.compose_dir = compose_dir
        self.docker = DockerClient()

    def project_name(self, tenant_id: str) -> str:
        return f"tenant_{tenant_id}"

    def container_name(self, tenant_id: str, service: str) -> str:
        return f"tenant_{tenant_id}_{service}"

    def up(self, tenant_id: str, compose_file: str) -> None:
        """Start a tenant's Docker Compose project."""
        project = self.project_name(tenant_id)
        logger.info("Starting tenant %s from %s", tenant_id, compose_file)
        self.docker.compose.up(
            compose_files=[compose_file],
            project_name=project,
            detach=True,
            build=False,
            quiet=True,
        )
        logger.info("Tenant %s started", tenant_id)

    def down(self, tenant_id: str, compose_file: str | None = None, volumes: bool = False) -> None:
        """Stop and remove a tenant's Docker Compose project."""
        project = self.project_name(tenant_id)
        logger.info("Stopping tenant %s (volumes=%s)", tenant_id, volumes)
        kwargs = {"project_name": project, "volumes": volumes}
        if compose_file:
            kwargs["compose_files"] = [compose_file]
        self.docker.compose.down(**kwargs)
        logger.info("Tenant %s stopped", tenant_id)

    def status(self, tenant_id: str, compose_file: str | None = None) -> dict[str, str]:
        """Get status of all containers in a tenant project."""
        project = self.project_name(tenant_id)
        kwargs = {"project_name": project}
        if compose_file:
            kwargs["compose_files"] = [compose_file]
        try:
            containers = self.docker.compose.ps(**kwargs)
            return {c.name: c.state.status for c in containers}
        except Exception as e:
            logger.error("Failed to get status for tenant %s: %s", tenant_id, e)
            return {}

    def is_healthy(self, tenant_id: str) -> bool:
        """Check if the tenant's WordPress container is running."""
        statuses = self.status(tenant_id)
        wp_name = self.container_name(tenant_id, "wordpress")
        return statuses.get(wp_name) == "running"
```

**Step 5: Run test to verify it passes**

```bash
cd mcp-server && python -m pytest tests/test_docker_ops.py -v
```

Expected: All PASS

**Step 6: Commit**

```bash
git add mcp-server/src/wp_mcp/tenants/docker_ops.py mcp-server/tests/test_docker_ops.py mcp-server/pyproject.toml
git commit -m "feat: add Docker operations module for tenant lifecycle"
```

---

## Task 5: Route Resolver — Caddy Dynamic Upstream

The MCP server endpoint that Caddy calls to resolve Host headers to container upstreams.

**Files:**
- Create: `mcp-server/src/wp_mcp/tenants/routing.py`
- Create: `mcp-server/src/wp_mcp/routes/routing.py`
- Test: `mcp-server/tests/test_routing.py`

**Step 1: Write the failing test**

```python
# mcp-server/tests/test_routing.py
import pytest
from unittest.mock import AsyncMock, patch

from wp_mcp.tenants.routing import RouteResolver


@pytest.fixture
def resolver():
    return RouteResolver(base_domain="ragbaz.cc")


def test_parse_view_subdomain(resolver):
    result = resolver.parse_host("faust.tenant1.ragbaz.cc")
    assert result == {"tenant_name": "tenant1", "view": "faust"}


def test_parse_astro_subdomain(resolver):
    result = resolver.parse_host("astro.mysite.ragbaz.cc")
    assert result == {"tenant_name": "mysite", "view": "astro"}


def test_parse_wordpress_subdomain(resolver):
    result = resolver.parse_host("wordpress.tenant1.ragbaz.cc")
    assert result == {"tenant_name": "tenant1", "view": "wordpress"}


def test_parse_bare_subdomain(resolver):
    result = resolver.parse_host("tenant1.ragbaz.cc")
    assert result == {"tenant_name": "tenant1", "view": None}


def test_parse_external_domain(resolver):
    result = resolver.parse_host("myblog.com")
    assert result == {"external_domain": "myblog.com"}


def test_parse_control_plane_returns_none(resolver):
    assert resolver.parse_host("app.ragbaz.cc") is None
    assert resolver.parse_host("my.ragbaz.cc") is None


def test_upstream_for_view():
    resolver = RouteResolver(base_domain="ragbaz.cc")
    assert resolver.upstream_for("abc123", "wordpress") == "tenant_abc123_wordpress:80"
    assert resolver.upstream_for("abc123", "faust") == "tenant_abc123_faust:3000"
    assert resolver.upstream_for("abc123", "astro") == "tenant_abc123_astro:4321"
```

**Step 2: Run test to verify it fails**

```bash
cd mcp-server && python -m pytest tests/test_routing.py -v
```

Expected: FAIL

**Step 3: Write the routing resolver**

```python
# mcp-server/src/wp_mcp/tenants/routing.py
"""Route resolver for Caddy dynamic upstream resolution."""

import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

VIEW_PORTS = {
    "wordpress": 80,
    "faust": 3000,
    "astro": 4321,
}

VIEWS = set(VIEW_PORTS.keys())

# Control plane subdomains that should not be treated as tenants
RESERVED_SUBDOMAINS = {"app", "my", "www", "api", "docs", "mail", "smtp"}


class RouteResolver:
    """Resolves Host headers to Docker container upstreams."""

    def __init__(self, base_domain: str = "ragbaz.cc"):
        self.base_domain = base_domain
        # Match: {view}.{tenant}.ragbaz.cc or {tenant}.ragbaz.cc
        self.subdomain_re = re.compile(
            rf"^(?:(?P<view>[^.]+)\.)?(?P<tenant>[^.]+)\.{re.escape(base_domain)}$"
        )

    def parse_host(self, host: str) -> dict[str, Any] | None:
        """Parse a Host header into tenant/view info.

        Returns:
            - {"tenant_name": str, "view": str} for view.tenant.domain
            - {"tenant_name": str, "view": None} for tenant.domain (bare)
            - {"external_domain": str} for external domains
            - None for control plane subdomains
        """
        # Strip port if present
        host = host.split(":")[0].lower()

        match = self.subdomain_re.match(host)
        if match:
            view = match.group("view")
            tenant = match.group("tenant")

            # Control plane subdomains
            if tenant in RESERVED_SUBDOMAINS and view is None:
                return None

            # {view}.{tenant}.ragbaz.cc
            if view and view in VIEWS:
                return {"tenant_name": tenant, "view": view}

            # {tenant}.ragbaz.cc (view is None, or view is actually the tenant name)
            if view is None:
                return {"tenant_name": tenant, "view": None}

            # {something}.{tenant}.ragbaz.cc where something is not a known view
            # Treat the full thing as tenant_name=view, view=None?
            # Actually this is: view=something, tenant=tenant — but view is unknown
            # Fall through to external domain handling
            return None

        # Not a subdomain of base_domain — external domain
        if not host.endswith(f".{self.base_domain}") and host != self.base_domain:
            return {"external_domain": host}

        return None

    def upstream_for(self, tenant_id: str, view: str) -> str:
        """Get the Docker upstream address for a tenant view."""
        port = VIEW_PORTS.get(view, 80)
        return f"tenant_{tenant_id}_{view}:{port}"
```

**Step 4: Write the HTTP endpoint handler**

```python
# mcp-server/src/wp_mcp/routes/routing.py
"""HTTP endpoints for Caddy dynamic upstream resolution."""

import json
import logging
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from wp_mcp.database import db
from wp_mcp.tenants.routing import RouteResolver

logger = logging.getLogger(__name__)

resolver = RouteResolver()


async def resolve_upstream(request: Request) -> Response:
    """Caddy calls this to resolve a Host header to an upstream.

    Caddy sends the original Host header. We look up the tenant
    and return the upstream address.

    Returns JSON: [{"dial": "container:port"}] for Caddy dynamic upstreams.
    Returns 404 if no match found.
    """
    host = request.headers.get("X-Forwarded-Host") or request.headers.get("Host", "")
    parsed = resolver.parse_host(host)

    if parsed is None:
        return Response(status_code=404)

    if "external_domain" in parsed:
        # Look up custom domain
        row = await db.fetchone(
            """SELECT t.id, td.target_view
               FROM tenant_domains td
               JOIN tenants t ON t.id = td.tenant_id
               WHERE td.external_domain = %s AND td.verified = TRUE AND t.status = 'running'""",
            (parsed["external_domain"],),
        )
        if not row:
            return Response(status_code=404)
        upstream = resolver.upstream_for(row["id"], row["target_view"])
        return JSONResponse([{"dial": upstream}])

    tenant_name = parsed["tenant_name"]
    view = parsed.get("view")

    # Look up tenant by name
    tenant = await db.fetchone(
        "SELECT id, default_view FROM tenants WHERE name = %s AND status = 'running'",
        (tenant_name,),
    )
    if not tenant:
        return Response(status_code=404)

    if view is None:
        view = tenant["default_view"]

    upstream = resolver.upstream_for(tenant["id"], view)
    return JSONResponse([{"dial": upstream}])


async def tls_check(request: Request) -> Response:
    """Caddy on-demand TLS check.

    Caddy calls GET /routing/tls-check?domain=X before fetching a cert.
    Return 200 to allow, 404 to deny.
    """
    domain = request.query_params.get("domain", "")
    if not domain:
        return Response(status_code=404)

    # Allow all *.ragbaz.cc (covered by wildcard cert)
    if domain.endswith(".ragbaz.cc"):
        return Response(status_code=200)

    # Check custom domains
    row = await db.fetchone(
        "SELECT id FROM tenant_domains WHERE external_domain = %s AND verified = TRUE",
        (domain,),
    )
    if row:
        return Response(status_code=200)

    return Response(status_code=404)
```

**Step 5: Run test to verify it passes**

```bash
cd mcp-server && python -m pytest tests/test_routing.py -v
```

Expected: All PASS

**Step 6: Commit**

```bash
git add mcp-server/src/wp_mcp/tenants/routing.py mcp-server/src/wp_mcp/routes/routing.py mcp-server/tests/test_routing.py
git commit -m "feat: add route resolver for Caddy dynamic upstream resolution"
```

---

## Task 6: Tenant Manager — CRUD Orchestration

Replaces the existing `tenant_manager.py` with one that orchestrates crypto + composer + docker_ops + DB.

**Files:**
- Create: `mcp-server/src/wp_mcp/tenants/manager.py`
- Test: `mcp-server/tests/test_tenant_manager_new.py`

**Step 1: Write the failing test**

```python
# mcp-server/tests/test_tenant_manager_new.py
"""Tests for TenantManager orchestration.

Mocks DB and Docker operations to test the orchestration logic.
"""
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from cryptography.fernet import Fernet


@pytest.fixture
def manager():
    os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    with patch("wp_mcp.tenants.manager.db") as mock_db, \
         patch("wp_mcp.tenants.manager.TenantDockerOps") as mock_docker_cls:
        mock_db.fetchone = AsyncMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=1)
        mock_db.insert = AsyncMock(return_value=1)

        from wp_mcp.tenants.manager import TenantManager
        mgr = TenantManager(
            encryption_key=os.environ["ENCRYPTION_KEY"],
            template_dir="/tmp/templates",
            compose_output_dir="/tmp/tenants",
        )
        mgr.docker_ops = mock_docker_cls.return_value
        mgr.db = mock_db
        yield mgr


@pytest.mark.asyncio
async def test_create_tenant_returns_tenant_id(manager):
    result = await manager.create_tenant(name="testsite", owner_user_id=1)
    assert "tenant_id" in result
    assert result["name"] == "testsite"
    assert result["domain"] == "testsite.ragbaz.cc"


@pytest.mark.asyncio
async def test_create_tenant_validates_name(manager):
    with pytest.raises(ValueError, match="DNS-safe"):
        await manager.create_tenant(name="INVALID NAME!", owner_user_id=1)


@pytest.mark.asyncio
async def test_create_tenant_rejects_reserved_name(manager):
    with pytest.raises(ValueError, match="reserved"):
        await manager.create_tenant(name="app", owner_user_id=1)


@pytest.mark.asyncio
async def test_set_default_view(manager):
    manager.db.fetchone = AsyncMock(return_value={"id": "abc", "name": "test", "default_view": "wordpress"})
    manager.db.execute = AsyncMock(return_value=1)
    result = await manager.set_default_view("abc", "faust")
    assert result is True
    manager.db.execute.assert_called()


@pytest.mark.asyncio
async def test_set_default_view_rejects_invalid(manager):
    with pytest.raises(ValueError, match="Invalid view"):
        await manager.set_default_view("abc", "nextjs")
```

**Step 2: Run test to verify it fails**

```bash
cd mcp-server && python -m pytest tests/test_tenant_manager_new.py -v
```

Expected: FAIL

**Step 3: Write the implementation**

```python
# mcp-server/src/wp_mcp/tenants/manager.py
"""Tenant lifecycle management — orchestrates crypto, composer, Docker ops, and DB."""

import os
import re
import uuid
import logging
from typing import Any

from wp_mcp.database import db as default_db
from wp_mcp.tenants.crypto import TenantCrypto
from wp_mcp.tenants.composer import TenantComposer
from wp_mcp.tenants.docker_ops import TenantDockerOps
from wp_mcp.tenants.routing import RESERVED_SUBDOMAINS, VIEWS

logger = logging.getLogger(__name__)

NAME_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")


class TenantManager:
    """Orchestrates tenant creation, updates, and deletion."""

    def __init__(
        self,
        encryption_key: str,
        base_domain: str = "ragbaz.cc",
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
```

**Step 4: Run test to verify it passes**

```bash
cd mcp-server && python -m pytest tests/test_tenant_manager_new.py -v
```

Expected: All PASS

**Step 5: Commit**

```bash
git add mcp-server/src/wp_mcp/tenants/manager.py mcp-server/tests/test_tenant_manager_new.py
git commit -m "feat: add TenantManager orchestrating crypto, compose, Docker, and DB"
```

---

## Task 7: REST Endpoints for Tenants

Wire the TenantManager into HTTP endpoints and register them in `server.py`.

**Files:**
- Create: `mcp-server/src/wp_mcp/routes/tenants.py`
- Modify: `mcp-server/src/wp_mcp/server.py` (register new routes)
- Test: `mcp-server/tests/test_tenant_routes.py`

**Step 1: Write the endpoint handlers**

```python
# mcp-server/src/wp_mcp/routes/tenants.py
"""REST endpoints for tenant management."""

import os
import logging
from starlette.requests import Request
from starlette.responses import JSONResponse

from wp_mcp.database import db
from wp_mcp.user_manager import UserManager
from wp_mcp.json_utils import sanitize_for_json

logger = logging.getLogger(__name__)

_manager = None


def get_manager():
    global _manager
    if _manager is None:
        from wp_mcp.tenants.manager import TenantManager
        encryption_key = os.getenv("ENCRYPTION_KEY")
        if not encryption_key:
            raise RuntimeError("ENCRYPTION_KEY required for tenant management")
        _manager = TenantManager(encryption_key=encryption_key)
    return _manager


async def _get_user(request):
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        return None
    return await UserManager.get_user_from_session(session_id)


async def create_tenant_endpoint(request: Request):
    user = await _get_user(request)
    if not user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    try:
        data = await request.json()
        name = data.get("name", "").strip()
        if not name:
            return JSONResponse({"error": "name is required"}, status_code=400)
        result = await get_manager().create_tenant(name=name, owner_user_id=user["id"])
        return JSONResponse(sanitize_for_json(result), status_code=201)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Create tenant error: %s", e)
        return JSONResponse({"error": "Failed to create tenant"}, status_code=500)


async def list_tenants_endpoint(request: Request):
    user = await _get_user(request)
    if not user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    try:
        tenants = await get_manager().list_tenants(owner_user_id=user["id"])
        return JSONResponse(sanitize_for_json({"tenants": tenants}))
    except Exception as e:
        logger.error("List tenants error: %s", e)
        return JSONResponse({"error": "Failed to list tenants"}, status_code=500)


async def get_tenant_endpoint(request: Request):
    user = await _get_user(request)
    if not user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    tenant_id = request.path_params["tenant_id"]
    try:
        tenant = await get_manager().get_tenant(tenant_id)
        if not tenant:
            return JSONResponse({"error": "Not found"}, status_code=404)
        return JSONResponse(sanitize_for_json(tenant))
    except Exception as e:
        logger.error("Get tenant error: %s", e)
        return JSONResponse({"error": "Failed to get tenant"}, status_code=500)


async def delete_tenant_endpoint(request: Request):
    user = await _get_user(request)
    if not user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    tenant_id = request.path_params["tenant_id"]
    try:
        success = await get_manager().delete_tenant(tenant_id)
        if not success:
            return JSONResponse({"error": "Not found"}, status_code=404)
        return JSONResponse({"success": True})
    except Exception as e:
        logger.error("Delete tenant error: %s", e)
        return JSONResponse({"error": "Failed to delete tenant"}, status_code=500)


async def update_default_view_endpoint(request: Request):
    user = await _get_user(request)
    if not user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    tenant_id = request.path_params["tenant_id"]
    try:
        data = await request.json()
        view = data.get("default_view", "")
        await get_manager().set_default_view(tenant_id, view)
        return JSONResponse({"success": True, "default_view": view})
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Update default view error: %s", e)
        return JSONResponse({"error": "Failed to update"}, status_code=500)


async def add_domain_endpoint(request: Request):
    user = await _get_user(request)
    if not user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    tenant_id = request.path_params["tenant_id"]
    try:
        data = await request.json()
        domain_id = await get_manager().add_custom_domain(
            tenant_id=tenant_id,
            external_domain=data["external_domain"],
            target_view=data["target_view"],
        )
        return JSONResponse({"success": True, "domain_id": domain_id}, status_code=201)
    except (ValueError, KeyError) as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Add domain error: %s", e)
        return JSONResponse({"error": "Failed to add domain"}, status_code=500)


async def remove_domain_endpoint(request: Request):
    user = await _get_user(request)
    if not user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    domain_id = int(request.path_params["domain_id"])
    try:
        success = await get_manager().remove_custom_domain(domain_id)
        if not success:
            return JSONResponse({"error": "Not found"}, status_code=404)
        return JSONResponse({"success": True})
    except Exception as e:
        logger.error("Remove domain error: %s", e)
        return JSONResponse({"error": "Failed to remove domain"}, status_code=500)


async def verify_domain_endpoint(request: Request):
    user = await _get_user(request)
    if not user:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    domain_id = int(request.path_params["domain_id"])
    try:
        success = await get_manager().verify_custom_domain(domain_id)
        if not success:
            return JSONResponse({"error": "Not found"}, status_code=404)
        return JSONResponse({"success": True, "verified": True})
    except Exception as e:
        logger.error("Verify domain error: %s", e)
        return JSONResponse({"error": "Failed to verify"}, status_code=500)
```

**Step 2: Register routes in server.py**

Add to the `mcp._app.routes.extend([...])` block in `server.py` (around line 182-267):

```python
from wp_mcp.routes import tenants as tenant_routes
from wp_mcp.routes import routing as routing_routes

# In the routes.extend block, add:
Route("/tenants", tenant_routes.create_tenant_endpoint, methods=["POST"]),
Route("/tenants", tenant_routes.list_tenants_endpoint, methods=["GET"]),
Route("/tenants/{tenant_id}", tenant_routes.get_tenant_endpoint, methods=["GET"]),
Route("/tenants/{tenant_id}", tenant_routes.delete_tenant_endpoint, methods=["DELETE"]),
Route("/tenants/{tenant_id}/default-view", tenant_routes.update_default_view_endpoint, methods=["PUT"]),
Route("/tenants/{tenant_id}/domains", tenant_routes.add_domain_endpoint, methods=["POST"]),
Route("/tenants/{tenant_id}/domains/{domain_id:int}", tenant_routes.remove_domain_endpoint, methods=["DELETE"]),
Route("/tenants/{tenant_id}/domains/{domain_id:int}/verify", tenant_routes.verify_domain_endpoint, methods=["POST"]),
# Caddy routing endpoints (no auth required)
Route("/routing/resolve", routing_routes.resolve_upstream, methods=["GET"]),
Route("/routing/tls-check", routing_routes.tls_check, methods=["GET"]),
```

**Step 3: Commit**

```bash
git add mcp-server/src/wp_mcp/routes/tenants.py mcp-server/src/wp_mcp/routes/routing.py mcp-server/src/wp_mcp/server.py
git commit -m "feat: add REST endpoints for tenant CRUD and Caddy routing"
```

---

## Task 8: Docker Socket Mount + Shared Networks

Update `docker-compose.production.yml` to mount Docker socket into MCP server, create shared networks.

**Files:**
- Modify: `docker-compose.production.yml`

**Step 1: Update production compose**

Add to the `mcp-server` service:

```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock
```

Add the shared external networks that tenant stacks will connect to:

```yaml
networks:
  articulate-internal:
    driver: bridge
    internal: true
  articulate-proxy:
    driver: bridge
  proxy_net:
    driver: bridge
    name: proxy_net
  control_net:
    driver: bridge
    name: control_net
```

Add `proxy_net` and `control_net` to the `mcp-server` and `caddy` services so they can reach tenant containers.

**Step 2: Create the external networks on the host**

```bash
docker network create proxy_net 2>/dev/null || true
docker network create control_net 2>/dev/null || true
```

**Step 3: Commit**

```bash
git add docker-compose.production.yml
git commit -m "feat: mount Docker socket in MCP server, add shared tenant networks"
```

---

## Task 9: Caddy Wildcard Configuration

Update Caddyfile for wildcard routing with dynamic upstreams.

**Files:**
- Modify: `docker/caddy/Caddyfile`

**Step 1: Add wildcard block to Caddyfile**

Append after the existing `http://my.ragbaz.cc` block:

```
# Tenant wildcard routing — dynamic upstream via MCP route resolver
*.ragbaz.cc {
    # Use internal TLS for subdomain routing
    tls internal

    reverse_proxy mcp-server:8000 {
        # Dynamic upstreams via HTTP subrequest
        dynamic http {
            uri /routing/resolve
            # Pass original Host header
            header Host {http.request.host}
        }

        header_up Host {http.request.host}
        header_up X-Forwarded-Host {http.request.host}
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-Proto {scheme}
        flush_interval -1
    }
}

# Custom external domains — on-demand TLS
:443 {
    tls {
        on_demand {
            ask http://mcp-server:8000/routing/tls-check
        }
    }

    reverse_proxy mcp-server:8000 {
        dynamic http {
            uri /routing/resolve
            header Host {http.request.host}
        }

        header_up Host {http.request.host}
        header_up X-Forwarded-Host {http.request.host}
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-Proto {scheme}
        flush_interval -1
    }
}
```

Note: Caddy's `dynamic http` upstream module may require the `caddy-l4` or `caddy-dynamicupstreams` plugin. If not available, fall back to the route resolver returning a redirect or using Caddy's `reverse_proxy` with a placeholder that calls the resolver. Check Caddy docs for exact syntax — the key mechanism is that Caddy makes an HTTP subrequest to determine the upstream. Alternative: use `caddy-docker-proxy` plugin which reads Docker labels.

**Step 2: Commit**

```bash
git add docker/caddy/Caddyfile
git commit -m "feat: add Caddy wildcard routing with dynamic upstreams"
```

---

## Task 10: Faust.js View Template

Create a minimal Faust.js app that renders WordPress content via GraphQL.

**Files:**
- Create: `templates/faust/Dockerfile`
- Create: `templates/faust/package.json`
- Create: `templates/faust/next.config.js`
- Create: `templates/faust/src/pages/index.js`
- Create: `templates/faust/src/pages/[...wordpressNode].js`
- Create: `templates/faust/faust.config.js`

**Step 1: Create Dockerfile**

```dockerfile
# templates/faust/Dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./
COPY --from=builder /app/next.config.js ./
COPY --from=builder /app/faust.config.js ./
EXPOSE 3000
CMD ["npm", "start"]
```

**Step 2: Create package.json**

```json
{
  "name": "articulate-faust-view",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  },
  "dependencies": {
    "@faustwp/core": "^3.0.0",
    "@faustwp/cli": "^3.0.0",
    "next": "^14.0.0",
    "react": "^18.0.0",
    "react-dom": "^18.0.0"
  }
}
```

**Step 3: Create faust.config.js**

```javascript
// templates/faust/faust.config.js
import { setConfig } from "@faustwp/core";

/** @type {import('@faustwp/core').FaustConfig} */
export default setConfig({
  wpUrl: process.env.NEXT_PUBLIC_WORDPRESS_URL,
  apiClientSecret: process.env.FAUST_SECRET_KEY || "",
});
```

**Step 4: Create next.config.js**

```javascript
// templates/faust/next.config.js
const { withFaust } = require("@faustwp/core");

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    remotePatterns: [
      { protocol: "http", hostname: "**" },
      { protocol: "https", hostname: "**" },
    ],
  },
};

module.exports = withFaust(nextConfig);
```

**Step 5: Create pages**

```javascript
// templates/faust/src/pages/index.js
import { gql, useQuery } from "@faustwp/core";
import Head from "next/head";

const GET_POSTS = gql`
  query GetPosts {
    posts(first: 10) {
      nodes {
        id
        title
        excerpt
        uri
        date
      }
    }
    generalSettings {
      title
      description
    }
  }
`;

export default function Home() {
  const { data, loading } = useQuery(GET_POSTS);

  if (loading) return <p>Loading...</p>;

  const { posts, generalSettings } = data || {};

  return (
    <>
      <Head>
        <title>{generalSettings?.title}</title>
        <meta name="description" content={generalSettings?.description} />
      </Head>
      <main style={{ maxWidth: 800, margin: "0 auto", padding: 20 }}>
        <h1>{generalSettings?.title}</h1>
        <p>{generalSettings?.description}</p>
        {posts?.nodes?.map((post) => (
          <article key={post.id} style={{ marginBottom: 24 }}>
            <h2>
              <a href={post.uri}>{post.title}</a>
            </h2>
            <div dangerouslySetInnerHTML={{ __html: post.excerpt }} />
            <time>{new Date(post.date).toLocaleDateString()}</time>
          </article>
        ))}
      </main>
    </>
  );
}

Home.query = GET_POSTS;
```

```javascript
// templates/faust/src/pages/[...wordpressNode].js
import { getWordPressProps, WordPressTemplate } from "@faustwp/core";

export default function Page(props) {
  return <WordPressTemplate {...props} />;
}

export async function getServerSideProps(context) {
  return getWordPressProps({ ctx: context });
}
```

**Step 6: Build the image**

```bash
cd templates/faust && docker build -t articulate-faust:latest .
```

**Step 7: Commit**

```bash
git add templates/faust/
git commit -m "feat: add Faust.js view template for tenant headless frontend"
```

---

## Task 11: Astro SSR View Template

Create a minimal Astro SSR app that renders WordPress content via GraphQL.

**Files:**
- Create: `templates/astro/Dockerfile`
- Create: `templates/astro/package.json`
- Create: `templates/astro/astro.config.mjs`
- Create: `templates/astro/src/pages/index.astro`
- Create: `templates/astro/src/pages/[...slug].astro`
- Create: `templates/astro/src/lib/wordpress.ts`

**Step 1: Create Dockerfile**

```dockerfile
# templates/astro/Dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./
EXPOSE 4321
ENV HOST=0.0.0.0
ENV PORT=4321
CMD ["node", "dist/server/entry.mjs"]
```

**Step 2: Create package.json**

```json
{
  "name": "articulate-astro-view",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "astro dev",
    "build": "astro build",
    "start": "node dist/server/entry.mjs"
  },
  "dependencies": {
    "astro": "^4.0.0",
    "@astrojs/node": "^8.0.0"
  }
}
```

**Step 3: Create astro.config.mjs**

```javascript
// templates/astro/astro.config.mjs
import { defineConfig } from "astro/config";
import node from "@astrojs/node";

export default defineConfig({
  output: "server",
  adapter: node({ mode: "standalone" }),
  server: { host: "0.0.0.0", port: 4321 },
});
```

**Step 4: Create WordPress GraphQL client**

```typescript
// templates/astro/src/lib/wordpress.ts
const GRAPHQL_URL =
  import.meta.env.WORDPRESS_GRAPHQL_URL || "http://localhost:80/graphql";

export async function wpQuery(query: string, variables = {}) {
  const res = await fetch(GRAPHQL_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, variables }),
  });
  const json = await res.json();
  if (json.errors) {
    throw new Error(json.errors.map((e: any) => e.message).join(", "));
  }
  return json.data;
}
```

**Step 5: Create pages**

```astro
---
// templates/astro/src/pages/index.astro
import { wpQuery } from "../lib/wordpress";

const data = await wpQuery(`
  query {
    posts(first: 10) {
      nodes { id title excerpt uri date }
    }
    generalSettings { title description }
  }
`);

const { posts, generalSettings } = data;
---
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{generalSettings.title}</title>
  <meta name="description" content={generalSettings.description} />
</head>
<body style="max-width:800px;margin:0 auto;padding:20px;font-family:system-ui">
  <h1>{generalSettings.title}</h1>
  <p>{generalSettings.description}</p>
  {posts.nodes.map((post: any) => (
    <article style="margin-bottom:24px">
      <h2><a href={`/${post.uri}`}>{post.title}</a></h2>
      <Fragment set:html={post.excerpt} />
      <time>{new Date(post.date).toLocaleDateString()}</time>
    </article>
  ))}
</body>
</html>
```

```astro
---
// templates/astro/src/pages/[...slug].astro
import { wpQuery } from "../lib/wordpress";

const { slug } = Astro.params;
const uri = `/${slug || ""}`;

const data = await wpQuery(`
  query GetContent($uri: String!) {
    nodeByUri(uri: $uri) {
      ... on Post {
        title
        content
        date
      }
      ... on Page {
        title
        content
      }
    }
  }
`, { uri });

const node = data?.nodeByUri;
if (!node) return Astro.redirect("/404");
---
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>{node.title}</title>
</head>
<body style="max-width:800px;margin:0 auto;padding:20px;font-family:system-ui">
  <a href="/">&larr; Back</a>
  <h1>{node.title}</h1>
  {node.date && <time>{new Date(node.date).toLocaleDateString()}</time>}
  <div set:html={node.content} />
</body>
</html>
```

**Step 6: Build the image**

```bash
cd templates/astro && docker build -t articulate-astro:latest .
```

**Step 7: Commit**

```bash
git add templates/astro/
git commit -m "feat: add Astro SSR view template for tenant headless frontend"
```

---

## Task 12: Integration — Wire Everything Together

Final wiring: update `__init__.py` exports, update `server.py` tool registration, add Docker socket to compose, ensure networks exist.

**Files:**
- Modify: `mcp-server/src/wp_mcp/tenants/__init__.py`
- Modify: `mcp-server/src/wp_mcp/server.py`
- Modify: `docker-compose.production.yml`

**Step 1: Update tenants package init**

```python
# mcp-server/src/wp_mcp/tenants/__init__.py
"""Multi-tenant infrastructure management."""
from wp_mcp.tenants.manager import TenantManager
from wp_mcp.tenants.crypto import TenantCrypto
from wp_mcp.tenants.composer import TenantComposer
from wp_mcp.tenants.docker_ops import TenantDockerOps
from wp_mcp.tenants.routing import RouteResolver

__all__ = ["TenantManager", "TenantCrypto", "TenantComposer", "TenantDockerOps", "RouteResolver"]
```

**Step 2: Run all tests**

```bash
cd mcp-server && python -m pytest tests/ -v
```

**Step 3: Build and test the MCP server container**

```bash
docker compose -f docker-compose.production.yml build mcp-server
docker compose -f docker-compose.production.yml restart mcp-server
```

**Step 4: Verify routing endpoints work**

```bash
curl -H "Host: faust.testsite.ragbaz.cc" http://localhost:8000/routing/resolve
# Should return 404 (no tenant exists yet)

curl "http://localhost:8000/routing/tls-check?domain=anything.ragbaz.cc"
# Should return 200
```

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: wire multi-tenant system — complete integration"
```

---

## Summary of Tasks

| # | Task | Key Files |
|---|------|-----------|
| 1 | DB Migration | `migrations/002_tenant_views_and_domains.sql` |
| 2 | Crypto module | `tenants/crypto.py` + test |
| 3 | Composer module | `tenants/composer.py` + template update + test |
| 4 | Docker ops module | `tenants/docker_ops.py` + test |
| 5 | Route resolver | `tenants/routing.py` + `routes/routing.py` + test |
| 6 | Tenant manager | `tenants/manager.py` + test |
| 7 | REST endpoints | `routes/tenants.py` + server.py wiring |
| 8 | Docker socket + networks | `docker-compose.production.yml` |
| 9 | Caddy wildcard config | `docker/caddy/Caddyfile` |
| 10 | Faust.js template | `templates/faust/` |
| 11 | Astro template | `templates/astro/` |
| 12 | Integration + testing | Final wiring and verification |

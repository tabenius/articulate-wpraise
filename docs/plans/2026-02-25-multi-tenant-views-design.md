# Multi-Tenant Views Design

> Date: 2026-02-25

## Overview

Evolve Articulate from a single-tenant WordPress stack into a multi-tenant platform where each tenant gets an isolated WordPress installation with multiple "view" frontends (Faust.js, Astro). A shared control plane (webedit, MCP server, Celery, Redis) manages all tenants.

## Subdomain Scheme

Each tenant gets subdomains on `ragbaz.xyz`:

- `wordpress.tenant1.ragbaz.xyz` — WordPress admin/backend
- `faust.tenant1.ragbaz.xyz` — Faust.js headless frontend
- `astro.tenant1.ragbaz.xyz` — Astro SSR headless frontend
- `tenant1.ragbaz.xyz` — routes to whichever view the owner chooses (`default_view`)

Users can also map external domains (e.g. `tenant1.com`) to a specific view via CNAME + verification.

## Data Model

Three new tables in shared MariaDB:

```sql
CREATE TABLE tenants (
    id              VARCHAR(32) PRIMARY KEY,
    name            VARCHAR(63) NOT NULL UNIQUE,
    domain          VARCHAR(255) NOT NULL,
    owner_user_id   INT,
    default_view    ENUM('wordpress','faust','astro') NOT NULL DEFAULT 'wordpress',
    status          ENUM('provisioning','running','stopped','error') NOT NULL DEFAULT 'provisioning',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE tenant_secrets (
    tenant_id         VARCHAR(32) PRIMARY KEY,
    db_password       VARBINARY(512) NOT NULL,
    db_root_password  VARBINARY(512) NOT NULL,
    wp_admin_password VARBINARY(512) NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

CREATE TABLE tenant_domains (
    id              INT PRIMARY KEY AUTO_INCREMENT,
    tenant_id       VARCHAR(32) NOT NULL,
    external_domain VARCHAR(255) NOT NULL UNIQUE,
    target_view     ENUM('wordpress','faust','astro') NOT NULL,
    verified        BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);
```

Secrets encrypted at rest with `ENCRYPTION_KEY`.

## Architecture

```
                         Internet
                            |
                   +--------v--------+
                   |    HAProxy       |  SSL termination
                   +--------+--------+
                            |
                   +--------v--------+
                   |     Caddy        |  Wildcard *.ragbaz.xyz
                   |                  |  On-demand TLS for custom domains
                   +--+-----+-----+--+
                      |     |     |
         +------------+     |     +------------+
         v                  v                   v
   +-----------+    +--------------+    +--------------+
   |  Shared    |    |  Tenant 1    |    |  Tenant 2    |
   |  Control   |    |              |    |              |
   |  Plane     |    |  WordPress   |    |  WordPress   |
   |            |    |  MariaDB     |    |  MariaDB     |
   |  webedit   |    |  Faust       |    |  Faust       |
   |  mcp-server|    |  Astro       |    |  Astro       |
   |  celery    |    |              |    |              |
   |  redis     |    |  tenant_net  |    |  tenant_net  |
   |  mariadb   |    |  (private)   |    |  (private)   |
   |  docs      |    |              |    |              |
   +---------+--+    +------+-------+    +------+-------+
             |              |                    |
             +--------------+--------------------+
                       proxy_net (shared)
```

### Networks

- `proxy_net` — Caddy + all tenant services that need external routing (WordPress, Faust, Astro)
- `control_net` — shared control plane talks to tenant WordPress for MCP/GraphQL operations
- `tenant_{id}_net` — private per-tenant, only WordPress + MariaDB (DB isolation)

### Per-Tenant Compose Project

Each tenant is a separate Docker Compose project (`tenant_{id}`) with:

- `tenant_{id}_wordpress` — WordPress 6.4, on `proxy_net` + `tenant_net` + `control_net`
- `tenant_{id}_mariadb` — MariaDB 10.11, on `tenant_net` only
- `tenant_{id}_faust` — Faust.js, on `proxy_net` + `tenant_net`
- `tenant_{id}_astro` — Astro SSR, on `proxy_net` + `tenant_net`

## Spawn Module

Replaces `spawn.py`. Lives at `mcp-server/src/wp_mcp/tenants/`:

```
mcp-server/src/wp_mcp/tenants/
├── __init__.py
├── manager.py        -- TenantManager: CRUD orchestration
├── models.py         -- DB models for tenants, secrets, domains
├── composer.py       -- Jinja2 template rendering for docker-compose YAML
├── docker_ops.py     -- python-on-whales wrapper: up, down, status, logs
├── routing.py        -- route resolver endpoint for Caddy
└── crypto.py         -- secret generation + encryption
```

## Tenant Lifecycle

### Creation

1. `POST /tenants` with `{name: "tenant1", owner_user_id: 42}`
2. Validate name (DNS-safe slug, unique)
3. Generate random secrets, encrypt, store in `tenant_secrets`
4. Render Jinja2 template to docker-compose YAML, save to `tenants/` dir
5. Docker SDK: `docker compose -p tenant_{id} up -d`
6. Set status `provisioning`
7. Celery background task polls WordPress healthcheck → status `running`

### Operations

- `GET /tenants` — list tenants (filtered by owner)
- `GET /tenants/{id}` — details + status
- `PUT /tenants/{id}` — update default_view, name
- `DELETE /tenants/{id}` — stop containers, remove volumes, delete DB rows
- `POST /tenants/{id}/domains` — add custom domain
- `DELETE /tenants/{id}/domains/{domain_id}` — remove custom domain
- `POST /tenants/{id}/domains/{domain_id}/verify` — DNS verification

## Caddy Routing

Single wildcard config, no regeneration. Dynamic upstream resolution via subrequests.

Caddy calls MCP server's `/routing/resolve` endpoint for every request:

1. `faust.tenant1.ragbaz.xyz` → lookup tenant by name → `tenant_{id}_faust:3000`
2. `tenant1.ragbaz.xyz` → lookup tenant + `default_view` → appropriate upstream
3. `tenant1.com` → lookup `tenant_domains` → upstream if verified
4. Unknown → 404

Redis cache (60s TTL) prevents DB hits on every request.

On-demand TLS for custom domains: Caddy calls `GET /routing/tls-check?domain=X`. MCP server returns 200 if domain is in `tenant_domains` and verified, 404 otherwise.

## View Containers

Generic pre-built images configured via env vars:

### Faust.js

- Node.js 20 Alpine, minimal Faust.js app
- `WORDPRESS_URL`, `WORDPRESS_GRAPHQL_URL`, `TENANT_NAME`, `SITE_URL`
- Port 3000
- Template at `templates/faust/`

### Astro

- Node.js 20 Alpine, Astro SSR with `@astrojs/node`
- Same env vars, port 4321
- Template at `templates/astro/`

Both consume WordPress GraphQL for content rendering (posts, pages, navigation).

## Control Plane Integration

- MCP server gets Docker socket mounted (`/var/run/docker.sock`)
- New `python-on-whales` dependency
- New MCP tools: `create_tenant`, `list_tenants`, `get_tenant`, `delete_tenant`, `set_default_view`, `add_custom_domain`, `remove_custom_domain`
- New REST endpoints for Caddy: `/routing/resolve`, `/routing/tls-check`
- DB migration adds the three new tables
- Existing webedit multi-WP connection system maps to tenants naturally

## Security

- Per-tenant DB isolation via private `tenant_net`
- No exposed ports on MariaDB
- Resource limits: 1 CPU, 512MB RAM, 200 PIDs per container
- `cap_drop: ALL`, `no-new-privileges`
- Docker socket access limited to MCP server (not internet-exposed)
- Secrets encrypted at rest, generated randomly (not deterministic)
- Custom domain verification before TLS cert issuance

## What Stays Unchanged

- webedit (Next.js) — already supports multiple WP connections
- Celery workers — gain tenant provisioning tasks
- Redis — shared, adds routing cache
- docs site — unchanged
- Existing `app.ragbaz.xyz` and `my.ragbaz.xyz` routes — unchanged

# Multi-Tenancy Guide

Articulate supports multiple isolated WordPress instances per user or organization. Each tenant has:
- Separate WordPress instance
- Independent user access control
- Resource quotas and usage tracking
- Optional separate database

## Quick Start

### 1. Apply Database Migrations

```bash
cd mcp-server
python3 scripts/run-migrations.py
```

This creates the `tenants`, `tenant_users`, and `tenant_usage` tables.

### 2. Create Your First Tenant

Via Claude chat:
```
Create a new WordPress tenant called "My Blog" with slug "my-blog"
at http://localhost:8080
```

Or via API:
```typescript
const response = await fetch('/api/tenants', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: 'My Blog',
    slug: 'my-blog',
    wp_url: 'http://localhost:8080',
    wp_graphql_endpoint: 'http://localhost:8080/graphql',
    wp_admin_user: 'admin'
  })
});
```

### 3. List Your Tenants

Via Claude:
```
Show me all my WordPress tenants
```

### 4. Share Tenant with Team

```
Add user john@example.com to my "My Blog" tenant as an editor
```

## Architecture

### Tenant Isolation Levels

**Level 1: Shared WordPress, Separate Content** *(Current Default)*
- All tenants use same WordPress instance
- Content isolation via user permissions
- Simplest setup, lowest cost

**Level 2: Shared Database, Separate WordPress Containers** *(Planned)*
- Each tenant gets dedicated WordPress container
- Shared database with table prefixes
- Better isolation, moderate cost

**Level 3: Separate Database per Tenant** *(Fully Supported)*
- Each tenant has dedicated database
- Complete data isolation
- Highest security, higher cost

### Database Schema

```sql
tenants
  ├─ id (UUID)
  ├─ name (display name)
  ├─ slug (URL identifier)
  ├─ owner_user_id (creator)
  ├─ wp_url, wp_graphql_endpoint
  ├─ db_host, db_name, db_user, db_password_encrypted
  ├─ max_posts, max_storage_mb, max_users (quotas)
  └─ status (active/suspended/deleted)

tenant_users (many-to-many)
  ├─ tenant_id
  ├─ user_id
  └─ role (owner/admin/editor/viewer)

tenant_usage
  ├─ tenant_id
  ├─ post_count, storage_used_mb, user_count
  └─ updated_at
```

## User Roles

| Role | Create/Edit Posts | Manage Users | Delete Tenant |
|------|------------------|--------------|---------------|
| **Owner** | ✅ | ✅ | ✅ |
| **Admin** | ✅ | ✅ | ❌ |
| **Editor** | ✅ | ❌ | ❌ |
| **Viewer** | ❌ | ❌ | ❌ |

## MCP Tools Reference

### `create_tenant`
Create a new tenant (isolated WordPress instance).

**Parameters:**
- `name`: Display name (e.g., "Acme Corporation")
- `slug`: URL-safe identifier (e.g., "acme-corp")
- `wp_url`: WordPress URL
- `wp_graphql_endpoint`: GraphQL endpoint
- `wp_admin_user`: WordPress admin username
- `wp_admin_email`: Admin email (optional)
- `db_host`, `db_name`, `db_user`, `db_password`: Database config (optional)
- `max_posts`, `max_storage_mb`, `max_users`: Resource limits

**Example:**
```python
tenant_id = await create_tenant(
    name="My Company Blog",
    slug="my-company",
    wp_url="https://blog.mycompany.com",
    wp_graphql_endpoint="https://blog.mycompany.com/graphql",
    wp_admin_user="admin",
    max_posts=5000
)
```

### `list_my_tenants`
List all tenants accessible by current user.

**Returns:**
```json
{
  "success": true,
  "tenants": [
    {
      "id": "uuid",
      "name": "My Blog",
      "slug": "my-blog",
      "wp_url": "http://localhost:8080",
      "role": "owner",
      "created_at": "2024-01-01T00:00:00"
    }
  ],
  "count": 1
}
```

### `get_tenant_details`
Get detailed information about a tenant.

**Parameters:**
- `tenant_id`: UUID of tenant

**Returns:**
```json
{
  "tenant": {
    "id": "uuid",
    "name": "My Blog",
    "status": "active",
    "max_posts": 1000,
    ...
  },
  "usage": {
    "post_count": 42,
    "storage_used_mb": 150.5,
    "user_count": 3
  }
}
```

### `update_tenant_status`
Change tenant status (active/suspended/deleted).

**Parameters:**
- `tenant_id`: UUID
- `status`: "active", "suspended", or "deleted"

### `add_user_to_tenant`
Share tenant with another user.

**Parameters:**
- `tenant_id`: UUID
- `user_email`: Email of user to add
- `role`: "owner", "admin", "editor", or "viewer"

### `remove_user_from_tenant`
Revoke user's access to tenant.

**Parameters:**
- `tenant_id`: UUID
- `user_email`: Email of user to remove

## Deployment Scenarios

### Single Server (Recommended for Start)

All tenants share one WordPress instance, isolated by permissions.

**Setup:**
1. Run migrations
2. Create tenants pointing to same WordPress URL
3. Users see only their own content

### Multi-Container (Scalable)

Each tenant gets dedicated WordPress container.

**Setup:**
1. Provision WordPress container per tenant
2. Create tenant with unique `wp_url` for each container
3. Use orchestration (Docker Compose, Kubernetes)

### Separate Databases (Maximum Isolation)

Each tenant has dedicated database.

**Setup:**
1. Create MariaDB database per tenant
2. Provide `db_host`, `db_name`, `db_user`, `db_password` when creating tenant
3. Passwords encrypted with `ENCRYPTION_KEY`

## Security

- **Database Credentials**: Encrypted with Fernet (requires `ENCRYPTION_KEY` in env)
- **Access Control**: Role-based permissions enforced at MCP layer
- **Tenant Isolation**: Users can only access tenants they're associated with
- **Audit Logging**: All tenant operations logged

## Resource Quotas

Enforce limits per tenant:

```python
await create_tenant(
    ...,
    max_posts=1000,        # Maximum posts
    max_storage_mb=5000,   # Maximum storage (5GB)
    max_users=10           # Maximum users
)
```

Check usage:
```python
details = await get_tenant_details(tenant_id)
usage = details["usage"]

if usage["post_count"] >= tenant["max_posts"]:
    # Quota exceeded - prevent new posts
```

## Migration from Single to Multi-Tenant

If you have existing WordPress setup:

1. **Export existing data**:
   ```bash
   wp db export backup.sql --allow-root
   ```

2. **Create default tenant**:
   ```python
   await create_tenant(
       name="Main Site",
       slug="main",
       wp_url=os.getenv("WP_URL")
   )
   ```

3. **Associate existing users**:
   ```python
   for user in existing_users:
       await add_user_to_tenant(default_tenant_id, user.email, "editor")
   ```

4. **Enable multi-tenant mode**:
   ```bash
   # In .env
   MULTI_TENANT_MODE=true
   ```

## Troubleshooting

### "Multi-tenancy not configured"
**Cause**: `ENCRYPTION_KEY` not set in environment.

**Fix**: Generate and set encryption key:
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Add to .env: ENCRYPTION_KEY=<generated-key>
```

### "User not found"
**Cause**: User doesn't exist in Articulate system.

**Fix**: User must register/login to Articulate first before being added to tenants.

### Migration failures
**Cause**: Database permissions or connection issues.

**Fix**: Check database credentials in `MYSQL_*` environment variables.

## Best Practices

1. **Start Simple**: Use shared WordPress until you need isolation
2. **Plan Slug Names**: Choose memorable, URL-safe slugs (can't be changed easily)
3. **Set Realistic Quotas**: Prevent resource exhaustion
4. **Regular Backups**: Backup tenant data separately
5. **Monitor Usage**: Track `tenant_usage` table for quota enforcement

## API Integration

Frontend components can call tenant tools via `/api/tenants`:

```typescript
// Create tenant
POST /api/tenants
{
  "name": "My Blog",
  "slug": "my-blog",
  ...
}

// List tenants
GET /api/tenants

// Get tenant details
GET /api/tenants/{tenant_id}

// Update status
PATCH /api/tenants/{tenant_id}
{
  "status": "suspended"
}

// Manage users
POST /api/tenants/{tenant_id}/users
{
  "email": "john@example.com",
  "role": "editor"
}
```

## Next Steps

- [ ] Create tenant management UI in frontend
- [ ] Implement automatic provisioning of WordPress containers
- [ ] Add tenant-level API keys
- [ ] Billing integration for quota-based pricing
- [ ] Tenant subdomain routing (tenant1.yourdomain.com)

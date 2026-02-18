# Docker Hostnames - Internal vs External

## Issue
WordPress connections were failing with "All connection attempts failed" because they used external URLs.

## Root Cause
WordPress connections stored in the database used `http://localhost:8080` (external/host URL) instead of `http://wordpress:80` (internal Docker hostname).

### Why This Matters
- **From host machine**: WordPress is at `http://localhost:8080` (port mapping)
- **From inside Docker**: WordPress is at `http://wordpress:80` (internal network)
- **MCP server runs inside Docker**: Must use internal hostname

## Error Example
```
httpx.ConnectError: All connection attempts failed
```

This happens when MCP server tries to connect to `localhost:8080` from inside the Docker network.

## Solution
WordPress connections must use internal Docker hostnames:

```sql
UPDATE wp_wordpress_connections
SET wp_url='http://wordpress:80',
    wp_graphql_endpoint='http://wordpress:80/graphql'
WHERE wp_url LIKE '%localhost%';
```

## Correct URLs by Context

### For WordPress Connections (used by MCP server)
```
wp_url: http://wordpress:80
wp_graphql_endpoint: http://wordpress:80/graphql
```

### For External Access (from browser/host)
```
WordPress: http://localhost:8080
MCP Server: http://localhost:8000
```

## Service Hostnames Inside Docker
- `wordpress` - WordPress (internal port 80, external 8080)
- `mcp-server` - MCP Server (internal port 8000, external 8000)
- `mariadb` - Database (internal port 3306, external 3306)
- `redis` - Redis (internal port 6379, external 6379)

## When Creating Connections
Always use internal Docker hostnames when creating WordPress connections through the API or database:

```json
{
  "name": "Local WordPress",
  "wp_url": "http://wordpress:80",
  "wp_graphql_endpoint": "http://wordpress:80/graphql",
  "wp_user": "admin",
  "wp_app_password": "..."
}
```

## Fixed
All existing connections updated to use `http://wordpress:80`.

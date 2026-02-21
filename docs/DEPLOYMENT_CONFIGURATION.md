# Deployment Configuration Guide

This guide explains how to configure Articulate for different deployment scenarios.

## Understanding the URL Configuration

Articulate uses different URLs depending on **where** the connections are made from:

1. **Backend-to-WordPress** (MCP Server → WordPress): Uses Docker internal networking
2. **Frontend-to-MCP** (Next.js → MCP Server): Can be localhost or remote
3. **Browser-to-WordPress** (User's browser → WordPress GraphQL): Must be publicly accessible URL

## Deployment Scenarios

### Scenario 1: Local Development (Everything on localhost)

**Use Case**: Developer running all services on their local machine.

**Configuration**:

**Root `.env`:**
```bash
WP_URL=http://localhost:8080
WP_GRAPHQL_ENDPOINT=http://wordpress:80/graphql  # Docker internal
MCP_SERVER_URL=http://localhost:8000
WP_APP_PASSWORD=xxxx_xxxx_xxxx_xxxx_xxxx_xxxx
```

**`web/.env.local`:**
```bash
MCP_SERVER_URL=http://localhost:8000
WP_URL=http://localhost:8080

# Default WordPress Connection (for user's browser)
NEXT_PUBLIC_DEFAULT_WP_NAME=Local WordPress
NEXT_PUBLIC_DEFAULT_WP_URL=http://localhost:8080
NEXT_PUBLIC_DEFAULT_WP_GRAPHQL_ENDPOINT=http://localhost:8080/graphql
NEXT_PUBLIC_DEFAULT_WP_USER=admin
DEFAULT_WP_APP_PASSWORD=xxxx_xxxx_xxxx_xxxx_xxxx_xxxx
```

### Scenario 2: Production - Single Server (All services on one server)

**Use Case**: All Docker containers running on a single server with a public domain.

**Configuration**:

**Root `.env`:**
```bash
WP_URL=https://yourdomain.com
WP_GRAPHQL_ENDPOINT=http://wordpress:80/graphql  # Docker internal
MCP_SERVER_URL=http://mcp-server:8000  # Docker internal
WP_APP_PASSWORD=xxxx_xxxx_xxxx_xxxx_xxxx_xxxx
DOMAIN=yourdomain.com
```

**`web/.env.local`:**
```bash
MCP_SERVER_URL=http://localhost:8000  # Next.js to MCP (same server)
WP_URL=https://yourdomain.com

# CRITICAL: Use public URLs that browsers can access
NEXT_PUBLIC_DEFAULT_WP_NAME=Production WordPress
NEXT_PUBLIC_DEFAULT_WP_URL=https://yourdomain.com
NEXT_PUBLIC_DEFAULT_WP_GRAPHQL_ENDPOINT=https://yourdomain.com/graphql
NEXT_PUBLIC_DEFAULT_WP_USER=admin
DEFAULT_WP_APP_PASSWORD=xxxx_xxxx_xxxx_xxxx_xxxx_xxxx
```

**Reverse Proxy Configuration**: Configure Nginx/Caddy/HAProxy to route:
- `yourdomain.com` → WordPress container (port 80)
- `yourdomain.com/graphql` → WordPress GraphQL endpoint
- `yourdomain.com:3003` or `app.yourdomain.com` → Next.js frontend (port 3003)

### Scenario 3: Production - Separate Servers

**Use Case**: Frontend on one server, WordPress on another.

**Example Setup**:
- Frontend: `app.yourdomain.com` (Server A)
- WordPress: `wp.yourdomain.com` (Server B)
- MCP Server: Runs on Server B with WordPress

**Server B (WordPress + MCP) - Root `.env`:**
```bash
WP_URL=https://wp.yourdomain.com
WP_GRAPHQL_ENDPOINT=http://wordpress:80/graphql  # Docker internal
MCP_SERVER_URL=http://mcp-server:8000  # Docker internal
WP_APP_PASSWORD=xxxx_xxxx_xxxx_xxxx_xxxx_xxxx
DOMAIN=wp.yourdomain.com
```

**Server A (Frontend) - `web/.env.local`:**
```bash
MCP_SERVER_URL=https://wp.yourdomain.com:8000  # Or expose MCP via reverse proxy
WP_URL=https://wp.yourdomain.com

# Browsers connect directly to Server B's WordPress
NEXT_PUBLIC_DEFAULT_WP_NAME=Production WordPress
NEXT_PUBLIC_DEFAULT_WP_URL=https://wp.yourdomain.com
NEXT_PUBLIC_DEFAULT_WP_GRAPHQL_ENDPOINT=https://wp.yourdomain.com/graphql
NEXT_PUBLIC_DEFAULT_WP_USER=admin
DEFAULT_WP_APP_PASSWORD=xxxx_xxxx_xxxx_xxxx_xxxx_xxxx
```

**Security Note**: For separate servers, consider:
1. Exposing MCP server via reverse proxy with authentication
2. OR: VPN/private network between servers
3. Enable CORS on WordPress for frontend domain

### Scenario 4: Remote Access to Local WordPress

**Use Case**: Frontend deployed remotely, but WordPress running locally (testing/development).

**Option A: Use ngrok/localtunnel to expose local WordPress**:
```bash
# On local machine running WordPress
ngrok http 8080
# You'll get: https://abc123.ngrok.io
```

**`web/.env.local` (on remote frontend):**
```bash
NEXT_PUBLIC_DEFAULT_WP_URL=https://abc123.ngrok.io
NEXT_PUBLIC_DEFAULT_WP_GRAPHQL_ENDPOINT=https://abc123.ngrok.io/graphql
```

**Option B: Use SSH tunnel** (more secure):
```bash
# On remote frontend server
ssh -L 8080:localhost:8080 your-local-machine
```

Then use `http://localhost:8080` in frontend config.

## Common Issues

### ❌ "Failed to fetch" or CORS errors

**Problem**: Browser can't reach WordPress URL.

**Check**:
1. Can you access `NEXT_PUBLIC_DEFAULT_WP_URL` in your browser from the same network as your users?
2. Is CORS enabled on WordPress for your frontend domain?

**Fix**: Use the correct public URL, or configure CORS in WordPress:
```php
// In WordPress theme's functions.php
add_action('graphql_init', function() {
    add_filter('graphql_response_headers_to_send', function($headers) {
        $headers['Access-Control-Allow-Origin'] = 'https://app.yourdomain.com';
        return $headers;
    });
});
```

### ❌ "403 Forbidden" after login

**Problem**: Auto-setup can't create WordPress connection.

**Possible Causes**:
1. `DEFAULT_WP_APP_PASSWORD` not set in `web/.env.local`
2. Application password is invalid
3. WordPress URL is unreachable from backend

**Fix**:
1. Check `web/.env.local` has `DEFAULT_WP_APP_PASSWORD` set
2. Generate new application password in WordPress: Admin → Profile → Application Passwords
3. Test connectivity: `curl -u "admin:your_app_password" https://yourdomain.com/wp-json/wp/v2/users/me`

### ❌ "Authentication required" 401 errors

**Problem**: MCP server not receiving session headers.

**Fix**: Ensure cookies are enabled, session cookie is set after login. Check browser DevTools → Application → Cookies for `session` cookie.

## Environment Variable Reference

### `NEXT_PUBLIC_*` Variables

**MUST** be publicly accessible URLs (user's browser connects directly):
- `NEXT_PUBLIC_DEFAULT_WP_URL` - WordPress home URL
- `NEXT_PUBLIC_DEFAULT_WP_GRAPHQL_ENDPOINT` - GraphQL endpoint (usually `{WP_URL}/graphql`)
- `NEXT_PUBLIC_DEFAULT_WP_USER` - WordPress username
- `NEXT_PUBLIC_DEFAULT_WP_NAME` - Display name for connection

### Server-Side Only Variables

**Can** use internal Docker networking:
- `DEFAULT_WP_APP_PASSWORD` - WordPress application password (never exposed to browser)
- `MCP_SERVER_URL` - MCP server URL from Next.js server
- `WP_URL` - WordPress URL for backend operations

## Testing Your Configuration

### 1. Test WordPress Accessibility from Browser

```bash
# Should return WordPress site HTML
curl https://yourdomain.com

# Should return GraphQL schema
curl -X POST https://yourdomain.com/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ __schema { queryType { name } } }"}'
```

### 2. Test Application Password

```bash
# Should return user info (replace spaces in password)
curl -u "admin:xxxx xxxx xxxx xxxx xxxx xxxx" \
  https://yourdomain.com/wp-json/wp/v2/users/me
```

### 3. Test Auto-Setup

1. Register new user in Articulate
2. Login
3. Check browser console - should see "WordPress connected!" toast
4. Should immediately see WordPress posts (no manual setup required)

If manual setup page appears, check:
- Environment variables are set correctly
- WordPress URL is accessible from user's browser
- Application password is valid

## Quick Reference

| Variable | Local Dev | Production (Single) | Production (Split) |
|----------|-----------|---------------------|-------------------|
| `NEXT_PUBLIC_DEFAULT_WP_URL` | `http://localhost:8080` | `https://yourdomain.com` | `https://wp.yourdomain.com` |
| `NEXT_PUBLIC_DEFAULT_WP_GRAPHQL_ENDPOINT` | `http://localhost:8080/graphql` | `https://yourdomain.com/graphql` | `https://wp.yourdomain.com/graphql` |
| `WP_URL` (root .env) | `http://localhost:8080` | `https://yourdomain.com` | `https://wp.yourdomain.com` |
| `MCP_SERVER_URL` (web) | `http://localhost:8000` | `http://localhost:8000` | `https://wp.yourdomain.com:8000` |

## Need Help?

If you're still stuck:

1. **Check the logs**: `docker-compose logs -f mcp-server wordpress web`
2. **Test each connection separately**: Backend → WordPress, Frontend → MCP, Browser → WordPress
3. **Verify DNS/firewall**: Ensure public URLs resolve and ports are open
4. **Review reverse proxy config**: Check Nginx/Caddy logs for routing issues

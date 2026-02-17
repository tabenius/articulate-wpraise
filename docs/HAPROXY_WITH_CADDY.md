# Using WP-AI with Existing HAProxy

Guide for integrating WP-AI into an existing HAProxy infrastructure, with options to use Caddy as an internal proxy for simplified routing.

## Table of Contents

- [Architecture Options](#architecture-options)
- [Option 1: HAProxy Direct Routing](#option-1-haproxy-direct-routing)
- [Option 2: HAProxy + Caddy Internal Proxy](#option-2-haproxy--caddy-internal-proxy-recommended)
- [Configuration Examples](#configuration-examples)
- [Troubleshooting](#troubleshooting)

## Architecture Options

### Option 1: HAProxy Direct Routing

```
Internet → HAProxy (SSL termination) → WP-AI services directly
                                     ├─> Next.js (3000)
                                     ├─> WordPress (8080)
                                     └─> MCP Server (8000)
```

**Pros:**
- Simpler, fewer moving parts
- HAProxy handles everything

**Cons:**
- More complex HAProxy configuration
- Need to manually configure all WP-AI routes in HAProxy

### Option 2: HAProxy + Caddy Internal Proxy (Recommended)

```
Internet → HAProxy (SSL termination) → Caddy (internal routing) → WP-AI services
                                                                 ├─> Next.js (3000)
                                                                 ├─> WordPress (8080)
                                                                 └─> MCP Server (8000)
```

**Pros:**
- Cleaner separation: HAProxy for SSL/domains, Caddy for WP-AI routing
- Easier WP-AI updates (routing logic in Caddy)
- Can use Caddy's advanced features (automatic compression, etc.)
- Caddy config is simpler than HAProxy for app routing

**Cons:**
- One additional hop (minimal performance impact)

## Option 1: HAProxy Direct Routing

Use this if you want HAProxy to route directly to all WP-AI services.

### 1. Start WP-AI in Production Mode

```bash
# Start without exposed ports
docker compose -f docker-compose.production.yml up -d
```

Services are now running but only accessible within Docker networks.

### 2. Expose Services on Localhost

You have two choices:

#### A. Bind to localhost in production compose

Edit `docker-compose.production.yml` to add localhost bindings:

```yaml
services:
  wordpress:
    ports:
      - "127.0.0.1:8080:80"  # Only accessible from localhost

  mcp-server:
    ports:
      - "127.0.0.1:8000:8000"  # Only accessible from localhost
```

Then start Next.js with PM2:
```bash
cd web
npm run build
pm2 start npm --name wp-ai-web -- start
```

#### B. Use docker network with HAProxy in container

Run HAProxy in a container and connect it to `wp-ai-proxy` network (advanced).

### 3. Update HAProxy Configuration

Add to `/etc/haproxy/haproxy.cfg`:

```haproxy
#---------------------------------------------------------------------
# WP-AI Backend Configuration
#---------------------------------------------------------------------

# ACL rules for routing
frontend https_front
    # ... your existing config ...

    # WP-AI ACLs
    acl is_wpai_domain hdr(host) -i wpai.yourdomain.com
    acl is_wp_admin path_beg /wp-admin
    acl is_wp_login path_beg /wp-login.php
    acl is_wp_content path_beg /wp-content /wp-includes
    acl is_graphql path_beg /graphql
    acl is_mcp_api path_beg /api/mcp

    # Route WP-AI traffic
    use_backend wpai_wordpress if is_wpai_domain is_wp_admin
    use_backend wpai_wordpress if is_wpai_domain is_wp_login
    use_backend wpai_wordpress if is_wpai_domain is_wp_content
    use_backend wpai_wordpress if is_wpai_domain is_graphql
    use_backend wpai_mcp if is_wpai_domain is_mcp_api
    use_backend wpai_nextjs if is_wpai_domain

# Backend for WP-AI Next.js
backend wpai_nextjs
    mode http
    balance roundrobin
    option httpchk GET /
    http-check expect status 200

    option forwardfor
    http-request set-header X-Forwarded-Proto https
    http-request set-header X-Forwarded-For %[src]

    server nextjs1 127.0.0.1:3000 check

# Backend for WP-AI WordPress
backend wpai_wordpress
    mode http
    balance roundrobin
    option httpchk GET /wp-admin/
    http-check expect status 200-399

    option forwardfor
    http-request set-header X-Forwarded-Proto https
    http-request set-header X-Forwarded-For %[src]
    http-request set-header X-Real-IP %[src]

    server wordpress1 127.0.0.1:8080 check

# Backend for WP-AI MCP Server
backend wpai_mcp
    mode http
    balance roundrobin
    option httpchk GET /health
    http-check expect status 200-399

    option forwardfor
    http-request set-header X-Forwarded-Proto https
    http-request set-header X-Forwarded-For %[src]

    # Strip /api/mcp prefix
    http-request replace-path /api/mcp(/)?(.*) /\2

    server mcp1 127.0.0.1:8000 check
```

### 4. Reload HAProxy

```bash
# Test configuration
sudo haproxy -c -f /etc/haproxy/haproxy.cfg

# Reload
sudo systemctl reload haproxy
```

## Option 2: HAProxy + Caddy Internal Proxy (Recommended)

Use this for cleaner separation: HAProxy handles SSL and domain routing, Caddy handles WP-AI internal routing.

### 1. Create Internal Caddy Configuration

Create `docker/caddy/Caddyfile.internal`:

```caddyfile
# Internal Caddy configuration (no SSL, HAProxy handles that)
# Listens on port 8090 for HAProxy to forward to

:8090 {
    # No automatic HTTPS - HAProxy handles SSL termination

    # Logging
    log {
        output stdout
        format json
    }

    # WordPress admin panel
    @wpadmin {
        path /wp-admin* /wp-login.php*
    }
    handle @wpadmin {
        reverse_proxy wordpress:80 {
            header_up Host {host}
            header_up X-Real-IP {http.request.header.X-Real-IP}
            header_up X-Forwarded-For {http.request.header.X-Forwarded-For}
            header_up X-Forwarded-Proto {http.request.header.X-Forwarded-Proto}
        }
    }

    # WordPress static assets
    @wpcontent {
        path /wp-content/* /wp-includes/*
    }
    handle @wpcontent {
        reverse_proxy wordpress:80 {
            header_up Host {host}
        }
    }

    # GraphQL endpoint
    @graphql {
        path /graphql*
    }
    handle @graphql {
        reverse_proxy wordpress:80 {
            header_up Host {host}
            header_up X-Real-IP {http.request.header.X-Real-IP}
            header_up X-Forwarded-For {http.request.header.X-Forwarded-For}
            header_up X-Forwarded-Proto {http.request.header.X-Forwarded-Proto}
            flush_interval -1
        }
    }

    # MCP Server API
    @mcpapi {
        path /api/mcp/*
    }
    handle @mcpapi {
        uri strip_prefix /api/mcp
        reverse_proxy mcp-server:8000 {
            header_up Host {host}
            header_up X-Real-IP {http.request.header.X-Real-IP}
            header_up X-Forwarded-For {http.request.header.X-Forwarded-For}
            header_up X-Forwarded-Proto {http.request.header.X-Forwarded-Proto}
            flush_interval -1
        }
    }

    # Next.js frontend (default)
    handle {
        reverse_proxy nextjs:3000 {
            header_up Host {host}
            header_up X-Real-IP {http.request.header.X-Real-IP}
            header_up X-Forwarded-For {http.request.header.X-Forwarded-For}
            header_up X-Forwarded-Proto {http.request.header.X-Forwarded-Proto}
            header_up Upgrade {http.request.header.Upgrade}
            header_up Connection {http.request.header.Connection}
        }
    }
}
```

### 2. Update Production Docker Compose

Edit `docker-compose.production.yml` to add Caddy and Next.js services:

```yaml
services:
  # ... existing services ...

  # Internal Caddy proxy
  caddy:
    image: caddy:2.7-alpine
    container_name: wp-ai-caddy-internal
    restart: unless-stopped
    volumes:
      - ./docker/caddy/Caddyfile.internal:/etc/caddy/Caddyfile:ro
    ports:
      - "127.0.0.1:8090:8090"  # Only accessible from localhost
    networks:
      - wp-ai-internal
      - wp-ai-proxy
    depends_on:
      - wordpress
      - mcp-server

  # Next.js frontend
  nextjs:
    image: node:20-alpine
    container_name: wp-ai-nextjs
    restart: unless-stopped
    working_dir: /app
    command: npm start
    environment:
      - NODE_ENV=production
    volumes:
      - ./web:/app
    networks:
      - wp-ai-proxy
```

### 3. Build and Start Services

```bash
# Build Next.js first
cd web
npm install
npm run build
cd ..

# Start all services including Caddy
docker compose -f docker-compose.production.yml up -d
```

### 4. Update HAProxy Configuration

Much simpler now - just one backend for all WP-AI traffic:

```haproxy
#---------------------------------------------------------------------
# WP-AI Backend Configuration (via internal Caddy)
#---------------------------------------------------------------------

frontend https_front
    # ... your existing config ...

    # WP-AI ACL
    acl is_wpai_domain hdr(host) -i wpai.yourdomain.com

    # Route all WP-AI traffic to Caddy (Caddy handles internal routing)
    use_backend wpai_caddy if is_wpai_domain

# Backend for WP-AI (Caddy internal proxy)
backend wpai_caddy
    mode http
    balance roundrobin
    option httpchk GET /
    http-check expect status 200

    option forwardfor
    http-request set-header X-Forwarded-Proto https
    http-request set-header X-Forwarded-For %[src]
    http-request set-header X-Real-IP %[src]

    # Forward to Caddy internal proxy
    server caddy1 127.0.0.1:8090 check
```

### 5. Reload HAProxy

```bash
# Test configuration
sudo haproxy -c -f /etc/haproxy/haproxy.cfg

# Reload
sudo systemctl reload haproxy
```

## Configuration Examples

### Multi-Domain Setup

If you want WP-AI on a subdomain alongside other services:

```haproxy
frontend https_front
    bind *:443 ssl crt /etc/haproxy/certs/yourdomain.pem

    # Existing services
    acl is_main_site hdr(host) -i yourdomain.com
    acl is_blog hdr(host) -i blog.yourdomain.com

    # WP-AI on subdomain
    acl is_wpai hdr(host) -i wpai.yourdomain.com

    # Routing
    use_backend main_site if is_main_site
    use_backend blog_backend if is_blog
    use_backend wpai_caddy if is_wpai  # Option 2: via Caddy
    # OR
    use_backend wpai_nextjs if is_wpai  # Option 1: direct
```

### Path-Based Routing

If you want WP-AI on a path like `/wpai`:

```haproxy
frontend https_front
    bind *:443 ssl crt /etc/haproxy/certs/yourdomain.pem

    acl is_main_domain hdr(host) -i yourdomain.com
    acl is_wpai_path path_beg /wpai

    # Route /wpai path to WP-AI
    use_backend wpai_caddy if is_main_domain is_wpai_path

# Backend needs path stripping
backend wpai_caddy
    mode http
    option forwardfor

    # Strip /wpai prefix
    http-request replace-path /wpai(/)?(.*) /\2

    server caddy1 127.0.0.1:8090 check
```

**Note:** Path-based routing requires updating WordPress site URL:
```bash
docker exec wp-ai-wordpress wp option update home "https://yourdomain.com/wpai" --allow-root
docker exec wp-ai-wordpress wp option update siteurl "https://yourdomain.com/wpai" --allow-root
```

## Verification

### Test HAProxy Routing

```bash
# Test that HAProxy routes correctly
curl -H "Host: wpai.yourdomain.com" http://localhost/

# If using path-based routing
curl http://localhost/wpai/
```

### Test Internal Caddy

```bash
# Test Caddy directly (if exposed on localhost)
curl http://localhost:8090/

# Check Caddy logs
docker compose logs -f caddy
```

### Test Full Chain

```bash
# Test through HAProxy with SSL
curl -I https://wpai.yourdomain.com

# Test WordPress admin
curl -I https://wpai.yourdomain.com/wp-admin/

# Test GraphQL
curl https://wpai.yourdomain.com/graphql -d '{"query": "{posts{nodes{title}}}"}'
```

## Troubleshooting

### 503 Service Unavailable

Check backend health:
```bash
# Check if services are running
docker compose ps

# Check Caddy health
curl http://localhost:8090/

# Check HAProxy backend status
echo "show stat" | socat stdio /var/run/haproxy/admin.sock | grep wpai
```

### X-Forwarded Headers Not Working

Ensure headers are passed through both proxies:

1. HAProxy sets initial headers:
```haproxy
http-request set-header X-Forwarded-Proto https
http-request set-header X-Real-IP %[src]
```

2. Caddy forwards them to backends:
```caddyfile
reverse_proxy wordpress:80 {
    header_up X-Real-IP {http.request.header.X-Real-IP}
    header_up X-Forwarded-For {http.request.header.X-Forwarded-For}
    header_up X-Forwarded-Proto {http.request.header.X-Forwarded-Proto}
}
```

### Caddy Container Crashes

Check logs:
```bash
docker compose logs caddy

# Verify Caddyfile syntax
docker compose exec caddy caddy validate --config /etc/caddy/Caddyfile
```

### WordPress Redirect Loop

Update WordPress URLs to match HAProxy domain:
```bash
docker exec wp-ai-wordpress wp option update home "https://wpai.yourdomain.com" --allow-root
docker exec wp-ai-wordpress wp option update siteurl "https://wpai.yourdomain.com" --allow-root
```

## Performance Considerations

### Option 1 (Direct) vs Option 2 (Caddy)

**Latency Impact:**
- Option 1: ~1-2ms (HAProxy only)
- Option 2: ~2-3ms (HAProxy + Caddy)

**Additional ~1ms is negligible for most use cases.**

**When to use Option 2:**
- ✅ Cleaner separation of concerns
- ✅ Easier WP-AI routing updates (no HAProxy reload)
- ✅ Want to use Caddy's features (compression, etc.)
- ✅ Multiple WP-AI instances (Caddy can route between them)

**When to use Option 1:**
- ✅ Absolute minimum latency required
- ✅ HAProxy expertise, comfortable with complex configs
- ✅ Want fewer moving parts

## Migration from Standalone to HAProxy

If you're already running WP-AI standalone and want to migrate:

```bash
# 1. Stop standalone deployment
docker compose down

# 2. Start with production config
docker compose -f docker-compose.production.yml up -d

# 3. Configure HAProxy (Option 1 or 2 above)

# 4. Update WordPress URLs
docker exec wp-ai-wordpress wp option update home "https://wpai.yourdomain.com" --allow-root
docker exec wp-ai-wordpress wp option update siteurl "https://wpai.yourdomain.com" --allow-root

# 5. Reload HAProxy
sudo systemctl reload haproxy

# 6. Test
curl -I https://wpai.yourdomain.com
```

## Monitoring

### HAProxy Stats

Add WP-AI backends to your HAProxy stats page:
```
http://yourserver:8404/stats
```

Look for `wpai_*` backends.

### Caddy Metrics (Option 2)

Enable Caddy metrics endpoint:

```caddyfile
{
    servers {
        metrics
    }
}

:8090 {
    # ... existing config ...
}

# Metrics endpoint (internal only)
:9090 {
    metrics /metrics
}
```

Access metrics: `curl http://localhost:9090/metrics`

## Summary

**Recommended Approach:**

For most users integrating into existing HAProxy:
- ✅ Use **Option 2** (HAProxy + Caddy internal proxy)
- ✅ Caddy handles all WP-AI routing complexity
- ✅ HAProxy just forwards to one backend (Caddy)
- ✅ Easy to update and maintain
- ✅ Minimal performance impact (~1ms)

**Configuration Files:**
- HAProxy: Simple backend pointing to Caddy (port 8090)
- Caddy: Internal routing logic for WP-AI services
- Docker Compose: Include Caddy service with port 8090

**Next Steps:**
1. Choose Option 1 or 2 based on your needs
2. Follow setup steps above
3. Test thoroughly with curl commands
4. Monitor HAProxy stats for health checks
5. Update as needed without HAProxy reloads (Option 2)

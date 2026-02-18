# Docker Network Configuration

## Issue
Login and registration were failing because services were running on different Docker networks and couldn't communicate.

## Root Cause
- The `docker-compose.yml` (development) uses default Docker network
- The `docker-compose.production.yml` uses isolated networks (`wp-ai-internal`, `wp-ai-proxy`)
- Services were started with different compose files, causing network isolation

## Symptoms
```
Login error: TypeError: fetch failed
  [cause]: [Error: getaddrinfo EAI_AGAIN mcp-server]
```

The frontend couldn't resolve the `mcp-server` hostname because they were on different networks.

## Solution
All services must use the same compose file. Use `docker-compose.production.yml` for proper network isolation:

```bash
# Correct: Use production compose file
docker compose -f docker-compose.production.yml up -d

# Or: Use the default (which now includes production via docker-compose.override.yml)
docker compose up -d
```

## Network Architecture
- **wp-ai-internal**: Internal services (mcp-server, mariadb, wordpress, redis, web frontend)
- **wp-ai-proxy**: External-facing services (caddy reverse proxy, web frontend)

## Verification
```bash
# Check which networks a container is on
docker inspect wp-ai-mcp --format '{{range $net, $config := .NetworkSettings.Networks}}{{$net}} {{end}}'

# Should show: wp-ai_wp-ai-internal wp-ai_wp-ai-proxy
```

## Files
- `docker-compose.yml` - Development config (single default network)
- `docker-compose.production.yml` - Production config (isolated networks) **← USE THIS**
- `docker-compose.override.yml` - Ensures production is used by default

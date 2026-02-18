# Technical Debt Analysis: Dual Authentication System

## Problem Statement

The MCP server currently has **two conflicting authentication systems** for WordPress:

### 1. Legacy System (Environment Variables)
- **Location**: `mcp-server/src/wp_mcp/config.py`
- **Source**: Environment variables (`WP_USER`, `WP_APP_PASSWORD`)
- **Usage**: Global `gql_client` singleton in `graphql/client.py`
- **Scope**: Single WordPress site, all users share same credentials

### 2. Modern System (Database Connections)
- **Location**: `mcp-server/src/wp_mcp/connection_manager.py`
- **Source**: `wp_wordpress_connections` database table
- **Usage**: Per-user connections with encrypted credentials
- **Scope**: Multi-tenant, each user can have multiple WordPress sites

## Current Issues

### Issue #1: Tools Use Legacy System
**All MCP tools** (`posts.py`, `pages.py`, `media.py`, etc.) import and use the global `gql_client`:

```python
from wp_mcp.graphql.client import gql_client  # ❌ Uses env variables

@mcp.tool()
async def create_post(...):
    data = await gql_client.mutate(...)  # ❌ Ignores user's connection
```

**Problem**: Tools ignore the user's selected WordPress connection and always use environment variable credentials.

### Issue #2: Inconsistent Data Flow
```
User Request → Auth Middleware → Identifies Connection
                                        ↓
                                  (Connection ignored!)
                                        ↓
                               Tool uses gql_client
                                        ↓
                            Uses WP_APP_PASSWORD from env
```

### Issue #3: Multi-Tenancy Broken
- Users can create multiple WordPress connections in the database
- But all tools use the same global credentials
- No way to actually use different connections

### Issue #4: Configuration Confusion
- Environment variables: `WP_URL`, `WP_USER`, `WP_APP_PASSWORD`
- Database connections: `wp_url`, `wp_user`, `wp_app_password`
- Both exist but serve different purposes
- Easy to confuse which system is being used

## Impact Assessment

### Critical Issues
1. **Security**: All users share same WordPress credentials
2. **Multi-tenancy**: Cannot actually support multiple WordPress sites
3. **Maintainability**: Two systems to maintain and debug
4. **Confusion**: Developers don't know which system to use

### Technical Debt Cost
- **Time**: ~30 minutes to debug authentication issues (as we just experienced)
- **Complexity**: Double the code paths for authentication
- **Risk**: Changes to one system may not be reflected in the other

## Solution: Migrate to Database-Only System

### Architecture Changes

#### Phase 1: Refactor GraphQL Client
**Current**:
```python
# Singleton with global credentials
gql_client = GraphQLClient()  # Uses config.wp_auth
```

**New**:
```python
# Factory function that creates client per connection
def get_graphql_client(connection_id: int, user_id: int) -> GraphQLClient:
    """Get GraphQL client for specific connection."""
    connection = await connection_manager.get_connection(connection_id, user_id)
    return GraphQLClient(
        endpoint=connection['wp_graphql_endpoint'],
        auth=(connection['wp_user'], connection['wp_app_password'])
    )
```

#### Phase 2: Update All Tools
**Current**:
```python
@mcp.tool()
async def create_post(...):
    data = await gql_client.mutate(...)
```

**New**:
```python
@mcp.tool()
async def create_post(..., _context: dict):
    # Get user's active connection from context
    connection_id = _context.get('connection_id')
    user_id = _context.get('user_id')

    # Get connection-specific GraphQL client
    client = await get_graphql_client(connection_id, user_id)
    data = await client.mutate(...)
```

#### Phase 3: Remove Legacy System
- Delete `config.wp_auth` property
- Remove `WP_USER`, `WP_APP_PASSWORD` from environment
- Keep only `WP_URL` and `WP_GRAPHQL_ENDPOINT` as defaults for initial setup
- Update documentation to reflect database-only authentication

### Migration Steps

1. **Add `get_graphql_client()` factory function**
2. **Update `GraphQLClient` to accept credentials in constructor**
3. **Modify all tools to get context and use factory**
4. **Update tests to use database connections**
5. **Remove global `gql_client` singleton**
6. **Clean up environment variables**
7. **Update docker-compose and documentation**

### Benefits

✅ **True multi-tenancy**: Each user uses their own credentials
✅ **Security**: No shared credentials across users
✅ **Simplicity**: Single source of truth (database)
✅ **Maintainability**: One system to maintain
✅ **Flexibility**: Easy to add/remove connections per user

### Risks & Mitigation

**Risk**: Breaking existing deployments
**Mitigation**: Keep environment variables as fallback for backwards compatibility

**Risk**: Performance (database query per request)
**Mitigation**: Add connection caching in connection_manager

**Risk**: Context not available in all tools
**Mitigation**: Update FastMCP tool decorator to always provide context

## Estimated Effort

- **Analysis**: 30 minutes ✅ (done)
- **Refactoring**: 2-3 hours
  - GraphQL client changes: 30 min
  - Update 7 tool files: 1 hour
  - Testing: 1 hour
  - Documentation: 30 min
- **Total**: ~3 hours

## Files to Modify

### Core Changes (Required)
1. `mcp-server/src/wp_mcp/graphql/client.py` - Factory function + constructor
2. `mcp-server/src/wp_mcp/tools/posts.py` - Update all tools
3. `mcp-server/src/wp_mcp/tools/pages.py` - Update all tools
4. `mcp-server/src/wp_mcp/tools/media.py` - Update all tools
5. `mcp-server/src/wp_mcp/tools/blocks.py` - Update all tools
6. `mcp-server/src/wp_mcp/tools/taxonomies.py` - Update all tools
7. `mcp-server/src/wp_mcp/tools/search.py` - Update all tools
8. `mcp-server/src/wp_mcp/tools/revisions.py` - Update all tools

### Configuration Changes (Optional)
9. `mcp-server/src/wp_mcp/config.py` - Mark as deprecated
10. `docker-compose.production.yml` - Update comments
11. `.env.example` - Update documentation

## Recommendation

**Proceed with refactoring immediately.** The technical debt is causing active bugs and confusion. The fix is straightforward and will prevent future authentication issues.

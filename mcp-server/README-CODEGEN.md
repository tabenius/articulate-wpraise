# Auto-Generated MCP Tools from WordPress GraphQL

This document explains the automated code generation pipeline that creates type-safe MCP tools from your WordPress GraphQL schema.

## Overview

The code generation pipeline has 3 layers:

```
WordPress GraphQL Schema
        ↓ (introspect_graphql.py)
Python MCP Tools (auto-generated)
        ↓ (generate_schemas.py)
JSON Schema Definitions
        ↓ (generate-mcp-types.mjs)
TypeScript Types (type-safe client)
```

## Setup

### 1. Enable WordPress GraphQL Introspection

In WordPress admin:
1. Go to **GraphQL → Settings**
2. Under **GraphQL Introspection**, enable **Public Introspection**
3. Save changes

Alternatively, add to `wp-config.php`:
```php
define( 'GRAPHQL_DEBUG', true );
```

### 2. Generate the Full Pipeline

```bash
# Step 1: Fetch WordPress GraphQL schema
docker exec articulate-mcp python3 /app/scripts/introspect_graphql.py http://wordpress:80/graphql > mcp-server/schema.json

# Step 2: Generate Python MCP tools from schema
docker exec articulate-mcp python3 /app/scripts/generate_mcp_from_graphql.py \
  --schema /app/schema.json \
  --output /app/src/articulate_mcp/tools/generated

# Step 3: Generate JSON schemas from Python tools
docker exec articulate-mcp python3 /app/scripts/generate_schemas.py > schemas/mcp-tools.json

# Step 4: Generate TypeScript types from JSON schemas
cd web && npm run generate-types
```

### 3. Use Auto-Generated Tools

Register the generated tools in your MCP server:

```python
# In src/articulate_mcp/server.py
from articulate_mcp.tools import generated as generated_tools

# Register generated tools
generated_tools.register(mcp)
```

## Benefits

### 1. **Single Source of Truth**
WordPress GraphQL schema defines all available operations. Everything else is derived.

### 2. **Automatic Sync**
When WordPress schema changes (new plugin, custom post type, etc.):
```bash
npm run codegen  # Re-runs entire pipeline
```

### 3. **End-to-End Type Safety**
```typescript
// TypeScript knows exact response shape
const post = await callMCPTool("createPost", {
  title: "Hello",  // TypeScript validates this matches CreatePostInput
});

// TypeScript knows post.id is number (not undefined!)
console.log(post.id);  // Type: number
```

### 4. **Zero Manual Maintenance**
- No hand-written GraphQL queries
- No manual type definitions
- No response parsing code
- Automatic field additions when schema evolves

## Example Generated Code

### Auto-Generated Python MCP Tool

```python
@mcp.tool()
async def create_post(
    title: str,
    content: str | None = None,
    status: str | None = None,
    context: dict | None = None
) -> dict[str, Any]:
    """Create a new WordPress post."""
    connection_id, user_id = get_connection_info(context)
    client = await get_graphql_client(connection_id, user_id)

    query = """
    mutation CreatePost($title: String!, $content: String, $status: PostStatusEnum) {
      createPost(input: {title: $title, content: $content, status: $status}) {
        post {
          databaseId
          title
          slug
          status
          content
          date
          modified
        }
      }
    }
    """

    variables = {"title": title, "content": content, "status": status}
    data = await client.query(query, variables={k: v for k, v in variables.items() if v is not None}, user_id=user_id)
    return data.get("createPost", {})
```

### Auto-Generated TypeScript Types

```typescript
/**
 * Response from create_post
 * Create a new WordPress post.
 */
export type CreatePostResponse = {
  id: number;
  title: string;
  slug: string | null;
  status: string;
  content?: string | null;
  date?: string;
  modified?: string;
  author?: string;
};
```

## Schema Version Checking

The generated code includes version checking to ensure client/server compatibility:

```typescript
import { MCP_SCHEMA_VERSION } from '@/types/mcp-generated';

// Check version on startup
const serverVersion = await callMCPTool("get_schema_version");
if (serverVersion !== MCP_SCHEMA_VERSION) {
  console.warn(`Schema mismatch: client=${MCP_SCHEMA_VERSION}, server=${serverVersion}`);
  // Prompt user to run `npm run codegen`
}
```

## Troubleshooting

### Introspection Disabled
**Error**: `GraphQL introspection is not allowed for public requests`

**Solution**: Enable introspection in WPGraphQL settings or add authentication headers:

```python
# In introspect_graphql.py
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {WORDPRESS_TOKEN}"  # Add auth
}
```

### Type Mismatches
**Error**: `Property 'id' does not exist on type 'unknown'`

**Solution**: Regenerate types:
```bash
npm run generate-types
```

### Missing Fields in Response
**Error**: Response doesn't include expected fields

**Solution**: Update the GraphQL query template in `generate_mcp_from_graphql.py` to request more fields, then regenerate.

## Future Enhancements

1. **Watch Mode**: Auto-regenerate when schema changes
2. **Partial Generation**: Only regenerate changed tools
3. **Custom Field Mappings**: Configure which fields to include/exclude
4. **Validation Generation**: Auto-generate Pydantic models for runtime validation
5. **Documentation Generation**: Auto-generate API docs from GraphQL descriptions

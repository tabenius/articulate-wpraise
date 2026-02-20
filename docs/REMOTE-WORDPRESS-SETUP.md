# Remote WordPress Setup for WP-AI

## Enable GraphQL Introspection

For WP-AI's code generation to work with your remote WordPress site, you need to enable GraphQL introspection.

### Option 1: Install MU-Plugin (Recommended)

1. Copy the MU-plugin to your WordPress installation:

```bash
# Download the plugin
wget https://raw.githubusercontent.com/your-repo/wp-ai/main/docker/wordpress/mu-plugins/enable-graphql-introspection.php

# Upload to your WordPress site
scp enable-graphql-introspection.php user@yoursite.com:/var/www/html/wp-content/mu-plugins/
```

2. The plugin will be automatically activated (MU-plugins are always active)

### Option 2: Add to functions.php

Add this to your theme's `functions.php`:

```php
// Enable GraphQL introspection for WP-AI
add_filter( 'graphql_introspection_enabled_for_public_requests', '__return_true' );
```

### Option 3: Enable in WPGraphQL Settings

1. Log in to WordPress admin
2. Go to **GraphQL → Settings**
3. Under **GraphQL Introspection**, enable **Public Introspection**
4. Save changes

## Security Considerations

Enabling public introspection allows anyone to query your GraphQL schema structure. This is generally safe as it only reveals the API structure, not actual data.

**For production sites**, consider:

1. **Use authenticated introspection** instead:
   - Don't enable public introspection
   - Configure WP-AI with WordPress admin credentials
   - Introspection will work only for authenticated users

2. **Disable after code generation**:
   - Enable introspection
   - Run code generation
   - Disable introspection
   - Re-run only when schema changes

3. **Use environment-based toggle**:
```php
// Only enable in development/staging
if ( defined( 'WP_ENV' ) && WP_ENV !== 'production' ) {
    add_filter( 'graphql_introspection_enabled_for_public_requests', '__return_true' );
}
```

## Testing the Setup

Test that introspection is enabled:

```bash
curl -X POST https://yoursite.com/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{__schema{queryType{name}}}"}'
```

Expected response:
```json
{
  "data": {
    "__schema": {
      "queryType": {
        "name": "RootQuery"
      }
    }
  }
}
```

If you see an error about introspection not being allowed, the setup isn't complete yet.

## Connecting to WP-AI

After enabling introspection, configure your remote WordPress connection in WP-AI:

1. Go to **Connections** in WP-AI
2. Click **Add Connection**
3. Enter your WordPress URL (e.g., `https://yoursite.com`)
4. Enter WordPress credentials
5. Click **Test Connection**
6. If successful, click **Save**

WP-AI will now be able to:
- Fetch your WordPress GraphQL schema
- Auto-generate type-safe MCP tools
- Keep types in sync with your WordPress installation

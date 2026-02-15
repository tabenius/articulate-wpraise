#!/bin/bash
set -e

echo "==> Waiting for WordPress to be ready..."
until curl -sf http://wordpress:80/wp-admin/install.php > /dev/null 2>&1; do
  echo "    WordPress not ready yet, retrying in 5s..."
  sleep 5
done

echo "==> WordPress is up. Running setup..."

# Check if WordPress is already installed
if wp core is-installed --path=/var/www/html --allow-root 2>/dev/null; then
  echo "==> WordPress already installed. Skipping core install."
else
  echo "==> Installing WordPress core..."
  wp core install \
    --url="http://localhost:8080" \
    --title="WP-AI Dev" \
    --admin_user="${WP_ADMIN_USER:-admin}" \
    --admin_password="${WP_ADMIN_PASS:-admin123}" \
    --admin_email="admin@wp-ai.local" \
    --skip-email \
    --path=/var/www/html \
    --allow-root
fi

# Set permalinks (required for WPGraphQL)
echo "==> Setting permalink structure..."
wp rewrite structure '/%postname%/' --path=/var/www/html --allow-root
wp rewrite flush --path=/var/www/html --allow-root

# Install and activate WPGraphQL
echo "==> Installing WPGraphQL..."
if wp plugin is-installed wp-graphql --path=/var/www/html --allow-root 2>/dev/null; then
  wp plugin activate wp-graphql --path=/var/www/html --allow-root 2>/dev/null || true
  echo "    WPGraphQL already installed."
else
  wp plugin install wp-graphql --activate --path=/var/www/html --allow-root
fi

# Install WPGraphQL Content Blocks
echo "==> Installing WPGraphQL Content Blocks..."
if wp plugin is-installed wp-graphql-content-blocks --path=/var/www/html --allow-root 2>/dev/null; then
  wp plugin activate wp-graphql-content-blocks --path=/var/www/html --allow-root 2>/dev/null || true
  echo "    WPGraphQL Content Blocks already installed."
else
  # Download latest release
  curl -L -o /tmp/wp-graphql-content-blocks.zip \
    "https://github.com/wpengine/wp-graphql-content-blocks/releases/latest/download/wp-graphql-content-blocks.zip" 2>/dev/null
  if [ -f /tmp/wp-graphql-content-blocks.zip ]; then
    wp plugin install /tmp/wp-graphql-content-blocks.zip --activate --path=/var/www/html --allow-root
    rm -f /tmp/wp-graphql-content-blocks.zip
  else
    echo "    WARNING: Could not download WPGraphQL Content Blocks plugin."
  fi
fi

# Enable GraphQL introspection (useful for development)
echo "==> Configuring WPGraphQL settings..."
wp option update graphql_general_settings '{"show_graphiql":"on","delete_data_on_deactivate":""}' --format=json --path=/var/www/html --allow-root 2>/dev/null || true

# Create application password for API authentication
echo "==> Creating application password..."
APP_PASS=$(wp user application-password create 1 "wp-ai-mcp" --porcelain --path=/var/www/html --allow-root 2>/dev/null || echo "")
if [ -n "$APP_PASS" ]; then
  echo "========================================="
  echo "  WP Application Password: $APP_PASS"
  echo "  Add this to your .env files as WP_APP_PASSWORD"
  echo "========================================="
else
  echo "    Application password may already exist."
fi

# Create a sample post with blocks for testing
echo "==> Creating sample content..."
SAMPLE_CONTENT='<!-- wp:heading {"level":1} -->
<h1 class="wp-block-heading">Welcome to WP-AI</h1>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>This is a sample post created by the WP-AI setup script. You can edit this content using the AI chat or the block editor.</p>
<!-- /wp:paragraph -->

<!-- wp:heading {"level":2} -->
<h2 class="wp-block-heading">Features</h2>
<!-- /wp:heading -->

<!-- wp:list -->
<ul class="wp-block-list">
<li>AI-powered content editing via chat</li>
<li>Visual block editor with drag-and-drop</li>
<li>Real-time sync between chat and editor</li>
<li>WordPress block format compatibility</li>
</ul>
<!-- /wp:list -->

<!-- wp:quote -->
<blockquote class="wp-block-quote"><p>The future of content creation is AI-assisted.</p><cite>WP-AI Team</cite></blockquote>
<!-- /wp:quote -->

<!-- wp:separator -->
<hr class="wp-block-separator has-alpha-channel-opacity"/>
<!-- /wp:separator -->

<!-- wp:paragraph -->
<p>Start editing by typing a message in the chat panel on the left, or click on any block above to edit it directly.</p>
<!-- /wp:paragraph -->'

EXISTING=$(wp post list --post_type=post --name=welcome-to-wp-ai --format=ids --path=/var/www/html --allow-root 2>/dev/null)
if [ -z "$EXISTING" ]; then
  wp post create \
    --post_title="Welcome to WP-AI" \
    --post_content="$SAMPLE_CONTENT" \
    --post_status=publish \
    --path=/var/www/html \
    --allow-root
  echo "    Sample post created."
else
  echo "    Sample post already exists."
fi

echo "==> Setup complete!"
echo "    WordPress: http://localhost:8080"
echo "    WP Admin:  http://localhost:8080/wp-admin"
echo "    GraphQL:   http://localhost:8080/graphql"

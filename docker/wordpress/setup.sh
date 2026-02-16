#!/bin/bash
set -e

# =============================================================================
# WP-AI WordPress Setup Script
# =============================================================================
# This script handles the initial WordPress setup including:
# - Core installation and configuration
# - Plugin installation (WPGraphQL, Content Blocks, custom plugins)
# - Database migrations
# - Sample content creation
# =============================================================================

# Color output for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
readonly WORDPRESS_PATH="/var/www/html"
readonly MAX_RETRIES=30
readonly RETRY_DELAY=5
readonly LOG_FILE="/tmp/wp-setup.log"

# =============================================================================
# Logging Functions
# =============================================================================

log_info() {
  local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
  echo -e "${BLUE}[INFO]${NC} ${timestamp} - $1" | tee -a "$LOG_FILE"
}

log_success() {
  local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
  echo -e "${GREEN}[SUCCESS]${NC} ${timestamp} - $1" | tee -a "$LOG_FILE"
}

log_warning() {
  local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
  echo -e "${YELLOW}[WARNING]${NC} ${timestamp} - $1" | tee -a "$LOG_FILE"
}

log_error() {
  local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
  echo -e "${RED}[ERROR]${NC} ${timestamp} - $1" | tee -a "$LOG_FILE"
}

log_section() {
  echo ""
  echo -e "${BLUE}========================================${NC}"
  echo -e "${BLUE}==> $1${NC}"
  echo -e "${BLUE}========================================${NC}"
}

# =============================================================================
# Validation Functions
# =============================================================================

validate_environment() {
  log_section "Validating Environment"

  local errors=0

  # Check required environment variables
  if [ -z "$WORDPRESS_DB_HOST" ]; then
    log_error "WORDPRESS_DB_HOST is not set"
    ((errors++))
  fi

  if [ -z "$WORDPRESS_DB_NAME" ]; then
    log_error "WORDPRESS_DB_NAME is not set"
    ((errors++))
  fi

  if [ -z "$WORDPRESS_DB_USER" ]; then
    log_error "WORDPRESS_DB_USER is not set"
    ((errors++))
  fi

  if [ -z "$WORDPRESS_DB_PASSWORD" ]; then
    log_error "WORDPRESS_DB_PASSWORD is not set"
    ((errors++))
  fi

  # Check if WP-CLI is available
  if ! command -v wp &> /dev/null; then
    log_error "WP-CLI is not installed"
    ((errors++))
  else
    log_success "WP-CLI found: $(wp --version)"
  fi

  # Check if MySQL client is available
  if ! command -v mysql &> /dev/null; then
    log_warning "MySQL client not found (needed for migrations)"
  else
    log_success "MySQL client found"
  fi

  if [ $errors -gt 0 ]; then
    log_error "Environment validation failed with $errors error(s)"
    return 1
  fi

  log_success "Environment validation passed"
  return 0
}

# =============================================================================
# Health Check Functions
# =============================================================================

wait_for_wordpress() {
  log_section "Waiting for WordPress"

  local retries=0
  until curl -sf http://wordpress:80/wp-admin/install.php > /dev/null 2>&1; do
    retries=$((retries + 1))
    if [ $retries -ge $MAX_RETRIES ]; then
      log_error "WordPress failed to start after $MAX_RETRIES attempts"
      return 1
    fi
    log_info "WordPress not ready yet (attempt $retries/$MAX_RETRIES), retrying in ${RETRY_DELAY}s..."
    sleep $RETRY_DELAY
  done

  log_success "WordPress is ready"
  return 0
}

wait_for_database() {
  log_info "Waiting for database connection..."

  local retries=0
  until wp db check --path="$WORDPRESS_PATH" --allow-root 2>/dev/null; do
    retries=$((retries + 1))
    if [ $retries -ge $MAX_RETRIES ]; then
      log_error "Database failed to connect after $MAX_RETRIES attempts"
      return 1
    fi
    log_info "Database not ready (attempt $retries/$MAX_RETRIES), retrying in ${RETRY_DELAY}s..."
    sleep $RETRY_DELAY
  done

  log_success "Database connection established"
  return 0
}

# =============================================================================
# WordPress Core Setup
# =============================================================================

install_wordpress_core() {
  log_section "WordPress Core Installation"

  if wp core is-installed --path="$WORDPRESS_PATH" --allow-root 2>/dev/null; then
    log_info "WordPress already installed, skipping core install"

    # Verify installation
    local site_url=$(wp option get siteurl --path="$WORDPRESS_PATH" --allow-root 2>/dev/null)
    local admin_email=$(wp option get admin_email --path="$WORDPRESS_PATH" --allow-root 2>/dev/null)
    log_info "Site URL: $site_url"
    log_info "Admin email: $admin_email"
    return 0
  fi

  log_info "Installing WordPress core..."

  wp core install \
    --url="http://localhost:8080" \
    --title="WP-AI Dev" \
    --admin_user="${WP_ADMIN_USER:-admin}" \
    --admin_password="${WP_ADMIN_PASS:-admin123}" \
    --admin_email="admin@wp-ai.local" \
    --skip-email \
    --path="$WORDPRESS_PATH" \
    --allow-root

  if [ $? -eq 0 ]; then
    log_success "WordPress core installed successfully"
    log_warning "Admin credentials: ${WP_ADMIN_USER:-admin} / ${WP_ADMIN_PASS:-admin123}"
  else
    log_error "WordPress core installation failed"
    return 1
  fi

  return 0
}

configure_permalinks() {
  log_section "Configuring Permalinks"

  log_info "Setting permalink structure (required for WPGraphQL)..."
  wp rewrite structure '/%postname%/' --path="$WORDPRESS_PATH" --allow-root
  wp rewrite flush --path="$WORDPRESS_PATH" --allow-root

  log_success "Permalinks configured"
}

# =============================================================================
# Plugin Installation
# =============================================================================

install_wpgraphql() {
  log_section "Installing WPGraphQL"

  if wp plugin is-installed wp-graphql --path="$WORDPRESS_PATH" --allow-root 2>/dev/null; then
    local status=$(wp plugin status wp-graphql --path="$WORDPRESS_PATH" --allow-root 2>&1 | grep "Status:" | awk '{print $2}')

    if [ "$status" = "Active" ]; then
      log_info "WPGraphQL already installed and active"
      local version=$(wp plugin get wp-graphql --field=version --path="$WORDPRESS_PATH" --allow-root 2>/dev/null)
      log_info "Version: $version"
      return 0
    else
      log_info "WPGraphQL installed but not active, activating..."
      wp plugin activate wp-graphql --path="$WORDPRESS_PATH" --allow-root
    fi
  else
    log_info "Installing WPGraphQL plugin..."
    wp plugin install wp-graphql --activate --path="$WORDPRESS_PATH" --allow-root
  fi

  # Verify activation
  if wp plugin is-active wp-graphql --path="$WORDPRESS_PATH" --allow-root 2>/dev/null; then
    log_success "WPGraphQL installed and activated"
  else
    log_error "WPGraphQL installation failed"
    return 1
  fi

  return 0
}

install_wpgraphql_content_blocks() {
  log_section "Installing WPGraphQL Content Blocks"

  if wp plugin is-installed wp-graphql-content-blocks --path="$WORDPRESS_PATH" --allow-root 2>/dev/null; then
    local status=$(wp plugin status wp-graphql-content-blocks --path="$WORDPRESS_PATH" --allow-root 2>&1 | grep "Status:" | awk '{print $2}')

    if [ "$status" = "Active" ]; then
      log_info "WPGraphQL Content Blocks already installed and active"
      return 0
    else
      log_info "WPGraphQL Content Blocks installed but not active, activating..."
      wp plugin activate wp-graphql-content-blocks --path="$WORDPRESS_PATH" --allow-root
      log_success "WPGraphQL Content Blocks activated"
      return 0
    fi
  fi

  log_info "Downloading WPGraphQL Content Blocks..."
  local download_url="https://github.com/wpengine/wp-graphql-content-blocks/releases/latest/download/wp-graphql-content-blocks.zip"
  local temp_file="/tmp/wp-graphql-content-blocks.zip"

  if curl -L -f -o "$temp_file" "$download_url" 2>/dev/null; then
    log_success "Downloaded successfully"

    log_info "Installing plugin..."
    wp plugin install "$temp_file" --activate --path="$WORDPRESS_PATH" --allow-root
    rm -f "$temp_file"

    if wp plugin is-active wp-graphql-content-blocks --path="$WORDPRESS_PATH" --allow-root 2>/dev/null; then
      log_success "WPGraphQL Content Blocks installed and activated"
    else
      log_error "Plugin installation succeeded but activation failed"
      return 1
    fi
  else
    log_error "Failed to download WPGraphQL Content Blocks"
    log_warning "Continuing without this plugin - some features may not work"
    return 0  # Don't fail the entire setup
  fi

  return 0
}

configure_wpgraphql() {
  log_section "Configuring WPGraphQL"

  log_info "Enabling GraphQL IDE and introspection..."
  wp option update graphql_general_settings '{"show_graphiql":"on","delete_data_on_deactivate":""}' --format=json --path="$WORDPRESS_PATH" --allow-root 2>/dev/null || true

  log_success "WPGraphQL configured"
}

install_custom_plugins() {
  log_section "Installing Custom Plugins"

  if [ ! -d "/tmp/wp-ai-plugins" ]; then
    log_warning "No custom plugins found at /tmp/wp-ai-plugins"
    return 0
  fi

  local plugin_count=$(find /tmp/wp-ai-plugins -maxdepth 1 -type d | tail -n +2 | wc -l)
  if [ $plugin_count -eq 0 ]; then
    log_warning "Custom plugins directory is empty"
    return 0
  fi

  log_info "Copying $plugin_count custom plugin(s)..."
  cp -r /tmp/wp-ai-plugins/* "$WORDPRESS_PATH/wp-content/plugins/"

  # List and activate each custom plugin
  for plugin_dir in /tmp/wp-ai-plugins/*/; do
    local plugin_name=$(basename "$plugin_dir")

    if [ -d "$WORDPRESS_PATH/wp-content/plugins/$plugin_name" ]; then
      log_info "Activating custom plugin: $plugin_name"

      if wp plugin activate "$plugin_name" --path="$WORDPRESS_PATH" --allow-root 2>/dev/null; then
        log_success "  ✓ $plugin_name activated"
      else
        log_warning "  ✗ Failed to activate $plugin_name"
      fi
    fi
  done

  return 0
}

# =============================================================================
# Authentication Setup
# =============================================================================

create_application_password() {
  log_section "Creating Application Password"

  # Check if application password already exists
  local existing=$(wp user application-password list 1 --field=name --path="$WORDPRESS_PATH" --allow-root 2>/dev/null | grep "wp-ai-mcp" || echo "")

  if [ -n "$existing" ]; then
    log_info "Application password 'wp-ai-mcp' already exists"
    log_warning "To create a new password, delete the existing one first:"
    log_warning "  wp user application-password delete 1 wp-ai-mcp --path=$WORDPRESS_PATH --allow-root"
    return 0
  fi

  log_info "Generating new application password..."
  local app_pass=$(wp user application-password create 1 "wp-ai-mcp" --porcelain --path="$WORDPRESS_PATH" --allow-root 2>/dev/null)

  if [ -n "$app_pass" ]; then
    echo ""
    echo -e "${GREEN}=========================================${NC}"
    echo -e "${GREEN}  Application Password Created${NC}"
    echo -e "${GREEN}=========================================${NC}"
    echo -e "${YELLOW}  Password: $app_pass${NC}"
    echo -e "${GREEN}=========================================${NC}"
    echo -e "Add this to your environment files:"
    echo -e "  ${BLUE}WP_APP_PASSWORD=$app_pass${NC}"
    echo -e "${GREEN}=========================================${NC}"
    echo ""
    log_success "Application password created"
  else
    log_error "Failed to create application password"
    return 1
  fi

  return 0
}

# =============================================================================
# Content Creation
# =============================================================================

create_sample_content() {
  log_section "Creating Sample Content"

  # Check if sample post already exists
  local existing=$(wp post list --post_type=post --name=welcome-to-wp-ai --format=ids --path="$WORDPRESS_PATH" --allow-root 2>/dev/null)

  if [ -n "$existing" ]; then
    log_info "Sample post already exists (ID: $existing)"
    return 0
  fi

  log_info "Creating sample post..."

  local sample_content='<!-- wp:heading {"level":1} -->
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
<li>Featured images with upload support</li>
<li>Categories and tags management</li>
<li>Post scheduling for future publication</li>
<li>Multi-user authentication with JWT</li>
</ul>
<!-- /wp:list -->

<!-- wp:quote -->
<blockquote class="wp-block-quote"><p>The future of content creation is AI-assisted.</p><cite>WP-AI Team</cite></blockquote>
<!-- /wp:quote -->

<!-- wp:separator -->
<hr class="wp-block-separator has-alpha-channel-opacity"/>
<!-- /wp:separator -->

<!-- wp:paragraph -->
<p>Start editing by typing a message in the chat panel, or use the visual block editor to modify content directly.</p>
<!-- /wp:paragraph -->'

  local post_id=$(wp post create \
    --post_title="Welcome to WP-AI" \
    --post_content="$sample_content" \
    --post_status=publish \
    --porcelain \
    --path="$WORDPRESS_PATH" \
    --allow-root)

  if [ -n "$post_id" ]; then
    log_success "Sample post created (ID: $post_id)"
  else
    log_warning "Failed to create sample post"
  fi

  return 0
}

# =============================================================================
# Database Migrations
# =============================================================================

run_migrations() {
  log_section "Running Database Migrations"

  if [ ! -f "/usr/local/bin/run-migrations.sh" ]; then
    log_warning "Migration runner not found at /usr/local/bin/run-migrations.sh"
    return 0
  fi

  if [ ! -d "/usr/local/migrations" ]; then
    log_warning "Migrations directory not found at /usr/local/migrations"
    return 0
  fi

  log_info "Executing migration runner..."
  bash /usr/local/bin/run-migrations.sh

  # Check migration version
  local version=$(wp option get wp_ai_migration_version --path="$WORDPRESS_PATH" --allow-root 2>/dev/null || echo "0")
  log_success "Current migration version: $version"

  return 0
}

# =============================================================================
# Summary Report
# =============================================================================

print_summary() {
  log_section "Setup Summary"

  # Gather information
  local site_url=$(wp option get siteurl --path="$WORDPRESS_PATH" --allow-root 2>/dev/null)
  local wp_version=$(wp core version --path="$WORDPRESS_PATH" --allow-root 2>/dev/null)
  local active_plugins=$(wp plugin list --status=active --field=name --path="$WORDPRESS_PATH" --allow-root 2>/dev/null | wc -l)
  local migration_version=$(wp option get wp_ai_migration_version --path="$WORDPRESS_PATH" --allow-root 2>/dev/null || echo "0")
  local post_count=$(wp post list --post_type=post --format=count --path="$WORDPRESS_PATH" --allow-root 2>/dev/null || echo "0")

  echo ""
  echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
  echo -e "${GREEN}║                  WP-AI Setup Complete!                     ║${NC}"
  echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
  echo ""
  echo -e "${BLUE}WordPress Information:${NC}"
  echo -e "  Version:          $wp_version"
  echo -e "  Site URL:         $site_url"
  echo -e "  Active plugins:   $active_plugins"
  echo -e "  Posts:            $post_count"
  echo -e "  Migration version: $migration_version"
  echo ""
  echo -e "${BLUE}Access Points:${NC}"
  echo -e "  ${GREEN}Frontend:${NC}     http://localhost:8080"
  echo -e "  ${GREEN}Admin Panel:${NC}  http://localhost:8080/wp-admin"
  echo -e "  ${GREEN}GraphQL IDE:${NC}  http://localhost:8080/graphql"
  echo -e "  ${GREEN}Next.js App:${NC}  http://localhost:3000"
  echo ""
  echo -e "${BLUE}Credentials:${NC}"
  echo -e "  ${GREEN}Username:${NC}     ${WP_ADMIN_USER:-admin}"
  echo -e "  ${GREEN}Password:${NC}     ${WP_ADMIN_PASS:-admin123}"
  echo ""
  echo -e "${YELLOW}Note: Application password shown above (if created)${NC}"
  echo ""
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
  log_info "Starting WP-AI WordPress setup..."
  log_info "Log file: $LOG_FILE"

  # Initialize log file
  echo "WP-AI WordPress Setup Log - $(date)" > "$LOG_FILE"

  # Run setup steps in order
  validate_environment || exit 1
  wait_for_wordpress || exit 1
  wait_for_database || exit 1
  install_wordpress_core || exit 1
  configure_permalinks || exit 1
  install_wpgraphql || exit 1
  install_wpgraphql_content_blocks || exit 1
  configure_wpgraphql || exit 1
  install_custom_plugins || exit 1
  create_application_password || exit 1
  create_sample_content || exit 1
  run_migrations || exit 1

  # Print summary
  print_summary

  log_success "Setup completed successfully!"
  log_info "Full log available at: $LOG_FILE"

  exit 0
}

# Run main function
main

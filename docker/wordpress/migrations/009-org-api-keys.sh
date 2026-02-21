#!/bin/bash
set -e

echo "[Migration 009] Adding organization API keys and org-owned connections..."

# Create organization API keys table
wp db query "
CREATE TABLE IF NOT EXISTS wp_org_api_keys (
  id BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  organization_id BIGINT(20) UNSIGNED NOT NULL,
  created_by BIGINT(20) UNSIGNED NOT NULL,
  key_hash VARCHAR(255) NOT NULL COMMENT 'SHA-256 hash of the API key',
  key_prefix VARCHAR(16) NOT NULL COMMENT 'First 12 chars for display',
  scopes VARCHAR(255) DEFAULT 'register_connection' COMMENT 'Comma-separated scopes',
  description VARCHAR(500) COMMENT 'User-provided description',
  expires_at DATETIME NOT NULL,
  used_at DATETIME COMMENT 'When key was used for registration (single-use)',
  is_active TINYINT(1) DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY unique_key_hash (key_hash),
  KEY idx_org (organization_id),
  KEY idx_created_by (created_by),
  KEY idx_prefix (key_prefix),
  KEY idx_active_expires (is_active, expires_at),
  CONSTRAINT fk_apikey_org FOREIGN KEY (organization_id) REFERENCES wp_organizations(id) ON DELETE CASCADE,
  CONSTRAINT fk_apikey_creator FOREIGN KEY (created_by) REFERENCES wp_users_auth(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
" --allow-root

echo "✓ Created wp_org_api_keys table"

# Add organization_id to connections table (nullable for backward compatibility)
wp db query "
ALTER TABLE wp_wordpress_connections
  ADD COLUMN IF NOT EXISTS organization_id BIGINT(20) UNSIGNED NULL AFTER user_id,
  ADD KEY IF NOT EXISTS idx_org_id (organization_id);
" --allow-root 2>/dev/null || echo "Column organization_id may already exist"

echo "✓ Added organization_id column to wp_wordpress_connections"

# Add foreign key constraint for organization_id
wp db query "
ALTER TABLE wp_wordpress_connections
  ADD CONSTRAINT fk_connection_org FOREIGN KEY (organization_id) REFERENCES wp_organizations(id) ON DELETE CASCADE;
" --allow-root 2>/dev/null || echo "Foreign key fk_connection_org may already exist"

echo "✓ Added foreign key constraint for organization connections"

# Drop old unique constraint that only considered user_id and name
wp db query "
ALTER TABLE wp_wordpress_connections
  DROP KEY user_name;
" --allow-root 2>/dev/null || echo "Old unique key user_name may not exist"

echo "✓ Dropped old unique constraint"

# Add new composite unique constraint that allows same name for different orgs
wp db query "
ALTER TABLE wp_wordpress_connections
  ADD UNIQUE KEY unique_connection_name (user_id, organization_id, name);
" --allow-root 2>/dev/null || echo "Unique key unique_connection_name may already exist"

echo "✓ Added new unique constraint allowing org-scoped connection names"

echo "[Migration 009] ✅ Organization API keys migration completed successfully"

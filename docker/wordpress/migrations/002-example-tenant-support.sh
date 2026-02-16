#!/bin/bash
# Migration 002: Example - Add tenant support to posts
# This migration demonstrates how to add columns for multi-tenancy
#
# ROLLBACK: To rollback, run:
#   wp db query "ALTER TABLE wp_posts DROP COLUMN IF EXISTS tenant_id;" --allow-root
#   wp db query "DROP TABLE IF EXISTS wp_tenants;" --allow-root

set -e

echo "Adding tenant support..."

# Create tenants table
wp db query "
CREATE TABLE IF NOT EXISTS wp_tenants (
  id BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(255) NOT NULL,
  status VARCHAR(20) DEFAULT 'active',
  db_host VARCHAR(255),
  db_name VARCHAR(255),
  db_user VARCHAR(255),
  db_password VARCHAR(255),
  wp_url VARCHAR(255),
  mcp_url VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY slug (slug)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
" --allow-root

echo "✓ Tenants table created"

# Add tenant_id column to posts table if it doesn't exist
wp db query "
ALTER TABLE wp_posts
ADD COLUMN IF NOT EXISTS tenant_id BIGINT(20) UNSIGNED DEFAULT NULL AFTER ID,
ADD INDEX IF NOT EXISTS idx_tenant_id (tenant_id);
" --allow-root 2>/dev/null || true

# For MySQL versions that don't support IF NOT EXISTS in ALTER TABLE
# Check if column exists first
COLUMN_EXISTS=$(wp db query "
SELECT COUNT(*) as count
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
AND TABLE_NAME = 'wp_posts'
AND COLUMN_NAME = 'tenant_id';
" --allow-root --skip-column-names)

if [ "$COLUMN_EXISTS" -eq "0" ]; then
  wp db query "ALTER TABLE wp_posts ADD COLUMN tenant_id BIGINT(20) UNSIGNED DEFAULT NULL AFTER ID;" --allow-root
  wp db query "ALTER TABLE wp_posts ADD INDEX idx_tenant_id (tenant_id);" --allow-root
  echo "✓ Added tenant_id column to wp_posts"
else
  echo "✓ tenant_id column already exists in wp_posts"
fi

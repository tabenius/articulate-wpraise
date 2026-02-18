#!/bin/bash
# Migration: Add activity feeds

set -e

echo "Running migration: Add activity feeds"

# Create activities table
wp db query "
CREATE TABLE IF NOT EXISTS wp_activities (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id BIGINT UNSIGNED NOT NULL,
  organization_id BIGINT UNSIGNED NULL,
  activity_type VARCHAR(50) NOT NULL,
  metadata JSON NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_user_id (user_id),
  INDEX idx_organization_id (organization_id),
  INDEX idx_activity_type (activity_type),
  INDEX idx_created_at (created_at),
  FOREIGN KEY (user_id) REFERENCES wp_users_auth(id) ON DELETE CASCADE,
  FOREIGN KEY (organization_id) REFERENCES wp_organizations(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
" --allow-root

echo "✅ Migration completed: Activity feeds table created"

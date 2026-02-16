#!/bin/bash
# Migration 001: Example - Add user preferences table
# This migration demonstrates how to create custom tables for user preferences
#
# ROLLBACK: To rollback, run:
#   wp db query "DROP TABLE IF EXISTS wp_user_preferences;" --allow-root

set -e

echo "Creating wp_user_preferences table..."

# Create custom user preferences table
wp db query "
CREATE TABLE IF NOT EXISTS wp_user_preferences (
  id BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id BIGINT(20) UNSIGNED NOT NULL,
  preference_key VARCHAR(255) NOT NULL,
  preference_value LONGTEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY user_id (user_id),
  KEY preference_key (preference_key),
  UNIQUE KEY user_preference (user_id, preference_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
" --allow-root

echo "✓ User preferences table created"

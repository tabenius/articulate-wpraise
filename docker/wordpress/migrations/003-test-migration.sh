#!/bin/bash
# Migration 003: test-migration
# Description: Create test table for migration system verification
#
# ROLLBACK: To rollback, run:
#   wp db query "DROP TABLE IF EXISTS wp_migration_test;" --allow-root

set -e

echo "Running migration 003: test-migration..."

wp db query "
CREATE TABLE IF NOT EXISTS wp_migration_test (
  id BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  test_data VARCHAR(255) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
" --allow-root

echo "✓ Migration 003 completed"

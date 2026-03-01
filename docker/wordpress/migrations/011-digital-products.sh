#!/bin/bash
set -e

echo "[Migration 011] Adding digital products and access grants..."

wp db query "
CREATE TABLE IF NOT EXISTS articulate_products (
  id BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  organization_id BIGINT(20) UNSIGNED NULL,
  created_by BIGINT(20) UNSIGNED NOT NULL,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  price_cents INT UNSIGNED NOT NULL DEFAULT 0 COMMENT 'Price in smallest currency unit',
  currency VARCHAR(3) NOT NULL DEFAULT 'usd',
  stripe_price_id VARCHAR(255) NULL COMMENT 'Stripe Price object ID',
  stripe_product_id VARCHAR(255) NULL COMMENT 'Stripe Product object ID',
  content_ids JSON NULL COMMENT 'WP post/page IDs this grants access to',
  file_path VARCHAR(500) NULL COMMENT 'Path or URL to downloadable file',
  file_name VARCHAR(255) NULL COMMENT 'Original filename for download',
  access_duration_days INT NULL COMMENT 'NULL = permanent access',
  download_limit INT NULL COMMENT 'NULL = unlimited downloads',
  is_active TINYINT(1) DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_org (organization_id),
  KEY idx_created_by (created_by),
  KEY idx_active (is_active),
  KEY idx_stripe_product (stripe_product_id),
  CONSTRAINT fk_product_creator FOREIGN KEY (created_by) REFERENCES articulate_users_auth(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
" --allow-root

echo "✓ Created articulate_products table"

wp db query "
CREATE TABLE IF NOT EXISTS articulate_access_grants (
  id BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  product_id BIGINT(20) UNSIGNED NOT NULL,
  customer_email VARCHAR(255) NOT NULL,
  customer_name VARCHAR(255) NULL,
  user_id BIGINT(20) UNSIGNED NULL COMMENT 'Linked Articulate user if registered',
  access_token VARCHAR(64) NOT NULL COMMENT 'Unique token for content access',
  stripe_session_id VARCHAR(255) NULL,
  stripe_payment_intent_id VARCHAR(255) NULL,
  amount_paid INT UNSIGNED NOT NULL DEFAULT 0,
  currency VARCHAR(3) NOT NULL DEFAULT 'usd',
  download_count INT UNSIGNED NOT NULL DEFAULT 0,
  download_limit INT UNSIGNED NULL COMMENT 'NULL = unlimited, inherited from product',
  expires_at DATETIME NULL COMMENT 'NULL = permanent',
  revoked_at DATETIME NULL COMMENT 'Admin can revoke access',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  last_accessed_at DATETIME NULL,
  PRIMARY KEY (id),
  UNIQUE KEY unique_token (access_token),
  KEY idx_product (product_id),
  KEY idx_email (customer_email),
  KEY idx_user (user_id),
  KEY idx_stripe_session (stripe_session_id),
  KEY idx_active (revoked_at, expires_at),
  CONSTRAINT fk_grant_product FOREIGN KEY (product_id) REFERENCES articulate_products(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
" --allow-root

echo "✓ Created articulate_access_grants table"

wp db query "
CREATE TABLE IF NOT EXISTS articulate_stripe_events (
  id BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  event_id VARCHAR(255) NOT NULL COMMENT 'Stripe event ID for idempotency',
  event_type VARCHAR(100) NOT NULL,
  payload JSON NULL,
  processed TINYINT(1) DEFAULT 0,
  processed_at DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY unique_event (event_id),
  KEY idx_type (event_type),
  KEY idx_processed (processed)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
" --allow-root

echo "✓ Created articulate_stripe_events table"

echo "[Migration 011] ✅ Digital products migration completed successfully"

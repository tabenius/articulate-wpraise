#!/bin/bash
set -e

echo "[Migration 004] Creating user management and WordPress connections tables..."

# Create users table
wp db query "
CREATE TABLE IF NOT EXISTS wp_users_auth (
  id BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  email VARCHAR(255) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  name VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
" --allow-root

echo "Created wp_users_auth table"

# Create WordPress connections table
wp db query "
CREATE TABLE IF NOT EXISTS wp_wordpress_connections (
  id BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id BIGINT(20) UNSIGNED NOT NULL,
  name VARCHAR(255) NOT NULL,
  wp_url VARCHAR(500) NOT NULL,
  wp_graphql_endpoint VARCHAR(500) NOT NULL,
  wp_user VARCHAR(255) NOT NULL,
  wp_app_password TEXT NOT NULL,
  is_active TINYINT(1) DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY user_name (user_id, name),
  KEY idx_user_id (user_id),
  KEY idx_active (user_id, is_active),
  CONSTRAINT fk_user_id FOREIGN KEY (user_id) REFERENCES wp_users_auth(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
" --allow-root

echo "Created wp_wordpress_connections table"

# Create sessions table
wp db query "
CREATE TABLE IF NOT EXISTS wp_sessions (
  id VARCHAR(255) NOT NULL,
  user_id BIGINT(20) UNSIGNED NOT NULL,
  expires_at DATETIME NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_user_id (user_id),
  KEY idx_expires (expires_at),
  CONSTRAINT fk_session_user_id FOREIGN KEY (user_id) REFERENCES wp_users_auth(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
" --allow-root

echo "Created wp_sessions table"

echo "[Migration 004] User management tables created successfully"

#!/bin/bash
# Migration 003: Add audit log table for security event tracking

set -e

echo "Running migration 003: Add audit log table..."

# Create audit_log table
wp db query "
CREATE TABLE IF NOT EXISTS wp_audit_log (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    event_type VARCHAR(50) NOT NULL,
    event_category ENUM('auth', 'access', 'data', 'security', 'system') NOT NULL DEFAULT 'security',
    severity ENUM('info', 'warning', 'error', 'critical') NOT NULL DEFAULT 'info',
    user_id BIGINT UNSIGNED NULL,
    ip_address VARCHAR(45) NULL,
    user_agent TEXT NULL,
    resource_type VARCHAR(50) NULL,
    resource_id VARCHAR(255) NULL,
    action VARCHAR(50) NULL,
    status VARCHAR(20) NULL,
    message TEXT NULL,
    metadata JSON NULL,
    INDEX idx_created_at (created_at),
    INDEX idx_event_type (event_type),
    INDEX idx_user_id (user_id),
    INDEX idx_ip_address (ip_address),
    INDEX idx_severity (severity),
    FOREIGN KEY (user_id) REFERENCES wp_users_auth(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
" --allow-root

echo "✅ Migration 003 completed: Audit log table created"

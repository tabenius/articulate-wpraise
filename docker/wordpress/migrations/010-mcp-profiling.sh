#!/bin/bash
# Migration 010: MCP Function Profiling Tables

mysql -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" <<'EOSQL'

-- MCP function profiling table
CREATE TABLE IF NOT EXISTS wp_mcp_profiling (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id BIGINT UNSIGNED NOT NULL,
  organization_id BIGINT UNSIGNED NULL,
  connection_id BIGINT UNSIGNED NULL,
  function_name VARCHAR(255) NOT NULL,
  execution_time_ms DECIMAL(10, 2) NOT NULL,
  cpu_time_ms DECIMAL(10, 2) NOT NULL,
  io_time_ms DECIMAL(10, 2) NOT NULL,
  memory_mb DECIMAL(10, 2) NULL,
  args_size_bytes INT UNSIGNED NULL,
  result_size_bytes INT UNSIGNED NULL,
  success BOOLEAN NOT NULL DEFAULT TRUE,
  error_message TEXT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

  INDEX idx_user_id (user_id),
  INDEX idx_organization_id (organization_id),
  INDEX idx_function_name (function_name),
  INDEX idx_created_at (created_at),
  INDEX idx_execution_time (execution_time_ms),
  INDEX idx_user_function (user_id, function_name),
  INDEX idx_org_function (organization_id, function_name),

  FOREIGN KEY (user_id) REFERENCES wp_users(id) ON DELETE CASCADE,
  FOREIGN KEY (organization_id) REFERENCES wp_organizations(id) ON DELETE SET NULL,
  FOREIGN KEY (connection_id) REFERENCES wp_wordpress_connections(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Aggregated profiling statistics (for faster queries)
CREATE TABLE IF NOT EXISTS wp_mcp_profiling_stats (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  organization_id BIGINT UNSIGNED NULL,
  function_name VARCHAR(255) NOT NULL,
  date DATE NOT NULL,
  call_count INT UNSIGNED NOT NULL DEFAULT 0,
  total_time_ms DECIMAL(12, 2) NOT NULL DEFAULT 0,
  avg_time_ms DECIMAL(10, 2) NOT NULL DEFAULT 0,
  min_time_ms DECIMAL(10, 2) NOT NULL,
  max_time_ms DECIMAL(10, 2) NOT NULL,
  p95_time_ms DECIMAL(10, 2) NULL,
  p99_time_ms DECIMAL(10, 2) NULL,
  success_count INT UNSIGNED NOT NULL DEFAULT 0,
  error_count INT UNSIGNED NOT NULL DEFAULT 0,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  UNIQUE KEY unique_org_function_date (organization_id, function_name, date),
  INDEX idx_function_name (function_name),
  INDEX idx_date (date),
  INDEX idx_avg_time (avg_time_ms),

  FOREIGN KEY (organization_id) REFERENCES wp_organizations(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

EOSQL

echo "Migration 010 (MCP Profiling) completed successfully"

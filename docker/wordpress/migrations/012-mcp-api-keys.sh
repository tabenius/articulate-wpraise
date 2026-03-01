#!/bin/bash
set -e

echo "[Migration 012] Adding MCP API key to WordPress connections..."

# Check if column already exists
COLUMN_EXISTS=$(wp db query "SELECT COUNT(*) AS cnt FROM information_schema.COLUMNS WHERE TABLE_NAME='articulate_wordpress_connections' AND COLUMN_NAME='mcp_api_key'" --allow-root 2>/dev/null | tail -1)

if [ "$COLUMN_EXISTS" = "0" ]; then
    wp db query "
    ALTER TABLE articulate_wordpress_connections
    ADD COLUMN mcp_api_key VARCHAR(64) DEFAULT NULL AFTER is_active,
    ADD UNIQUE KEY idx_mcp_api_key (mcp_api_key);
    " --allow-root
    echo "Added mcp_api_key column"
else
    echo "mcp_api_key column already exists, skipping"
fi

# Generate keys for existing connections that don't have one
wp db query "
UPDATE articulate_wordpress_connections
SET mcp_api_key = CONCAT(
    SUBSTRING(SHA2(CONCAT(id, RAND(), NOW(), UUID()), 256), 1, 32),
    SUBSTRING(SHA2(CONCAT(RAND(), id, UUID()), 256), 1, 11)
)
WHERE mcp_api_key IS NULL;
" --allow-root

echo "Generated MCP API keys for existing connections"

echo "[Migration 012] MCP API key column added successfully"

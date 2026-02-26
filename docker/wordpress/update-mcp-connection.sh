#!/bin/bash
# =============================================================================
# Update MCP Connection with Application Password
# =============================================================================
# This script updates the WordPress connection in the MCP database with the
# application password created during setup.
# =============================================================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
  echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Application Password exists for admin user
APP_PASSWORD=$(wp user application-password list 1 --field=password --format=csv --path=/var/www/html --allow-root 2>/dev/null | tail -1)

if [ -z "$APP_PASSWORD" ]; then
  log_info "No application password found, creating one..."
  APP_PASSWORD=$(wp user application-password create 1 "WP-AI MCP Server" --porcelain --path=/var/www/html --allow-root 2>/dev/null)

  if [ -z "$APP_PASSWORD" ]; then
    log_error "Failed to create application password"
    exit 1
  fi

  log_info "Created new application password: $APP_PASSWORD"
else
  log_info "Using existing application password"
fi

# Wait for MCP server to be ready
log_info "Waiting for MCP server to be ready..."
max_retries=30
retries=0

while ! curl -sf http://mcp-server:8000/health > /dev/null 2>&1; do
  retries=$((retries + 1))
  if [ $retries -ge $max_retries ]; then
    log_error "MCP server failed to start after $max_retries attempts"
    log_error "Continuing without updating connection - you'll need to do this manually"
    exit 0  # Don't fail the whole setup
  fi
  sleep 2
done

log_info "MCP server is ready"

# Create a Python script to update the connection
cat > /tmp/update_mcp_connection.py <<'PYTHON_SCRIPT'
#!/usr/bin/env python3
import os
import sys
import pymysql
from cryptography.fernet import Fernet

def main():
    # Get environment variables
    app_password = sys.argv[1] if len(sys.argv) > 1 else None
    if not app_password:
        print("ERROR: Application password not provided")
        sys.exit(1)

    encryption_key = os.getenv("ENCRYPTION_KEY")
    if not encryption_key:
        print("ERROR: ENCRYPTION_KEY not set")
        sys.exit(1)

    # Encrypt the password
    cipher = Fernet(encryption_key.encode())
    encrypted_password = cipher.encrypt(app_password.encode()).decode()

    # Connect to database
    try:
        conn = pymysql.connect(
            host=os.getenv("MYSQL_HOST", "mariadb"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.getenv("MYSQL_USER", "wpuser"),
            password=os.getenv("MYSQL_PASSWORD", "wppassword"),
            database=os.getenv("MYSQL_DATABASE", "wordpress"),
        )

        with conn.cursor() as cursor:
            # Check if connection exists
            cursor.execute(
                "SELECT id FROM wp_wordpress_connections WHERE name = 'Local WordPress' LIMIT 1"
            )
            result = cursor.fetchone()

            if result:
                # Update existing connection
                cursor.execute(
                    "UPDATE wp_wordpress_connections SET wp_app_password = %s WHERE id = %s",
                    (encrypted_password, result[0])
                )
                print(f"✓ Updated existing connection (ID: {result[0]})")
            else:
                print("⚠ No 'Local WordPress' connection found - skipping update")
                print("  You'll need to create the connection manually in the web UI")

            conn.commit()

        conn.close()
        print("✓ MCP connection update complete")

    except Exception as e:
        print(f"ERROR: Failed to update connection: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
PYTHON_SCRIPT

# Copy script to MCP container and execute it
docker cp /tmp/update_mcp_connection.py articulate-mcp:/tmp/
docker exec articulate-mcp python3 /tmp/update_mcp_connection.py "$APP_PASSWORD"

log_info "Connection update complete!"
echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}  WordPress Connection Updated${NC}"
echo -e "${GREEN}=========================================${NC}"
echo -e "  Username: admin"
echo -e "  Password: $APP_PASSWORD"
echo -e "${GREEN}=========================================${NC}"
echo ""

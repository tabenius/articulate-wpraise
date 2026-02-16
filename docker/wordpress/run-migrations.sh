#!/bin/bash
set -e

# Migration runner for WordPress database schema evolution
# Tracks migration version in wp_options and runs new migrations sequentially

echo "Running database migrations..."

# Get current migration version from WordPress options table
# Default to 0 if option doesn't exist yet
CURRENT_VERSION=$(wp option get wp_ai_migration_version --allow-root 2>/dev/null || echo "0")
echo "Current migration version: $CURRENT_VERSION"

# Track if any migrations were applied
MIGRATIONS_APPLIED=0

# Find and run all migration scripts in order
if [ -d "/usr/local/migrations" ]; then
  for migration in /usr/local/migrations/*.sh; do
    # Skip if no migrations found
    [ -e "$migration" ] || continue

    # Extract migration number from filename (e.g., 001-description.sh -> 001)
    MIGRATION_NUMBER=$(basename "$migration" .sh | sed 's/-.*//')
    MIGRATION_NAME=$(basename "$migration")

    # Only run if this migration number is greater than current version
    if [ "$MIGRATION_NUMBER" -gt "$CURRENT_VERSION" ]; then
      echo "Applying migration $MIGRATION_NAME..."

      # Execute the migration script
      if bash "$migration"; then
        # Update the migration version in WordPress
        wp option update wp_ai_migration_version "$MIGRATION_NUMBER" --allow-root
        echo "✓ Migration $MIGRATION_NAME applied successfully"
        MIGRATIONS_APPLIED=$((MIGRATIONS_APPLIED + 1))
      else
        echo "✗ Migration $MIGRATION_NAME failed!"
        exit 1
      fi
    fi
  done
else
  echo "No migrations directory found at /usr/local/migrations"
fi

if [ $MIGRATIONS_APPLIED -eq 0 ]; then
  echo "No new migrations to apply"
else
  echo "Applied $MIGRATIONS_APPLIED migration(s)"
fi

echo "Migration check complete"

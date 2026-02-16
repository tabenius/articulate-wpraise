#!/bin/bash
set -e

# Migration generator script
# Usage: ./scripts/create-migration.sh <migration-name>
# Example: ./scripts/create-migration.sh add-post-revisions

if [ -z "$1" ]; then
  echo "Usage: $0 <migration-name>"
  echo "Example: $0 add-post-revisions"
  exit 1
fi

MIGRATION_NAME=$1
MIGRATIONS_DIR="docker/wordpress/migrations"

# Create migrations directory if it doesn't exist
mkdir -p "$MIGRATIONS_DIR"

# Find the highest existing migration number
HIGHEST=0
for file in "$MIGRATIONS_DIR"/*.sh; do
  # Skip if no migrations found (glob didn't match)
  [ -e "$file" ] || continue

  NUM=$(basename "$file" .sh | sed 's/-.*//')
  if [ "$NUM" -gt "$HIGHEST" ] 2>/dev/null; then
    HIGHEST=$NUM
  fi
done

# Increment to get new migration number
NEW_NUMBER=$(printf "%03d" $((HIGHEST + 1)))
FILENAME="${NEW_NUMBER}-${MIGRATION_NAME}.sh"
FILEPATH="$MIGRATIONS_DIR/$FILENAME"

# Create migration file from template
cat > "$FILEPATH" << 'EOF'
#!/bin/bash
# Migration ${NEW_NUMBER}: ${MIGRATION_NAME}
# Description: [Add description here]
#
# ROLLBACK: To rollback, run:
#   [Add rollback SQL commands here]

set -e

echo "Running migration ${NEW_NUMBER}: ${MIGRATION_NAME}..."

# Add your migration SQL commands here using wp db query
# Example:
# wp db query "
# CREATE TABLE IF NOT EXISTS wp_example (
#   id BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
#   name VARCHAR(255) NOT NULL,
#   PRIMARY KEY (id)
# ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
# " --allow-root

echo "✓ Migration ${NEW_NUMBER} completed"
EOF

# Replace placeholders in the template
sed -i "s/\${NEW_NUMBER}/$NEW_NUMBER/g" "$FILEPATH"
sed -i "s/\${MIGRATION_NAME}/$MIGRATION_NAME/g" "$FILEPATH"

# Make it executable
chmod +x "$FILEPATH"

echo "Created migration: $FILEPATH"
echo ""
echo "Next steps:"
echo "1. Edit $FILEPATH to add your migration SQL"
echo "2. Add rollback commands in the comment header"
echo "3. Test the migration by rebuilding the WordPress container"
echo ""
echo "To test:"
echo "  docker compose build wordpress"
echo "  docker compose up -d wordpress"
echo "  docker compose logs wp-setup"

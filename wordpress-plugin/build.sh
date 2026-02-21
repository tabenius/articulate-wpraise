#!/bin/bash
set -e

echo "Building WP-AI Connector plugin..."

# Navigate to plugin directory
cd "$(dirname "$0")"

# Remove old ZIP if exists
rm -f wp-ai-connector.zip

# Create ZIP excluding development files
cd wp-ai-connector
zip -r ../wp-ai-connector.zip . \
  -x "*.git*" \
  -x "*.DS_Store" \
  -x "node_modules/*" \
  -x "*.md"

cd ..

echo "✓ Plugin ZIP created: wp-ai-connector.zip"

# Create web public downloads directory if it doesn't exist
DOWNLOADS_DIR="../web/public/downloads"
mkdir -p "$DOWNLOADS_DIR"

# Copy ZIP to web public directory
cp wp-ai-connector.zip "$DOWNLOADS_DIR/"

echo "✓ Plugin copied to $DOWNLOADS_DIR/wp-ai-connector.zip"
echo ""
echo "Plugin is now available at: /downloads/wp-ai-connector.zip"

#!/bin/bash
# Migration: Add profile visibility settings

set -e

echo "Running migration: Add profile visibility settings"

# Add visibility column to wp_users_auth table
wp db query "ALTER TABLE wp_users_auth ADD COLUMN IF NOT EXISTS visibility VARCHAR(20) NOT NULL DEFAULT 'public'" --allow-root

echo "✅ Migration completed: Profile visibility settings added"

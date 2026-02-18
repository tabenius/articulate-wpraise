#!/bin/bash
# Migration: Add organization visibility

set -e

echo "Running migration: Add organization visibility"

# Add visibility column to wp_organizations table
wp db query "ALTER TABLE wp_organizations ADD COLUMN IF NOT EXISTS visibility VARCHAR(20) NOT NULL DEFAULT 'public'" --allow-root

echo "✅ Migration completed: Organization visibility added"

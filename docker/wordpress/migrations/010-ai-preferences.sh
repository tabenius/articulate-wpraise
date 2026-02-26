#!/bin/bash
# Migration 010: AI Preferences System
# Creates tables for user AI preferences and organization AI settings

set -e

MYSQL_CMD="mysql -h${DB_HOST} -u${DB_USER} -p${DB_PASSWORD} ${DB_NAME}"

echo "Running migration 010: AI Preferences System"

$MYSQL_CMD <<'EOF'

-- User AI Preferences Table
CREATE TABLE IF NOT EXISTS wp_user_ai_preferences (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id BIGINT UNSIGNED NOT NULL,

  -- Writing Style
  tone VARCHAR(50) DEFAULT 'professional',
  audience VARCHAR(50) DEFAULT 'general',
  writing_level VARCHAR(50) DEFAULT 'moderate',
  content_length VARCHAR(50) DEFAULT 'medium',

  -- SEO Settings
  auto_generate_seo BOOLEAN DEFAULT false,
  seo_style VARCHAR(50) DEFAULT 'balanced',
  target_keyword_density DECIMAL(3,1) DEFAULT 1.5,

  -- Language
  primary_language VARCHAR(10) DEFAULT 'en',
  translation_languages JSON,

  -- Brand Voice
  brand_voice TEXT,
  company_values JSON,
  avoid_words JSON,
  preferred_terms JSON,

  -- Image AI
  auto_generate_alt_text BOOLEAN DEFAULT true,
  alt_text_style VARCHAR(50) DEFAULT 'descriptive',

  -- Assistance Settings
  suggestion_frequency VARCHAR(50) DEFAULT 'balanced',
  confirm_before_apply BOOLEAN DEFAULT true,
  dismissed_suggestions JSON,

  -- Model Selection
  default_model VARCHAR(50) DEFAULT 'sonnet',
  model_config JSON,

  -- Additional Settings
  use_emojis BOOLEAN DEFAULT false,
  include_sources BOOLEAN DEFAULT false,

  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  FOREIGN KEY (user_id) REFERENCES wp_users(id) ON DELETE CASCADE,
  UNIQUE KEY unique_user (user_id),
  INDEX idx_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Organization AI Settings Table
CREATE TABLE IF NOT EXISTS wp_org_ai_settings (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  organization_id BIGINT UNSIGNED NOT NULL,

  -- Override user preferences for consistency
  enforce_brand_voice BOOLEAN DEFAULT false,
  brand_voice TEXT,
  tone VARCHAR(50),
  writing_level VARCHAR(50),

  -- Usage Limits
  monthly_request_limit INT,
  cost_limit_usd DECIMAL(10,2),

  -- Shared Resources
  custom_prompts JSON,
  approved_styles JSON,

  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  FOREIGN KEY (organization_id) REFERENCES wp_organizations(id) ON DELETE CASCADE,
  UNIQUE KEY unique_org (organization_id),
  INDEX idx_org (organization_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- AI Usage Tracking Table
CREATE TABLE IF NOT EXISTS articulate_ai_usage (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id BIGINT UNSIGNED NOT NULL,
  organization_id BIGINT UNSIGNED,

  feature VARCHAR(100) NOT NULL,
  model VARCHAR(50) NOT NULL,

  input_tokens INT NOT NULL DEFAULT 0,
  output_tokens INT NOT NULL DEFAULT 0,
  cost_usd DECIMAL(10,6) DEFAULT 0,

  request_data JSON,
  response_data JSON,

  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

  FOREIGN KEY (user_id) REFERENCES wp_users(id) ON DELETE CASCADE,
  FOREIGN KEY (organization_id) REFERENCES wp_organizations(id) ON DELETE SET NULL,

  INDEX idx_user_date (user_id, created_at),
  INDEX idx_org_date (organization_id, created_at),
  INDEX idx_feature (feature),
  INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

EOF

echo "Migration 010 completed successfully"

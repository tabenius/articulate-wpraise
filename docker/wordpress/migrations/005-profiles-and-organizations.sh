#!/bin/bash
set -e

echo "[Migration 005] Adding profiles and organizations..."

# Add profile fields to wp_users_auth
wp db query "
ALTER TABLE wp_users_auth
  ADD COLUMN IF NOT EXISTS username VARCHAR(50) UNIQUE AFTER email,
  ADD COLUMN IF NOT EXISTS avatar VARCHAR(500) AFTER name,
  ADD COLUMN IF NOT EXISTS banner VARCHAR(500) AFTER avatar,
  ADD COLUMN IF NOT EXISTS bio TEXT AFTER banner;
" --allow-root

echo "Added profile fields to wp_users_auth"

# Create organizations table
wp db query "
CREATE TABLE IF NOT EXISTS wp_organizations (
  id BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(100) NOT NULL UNIQUE,
  owner_id BIGINT(20) UNSIGNED NOT NULL,
  avatar VARCHAR(500),
  banner VARCHAR(500),
  bio TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY slug (slug),
  KEY idx_owner (owner_id),
  CONSTRAINT fk_org_owner FOREIGN KEY (owner_id) REFERENCES wp_users_auth(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
" --allow-root

echo "Created wp_organizations table"

# Create organization members table (many-to-many)
wp db query "
CREATE TABLE IF NOT EXISTS wp_organization_members (
  id BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  organization_id BIGINT(20) UNSIGNED NOT NULL,
  user_id BIGINT(20) UNSIGNED NOT NULL,
  role ENUM('owner', 'admin', 'member', 'viewer') DEFAULT 'member',
  joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY unique_org_user (organization_id, user_id),
  KEY idx_org (organization_id),
  KEY idx_user (user_id),
  CONSTRAINT fk_orgmember_org FOREIGN KEY (organization_id) REFERENCES wp_organizations(id) ON DELETE CASCADE,
  CONSTRAINT fk_orgmember_user FOREIGN KEY (user_id) REFERENCES wp_users_auth(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
" --allow-root

echo "Created wp_organization_members table"

# Create organization invites table
wp db query "
CREATE TABLE IF NOT EXISTS wp_organization_invites (
  id BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  organization_id BIGINT(20) UNSIGNED NOT NULL,
  inviter_id BIGINT(20) UNSIGNED NOT NULL,
  invitee_email VARCHAR(255) NOT NULL,
  invitee_id BIGINT(20) UNSIGNED,
  role ENUM('admin', 'member', 'viewer') DEFAULT 'member',
  status ENUM('pending', 'accepted', 'rejected', 'expired') DEFAULT 'pending',
  token VARCHAR(255) UNIQUE NOT NULL,
  expires_at DATETIME NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  responded_at DATETIME,
  PRIMARY KEY (id),
  UNIQUE KEY unique_pending_invite (organization_id, invitee_email, status),
  KEY idx_org (organization_id),
  KEY idx_inviter (inviter_id),
  KEY idx_invitee_email (invitee_email),
  KEY idx_invitee_id (invitee_id),
  KEY idx_token (token),
  KEY idx_status (status),
  CONSTRAINT fk_invite_org FOREIGN KEY (organization_id) REFERENCES wp_organizations(id) ON DELETE CASCADE,
  CONSTRAINT fk_invite_inviter FOREIGN KEY (inviter_id) REFERENCES wp_users_auth(id) ON DELETE CASCADE,
  CONSTRAINT fk_invite_invitee FOREIGN KEY (invitee_id) REFERENCES wp_users_auth(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
" --allow-root

echo "Created wp_organization_invites table"

echo "[Migration 005] Profiles and organizations created successfully"

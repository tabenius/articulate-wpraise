-- Migration 005: Add WordPress user mapping to tenant_users
ALTER TABLE tenant_users
    ADD COLUMN wp_user_id INT DEFAULT NULL,
    ADD COLUMN wp_username VARCHAR(255) DEFAULT NULL,
    ADD COLUMN wp_role VARCHAR(50) DEFAULT NULL

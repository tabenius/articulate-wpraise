-- Add email verification and password reset support

ALTER TABLE wp_users_auth
    ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT FALSE AFTER name,
    ADD COLUMN email_verify_token VARCHAR(255) DEFAULT NULL AFTER email_verified,
    ADD COLUMN email_verify_expires DATETIME DEFAULT NULL AFTER email_verify_token;

-- Mark existing users as verified (they registered before verification was required)
UPDATE wp_users_auth SET email_verified = TRUE WHERE email_verified = FALSE;

CREATE TABLE IF NOT EXISTS wp_password_reset_tokens (
    id BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT(20) UNSIGNED NOT NULL,
    token VARCHAR(255) NOT NULL UNIQUE,
    expires_at DATETIME NOT NULL,
    used_at DATETIME DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_token (token),
    INDEX idx_user_id (user_id),
    INDEX idx_expires (expires_at),
    FOREIGN KEY (user_id) REFERENCES wp_users_auth(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- One-time login tokens for WP-Admin SSO
CREATE TABLE IF NOT EXISTS wp_login_tokens (
    id BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT(20) UNSIGNED NOT NULL,
    tenant_id VARCHAR(36) NOT NULL,
    token VARCHAR(255) NOT NULL UNIQUE,
    expires_at DATETIME NOT NULL,
    used_at DATETIME DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_token (token),
    INDEX idx_expires (expires_at),
    FOREIGN KEY (user_id) REFERENCES wp_users_auth(id) ON DELETE CASCADE,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Multi-Tenancy: Tenants Table
-- Each tenant represents an isolated WordPress instance for a user or organization

CREATE TABLE IF NOT EXISTS tenants (
    id VARCHAR(36) PRIMARY KEY,  -- UUID
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,  -- URL-safe identifier (e.g., 'acme-corp')

    -- Owner
    owner_user_id INT NOT NULL,

    -- WordPress Configuration
    wp_url VARCHAR(500) NOT NULL,  -- WordPress instance URL
    wp_graphql_endpoint VARCHAR(500) NOT NULL,
    wp_admin_user VARCHAR(100) NOT NULL,
    wp_admin_email VARCHAR(255),

    -- Database connection (if using separate DB per tenant)
    db_host VARCHAR(255),
    db_port INT DEFAULT 3306,
    db_name VARCHAR(100),
    db_user VARCHAR(100),
    db_password_encrypted TEXT,  -- Encrypted with ENCRYPTION_KEY

    -- Status
    status ENUM('active', 'suspended', 'deleted') DEFAULT 'active',

    -- Resource Limits (for multi-tenant quotas)
    max_posts INT DEFAULT 1000,
    max_storage_mb INT DEFAULT 5000,
    max_users INT DEFAULT 10,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL,

    INDEX idx_owner (owner_user_id),
    INDEX idx_status (status),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tenant Users Association (many-to-many)
-- Allows sharing a tenant WordPress with multiple users
CREATE TABLE IF NOT EXISTS tenant_users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    user_id INT NOT NULL,
    role ENUM('owner', 'admin', 'editor', 'viewer') DEFAULT 'viewer',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY unique_tenant_user (tenant_id, user_id),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    INDEX idx_user (user_id),
    INDEX idx_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tenant Usage Tracking
CREATE TABLE IF NOT EXISTS tenant_usage (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,

    -- Current usage
    post_count INT DEFAULT 0,
    storage_used_mb DECIMAL(10,2) DEFAULT 0,
    user_count INT DEFAULT 0,

    -- Last updated
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    INDEX idx_tenant (tenant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

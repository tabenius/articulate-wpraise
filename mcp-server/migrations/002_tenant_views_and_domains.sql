-- Tenant Views & Custom Domains
-- Evolves the tenant schema to support multiple frontend views (WordPress, Faust, Astro)
-- and custom domain routing per tenant.

-- Add new columns to tenants table
ALTER TABLE tenants
    ADD COLUMN domain VARCHAR(255) AFTER slug,
    ADD COLUMN default_view ENUM('wordpress','faust','astro') NOT NULL DEFAULT 'wordpress' AFTER domain,
    ADD COLUMN docker_project VARCHAR(100) AFTER default_view,
    ADD INDEX idx_name (name),
    ADD INDEX idx_domain (domain);

-- Expand status enum to include provisioning states
ALTER TABLE tenants
    MODIFY COLUMN status ENUM('provisioning','running','stopped','error','active','suspended','deleted') DEFAULT 'provisioning';

-- Tenant secrets (encrypted credentials stored separately from main tenant row)
CREATE TABLE IF NOT EXISTS tenant_secrets (
    tenant_id VARCHAR(36) PRIMARY KEY,
    db_password VARBINARY(512) NOT NULL,
    db_root_password VARBINARY(512) NOT NULL,
    wp_admin_password VARBINARY(512) NOT NULL,

    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tenant custom domains (maps external domains to a specific frontend view)
CREATE TABLE IF NOT EXISTS tenant_domains (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    external_domain VARCHAR(255) NOT NULL UNIQUE,
    target_view ENUM('wordpress','faust','astro') NOT NULL,
    verified BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    INDEX idx_tenant_id (tenant_id),
    INDEX idx_external_domain (external_domain)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

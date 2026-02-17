#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "======================================"
echo "    WP-AI Production Setup Script    "
echo "======================================"
echo ""

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker is not installed${NC}"
    echo "  Install from: https://docs.docker.com/get-docker/"
    exit 1
fi
echo -e "${GREEN}✓ Docker installed${NC}"

if ! command -v docker compose &> /dev/null; then
    echo -e "${RED}✗ Docker Compose is not installed${NC}"
    echo "  Install from: https://docs.docker.com/compose/install/"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose installed${NC}"

if ! command -v node &> /dev/null; then
    echo -e "${RED}✗ Node.js is not installed${NC}"
    echo "  Install from: https://nodejs.org/"
    exit 1
fi
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 20 ]; then
    echo -e "${RED}✗ Node.js version 20+ required (found: $(node -v))${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Node.js $(node -v) installed${NC}"

echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠ .env file not found. Creating from .env.example...${NC}"
    if [ ! -f .env.example ]; then
        echo -e "${RED}✗ .env.example not found${NC}"
        exit 1
    fi
    cp .env.example .env
    echo -e "${GREEN}✓ Created .env file${NC}"
else
    echo -e "${GREEN}✓ .env file exists${NC}"
fi

# Function to generate secure password
generate_password() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-32
}

# Function to generate Fernet key
generate_fernet_key() {
    python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || \
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
}

# Function to update .env value
update_env() {
    local key=$1
    local value=$2
    if grep -q "^${key}=" .env; then
        # Update existing value
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|^${key}=.*|${key}=${value}|" .env
        else
            sed -i "s|^${key}=.*|${key}=${value}|" .env
        fi
    else
        # Add new value
        echo "${key}=${value}" >> .env
    fi
}

# Validate and generate secrets
echo ""
echo "Validating environment variables..."

# Check and generate MYSQL_ROOT_PASSWORD
if ! grep -q "^MYSQL_ROOT_PASSWORD=" .env || grep -q "^MYSQL_ROOT_PASSWORD=your_secure_root_password_here" .env || grep -q "^MYSQL_ROOT_PASSWORD=$" .env; then
    MYSQL_ROOT_PASSWORD=$(generate_password)
    update_env "MYSQL_ROOT_PASSWORD" "$MYSQL_ROOT_PASSWORD"
    echo -e "${GREEN}✓ Generated MYSQL_ROOT_PASSWORD${NC}"
else
    echo -e "${GREEN}✓ MYSQL_ROOT_PASSWORD already set${NC}"
fi

# Check and generate MYSQL_PASSWORD
if ! grep -q "^MYSQL_PASSWORD=" .env || grep -q "^MYSQL_PASSWORD=your_secure_wp_password_here" .env || grep -q "^MYSQL_PASSWORD=$" .env; then
    MYSQL_PASSWORD=$(generate_password)
    update_env "MYSQL_PASSWORD" "$MYSQL_PASSWORD"
    echo -e "${GREEN}✓ Generated MYSQL_PASSWORD${NC}"
else
    echo -e "${GREEN}✓ MYSQL_PASSWORD already set${NC}"
fi

# Check and generate WP_ADMIN_PASS
if ! grep -q "^WP_ADMIN_PASS=" .env || grep -q "^WP_ADMIN_PASS=your_secure_admin_password_here" .env || grep -q "^WP_ADMIN_PASS=$" .env; then
    WP_ADMIN_PASS=$(generate_password)
    update_env "WP_ADMIN_PASS" "$WP_ADMIN_PASS"
    echo -e "${GREEN}✓ Generated WP_ADMIN_PASS${NC}"
else
    echo -e "${GREEN}✓ WP_ADMIN_PASS already set${NC}"
fi

# Check and generate ENCRYPTION_KEY
if ! grep -q "^ENCRYPTION_KEY=" .env || grep -q "^ENCRYPTION_KEY=your_fernet_encryption_key_here" .env || grep -q "^ENCRYPTION_KEY=$" .env; then
    if command -v python3 &> /dev/null || command -v python &> /dev/null; then
        ENCRYPTION_KEY=$(generate_fernet_key)
        update_env "ENCRYPTION_KEY" "$ENCRYPTION_KEY"
        echo -e "${GREEN}✓ Generated ENCRYPTION_KEY${NC}"
    else
        echo -e "${YELLOW}⚠ Python not found, cannot generate ENCRYPTION_KEY automatically${NC}"
        echo "  Generate manually with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
    fi
else
    echo -e "${GREEN}✓ ENCRYPTION_KEY already set${NC}"
fi

# Check required non-secret values
REQUIRED_VARS=("MYSQL_DATABASE" "MYSQL_USER" "WP_ADMIN_USER")
for var in "${REQUIRED_VARS[@]}"; do
    if ! grep -q "^${var}=" .env; then
        echo -e "${YELLOW}⚠ ${var} not set in .env${NC}"
    else
        echo -e "${GREEN}✓ ${var} is set${NC}"
    fi
done

echo ""
echo -e "${YELLOW}⚠ IMPORTANT: You still need to configure:${NC}"
echo "  - WP_APP_PASSWORD (generate in WordPress admin after setup)"
echo "  - WP_DOMAIN (for production deployment)"
echo ""

# Ask if user wants to start Docker services
read -p "Start Docker services now? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Starting Docker services..."
    docker compose up -d

    echo ""
    echo "Waiting for setup to complete..."
    docker compose logs -f wp-setup &
    LOGS_PID=$!

    # Wait for wp-setup container to exit
    while [ "$(docker inspect -f '{{.State.Status}}' wp-ai-setup 2>/dev/null)" != "exited" ]; do
        sleep 2
    done

    kill $LOGS_PID 2>/dev/null || true

    echo ""
    echo -e "${GREEN}✓ Docker services started${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Wait for WordPress to be ready (check: docker compose logs wordpress)"
    echo "  2. Access WordPress admin: http://localhost:8080/wp-admin"
    echo "     Username: $(grep "^WP_ADMIN_USER=" .env | cut -d'=' -f2)"
    echo "     Password: $(grep "^WP_ADMIN_PASS=" .env | cut -d'=' -f2)"
    echo "  3. Generate application password:"
    echo "     - Go to Users → Profile → Application Passwords"
    echo "     - Create new password named 'MCP Server'"
    echo "     - Copy the password and add to .env as WP_APP_PASSWORD"
    echo "  4. Setup frontend:"
    echo "     cd web"
    echo "     cp .env.local.example .env.local"
    echo "     npm install"
    echo "     npm run dev"
fi

echo ""
echo -e "${GREEN}Setup complete!${NC}"

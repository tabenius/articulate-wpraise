#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root (parent of scripts directory)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Change to project root
cd "$PROJECT_ROOT"

echo "======================================"
echo "   WP-AI Domain Configuration Tool   "
echo "======================================"
echo ""
echo "Project root: $PROJECT_ROOT"
echo ""

# Get domain from user
read -p "Enter your domain name (e.g., example.com): " DOMAIN

if [ -z "$DOMAIN" ]; then
    echo -e "${RED}✗ Domain cannot be empty${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}Domain: $DOMAIN${NC}"
echo ""

# Check DNS resolution
echo "Checking DNS resolution..."
if host "$DOMAIN" > /dev/null 2>&1; then
    IP=$(host "$DOMAIN" | grep "has address" | awk '{print $4}' | head -1)
    echo -e "${GREEN}✓ Domain resolves to: $IP${NC}"

    # Check if it points to this server
    SERVER_IP=$(curl -s ifconfig.me || curl -s icanhazip.com)
    if [ "$IP" == "$SERVER_IP" ]; then
        echo -e "${GREEN}✓ Domain points to this server ($SERVER_IP)${NC}"
    else
        echo -e "${YELLOW}⚠ Domain points to $IP but server IP is $SERVER_IP${NC}"
        echo "  Update your DNS A record to point to $SERVER_IP"
    fi
else
    echo -e "${YELLOW}⚠ Domain does not resolve yet${NC}"
    SERVER_IP=$(curl -s ifconfig.me || curl -s icanhazip.com)
    echo "  Add DNS A record: $DOMAIN → $SERVER_IP"
fi

echo ""

# Update .env file
echo "Updating .env configuration..."

if [ ! -f .env ]; then
    echo -e "${RED}✗ .env file not found. Run ./scripts/setup.sh first${NC}"
    exit 1
fi

# Function to update .env value
update_env() {
    local key=$1
    local value=$2
    if grep -q "^${key}=" .env; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|^${key}=.*|${key}=${value}|" .env
        else
            sed -i "s|^${key}=.*|${key}=${value}|" .env
        fi
    else
        echo "${key}=${value}" >> .env
    fi
}

update_env "DOMAIN" "$DOMAIN"
update_env "WP_DOMAIN" "https://$DOMAIN"
echo -e "${GREEN}✓ Updated .env with domain configuration${NC}"

echo ""

# WordPress URL configuration
echo "Updating WordPress site URL..."
if docker ps | grep -q wp-ai-wordpress; then
    docker exec wp-ai-wordpress wp option update home "https://$DOMAIN" --allow-root 2>/dev/null || \
        echo -e "${YELLOW}⚠ Could not update WordPress home URL (wp-cli may not be ready)${NC}"

    docker exec wp-ai-wordpress wp option update siteurl "https://$DOMAIN" --allow-root 2>/dev/null || \
        echo -e "${YELLOW}⚠ Could not update WordPress site URL (wp-cli may not be ready)${NC}"

    echo -e "${GREEN}✓ WordPress URLs updated${NC}"
else
    echo -e "${YELLOW}⚠ WordPress container not running. URLs will be set on next startup${NC}"
fi

echo ""

# SSL Certificate suggestions
echo "======================================"
echo "           SSL Certificate           "
echo "======================================"
echo ""
echo "Choose your SSL certificate method:"
echo ""
echo "1. Let's Encrypt (Recommended - Free, Automatic)"
echo "2. Caddy (Easiest - Automatic HTTPS)"
echo "3. Traefik (Docker-native - Automatic)"
echo "4. Manual certificate"
echo ""
read -p "Enter choice (1-4): " SSL_CHOICE

case $SSL_CHOICE in
    1)
        echo ""
        echo "Setting up Let's Encrypt with Certbot..."
        if ! command -v certbot &> /dev/null; then
            echo -e "${YELLOW}⚠ Certbot not installed${NC}"
            echo "Install with: sudo apt install certbot"
            echo "Then run: sudo certbot certonly --standalone -d $DOMAIN"
        else
            echo "Run: sudo certbot certonly --standalone -d $DOMAIN"
            echo ""
            echo "After obtaining certificate, configure your reverse proxy:"
            echo "  - Nginx: /etc/nginx/sites-available/wp-ai"
            echo "  - HAProxy: /etc/haproxy/haproxy.cfg"
        fi
        ;;
    2)
        echo ""
        echo "Caddy handles SSL automatically!"
        echo ""
        echo "1. Install Caddy: https://caddyserver.com/docs/install"
        echo "2. Edit docker/caddy/Caddyfile and replace 'yourdomain.com' with '$DOMAIN'"
        echo "3. Run: sudo caddy run --config docker/caddy/Caddyfile"
        echo ""
        echo "That's it! Caddy will automatically obtain and renew SSL certificates."
        ;;
    3)
        echo ""
        echo "Traefik handles SSL automatically!"
        echo ""
        echo "1. Set LETSENCRYPT_EMAIL in .env"
        echo "2. Run: docker compose -f docker-compose.production.yml -f docker/traefik/docker-compose.traefik.yml up -d"
        echo ""
        echo "Traefik will automatically obtain and renew SSL certificates."
        ;;
    4)
        echo ""
        echo "Manual certificate setup:"
        echo "1. Obtain SSL certificate from your provider"
        echo "2. Place certificate files on server"
        echo "3. Configure your reverse proxy to use the certificates"
        ;;
    *)
        echo -e "${YELLOW}⚠ Invalid choice${NC}"
        ;;
esac

echo ""
echo "======================================"
echo "            Next Steps               "
echo "======================================"
echo ""
echo "1. Ensure DNS points to this server"
echo "2. Set up SSL certificate (see above)"
echo "3. Configure reverse proxy:"
echo "   - Nginx: See docker/nginx/nginx.conf"
echo "   - HAProxy: See README.md"
echo "   - Traefik: See docker/traefik/docker-compose.traefik.yml"
echo "   - Caddy: See docker/caddy/Caddyfile"
echo "4. Restart services with production config:"
echo "   docker compose -f docker-compose.production.yml up -d"
echo "5. Test: https://$DOMAIN"
echo ""
echo -e "${GREEN}Configuration complete!${NC}"

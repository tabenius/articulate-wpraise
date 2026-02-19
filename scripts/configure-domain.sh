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

# Ask about reverse proxy setup
echo "Which reverse proxy are you using?"
echo ""
echo "1. HAProxy (SSL termination + Caddy for HTTP routing)"
echo "2. Direct Caddy (Caddy handles SSL and routing)"
echo "3. Nginx, Traefik, or other"
echo ""
read -p "Enter choice (1-3) [1]: " PROXY_CHOICE
PROXY_CHOICE=${PROXY_CHOICE:-1}

echo ""

if [ "$PROXY_CHOICE" == "1" ]; then
    USE_HAPROXY=true
    echo -e "${BLUE}HAProxy mode selected${NC}"
    echo ""
    echo "This setup uses:"
    echo "  - HAProxy: SSL termination, domain routing (port 443)"
    echo "  - Caddy: HTTP reverse proxy (port 4555)"
    echo "  - Split domains: App domain + WordPress domain"
    echo ""

    # Get app domain
    read -p "Enter your app domain (e.g., app.example.com): " APP_DOMAIN
    if [ -z "$APP_DOMAIN" ]; then
        echo -e "${RED}✗ App domain cannot be empty${NC}"
        exit 1
    fi

    # Get WordPress domain
    read -p "Enter your WordPress domain (e.g., my.example.com): " WP_DOMAIN_NAME
    if [ -z "$WP_DOMAIN_NAME" ]; then
        echo -e "${RED}✗ WordPress domain cannot be empty${NC}"
        exit 1
    fi

    DOMAIN=$APP_DOMAIN

    echo ""
    echo -e "${BLUE}App Domain: $APP_DOMAIN${NC}"
    echo -e "${BLUE}WordPress Domain: $WP_DOMAIN_NAME${NC}"
    echo ""
else
    USE_HAPROXY=false
    # Get domain from user
    read -p "Enter your domain name (e.g., example.com): " DOMAIN

    if [ -z "$DOMAIN" ]; then
        echo -e "${RED}✗ Domain cannot be empty${NC}"
        exit 1
    fi

    echo ""
    echo -e "${BLUE}Domain: $DOMAIN${NC}"
    echo ""
fi

# Check DNS resolution
echo "Checking DNS resolution..."
SERVER_IP=$(curl -s ifconfig.me || curl -s icanhazip.com)

check_domain_dns() {
    local domain=$1
    if host "$domain" > /dev/null 2>&1; then
        IP=$(host "$domain" | grep "has address" | awk '{print $4}' | head -1)
        echo -e "${GREEN}✓ $domain resolves to: $IP${NC}"

        if [ "$IP" == "$SERVER_IP" ]; then
            echo -e "${GREEN}✓ Points to this server ($SERVER_IP)${NC}"
        else
            echo -e "${YELLOW}⚠ Points to $IP but server IP is $SERVER_IP${NC}"
            echo "  Update DNS A record to point to $SERVER_IP"
        fi
    else
        echo -e "${YELLOW}⚠ $domain does not resolve yet${NC}"
        echo "  Add DNS A record: $domain → $SERVER_IP"
    fi
}

if [ "$USE_HAPROXY" = true ]; then
    echo "Checking app domain..."
    check_domain_dns "$APP_DOMAIN"
    echo ""
    echo "Checking WordPress domain..."
    check_domain_dns "$WP_DOMAIN_NAME"
else
    check_domain_dns "$DOMAIN"
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

if [ "$USE_HAPROXY" = true ]; then
    update_env "DOMAIN" "$APP_DOMAIN"
    update_env "WP_DOMAIN" "https://$WP_DOMAIN_NAME"
    update_env "APP_DOMAIN" "$APP_DOMAIN"
    update_env "WP_SUBDOMAIN" "$WP_DOMAIN_NAME"
else
    update_env "DOMAIN" "$DOMAIN"
    update_env "WP_DOMAIN" "https://$DOMAIN"
fi
echo -e "${GREEN}✓ Updated .env with domain configuration${NC}"

echo ""

# WordPress URL configuration
echo "Updating WordPress site URL..."
if docker ps | grep -q wp-ai-wordpress; then
    WP_URL="https://$DOMAIN"
    if [ "$USE_HAPROXY" = true ]; then
        WP_URL="https://$WP_DOMAIN_NAME"
    fi

    docker exec wp-ai-wordpress wp option update home "$WP_URL" --allow-root 2>/dev/null || \
        echo -e "${YELLOW}⚠ Could not update WordPress home URL (wp-cli may not be ready)${NC}"

    docker exec wp-ai-wordpress wp option update siteurl "$WP_URL" --allow-root 2>/dev/null || \
        echo -e "${YELLOW}⚠ Could not update WordPress site URL (wp-cli may not be ready)${NC}"

    echo -e "${GREEN}✓ WordPress URLs updated to $WP_URL${NC}"
else
    echo -e "${YELLOW}⚠ WordPress container not running. URLs will be set on next startup${NC}"
fi

echo ""

# Update Caddyfile for HAProxy if needed
if [ "$USE_HAPROXY" = true ]; then
    echo "Updating Caddyfile for HAProxy configuration..."
    CADDYFILE="docker/caddy/Caddyfile"

    if [ -f "$CADDYFILE" ]; then
        # Backup original
        cp "$CADDYFILE" "$CADDYFILE.backup"

        # Update app domain
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|http://app\\.ragbaz\\.xyz|http://$APP_DOMAIN|g" "$CADDYFILE"
            sed -i '' "s|http://my\\.ragbaz\\.xyz|http://$WP_DOMAIN_NAME|g" "$CADDYFILE"
        else
            sed -i "s|http://app\\.ragbaz\\.xyz|http://$APP_DOMAIN|g" "$CADDYFILE"
            sed -i "s|http://my\\.ragbaz\\.xyz|http://$WP_DOMAIN_NAME|g" "$CADDYFILE"
        fi

        echo -e "${GREEN}✓ Updated Caddyfile with your domains${NC}"
        echo "  App domain: $APP_DOMAIN"
        echo "  WordPress domain: $WP_DOMAIN_NAME"
        echo "  Backup saved: $CADDYFILE.backup"
    else
        echo -e "${YELLOW}⚠ Caddyfile not found at $CADDYFILE${NC}"
    fi

    echo ""
fi

# SSL Certificate suggestions
echo "======================================"
echo "           SSL Certificate           "
echo "======================================"
echo ""

if [ "$USE_HAPROXY" = true ]; then
    echo -e "${BLUE}HAProxy SSL Configuration${NC}"
    echo ""
    echo "HAProxy will handle SSL termination. Choose your certificate source:"
    echo ""
    echo "1. Cloudflare Origin Certificate (Recommended for Cloudflare users)"
    echo "2. Let's Encrypt with Certbot"
    echo "3. Manual certificate"
    echo ""
    read -p "Enter choice (1-3) [1]: " SSL_CHOICE
    SSL_CHOICE=${SSL_CHOICE:-1}

    case $SSL_CHOICE in
        1)
            echo ""
            echo -e "${GREEN}Cloudflare Origin Certificate Setup${NC}"
            echo ""
            echo "1. Go to Cloudflare Dashboard → SSL/TLS → Origin Server"
            echo "2. Click 'Create Certificate'"
            echo "3. Select RSA (2048), add hostnames: *.$DOMAIN, $DOMAIN"
            echo "4. Save certificate and key to server:"
            echo ""
            echo "   sudo mkdir -p /etc/haproxy/certs"
            echo "   sudo nano /etc/haproxy/certs/${DOMAIN}.crt   # Paste certificate"
            echo "   sudo nano /etc/haproxy/certs/${DOMAIN}.key   # Paste private key"
            echo ""
            echo "5. Combine for HAProxy:"
            echo "   sudo cat /etc/haproxy/certs/${DOMAIN}.crt \\"
            echo "            /etc/haproxy/certs/${DOMAIN}.key > \\"
            echo "            /etc/haproxy/certs/${DOMAIN}.pem"
            echo "   sudo chmod 600 /etc/haproxy/certs/${DOMAIN}.pem"
            echo ""
            echo "See HAPROXY_CONFIG.md for complete HAProxy configuration."
            ;;
        2)
            echo ""
            echo -e "${GREEN}Let's Encrypt with Certbot${NC}"
            echo ""
            echo "1. Install certbot: sudo apt install certbot"
            echo "2. Get certificate:"
            echo "   sudo certbot certonly --standalone -d $APP_DOMAIN -d $WP_DOMAIN_NAME"
            echo ""
            echo "3. Combine for HAProxy:"
            echo "   sudo cat /etc/letsencrypt/live/$APP_DOMAIN/fullchain.pem \\"
            echo "            /etc/letsencrypt/live/$APP_DOMAIN/privkey.pem > \\"
            echo "            /etc/haproxy/certs/${DOMAIN}.pem"
            echo "   sudo chmod 600 /etc/haproxy/certs/${DOMAIN}.pem"
            echo ""
            echo "4. Auto-renewal: Add to crontab"
            echo "   0 0 * * * certbot renew --post-hook 'cat /etc/letsencrypt/live/$APP_DOMAIN/fullchain.pem /etc/letsencrypt/live/$APP_DOMAIN/privkey.pem > /etc/haproxy/certs/${DOMAIN}.pem && systemctl reload haproxy'"
            ;;
        3)
            echo ""
            echo -e "${GREEN}Manual Certificate${NC}"
            echo ""
            echo "1. Obtain SSL certificate from your provider"
            echo "2. Combine certificate and key:"
            echo "   cat cert.pem key.pem > /etc/haproxy/certs/${DOMAIN}.pem"
            echo "   chmod 600 /etc/haproxy/certs/${DOMAIN}.pem"
            ;;
    esac

    echo ""
    echo -e "${YELLOW}Important HAProxy Configuration:${NC}"
    echo "  - Edit /etc/haproxy/haproxy.cfg (see HAPROXY_CONFIG.md)"
    echo "  - Update certificate path to /etc/haproxy/certs/${DOMAIN}.pem"
    echo "  - Update domain ACLs for $APP_DOMAIN and $WP_DOMAIN_NAME"
    echo "  - Test: sudo haproxy -c -f /etc/haproxy/haproxy.cfg"
    echo "  - Reload: sudo systemctl reload haproxy"

else
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
fi

echo ""
echo "======================================"
echo "            Next Steps               "
echo "======================================"
echo ""

if [ "$USE_HAPROXY" = true ]; then
    echo "HAProxy + Caddy Split-Domain Setup:"
    echo ""
    echo "1. DNS Configuration (Cloudflare recommended):"
    echo "   • A record: $APP_DOMAIN → $SERVER_IP (Proxied)"
    echo "   • A record: $WP_DOMAIN_NAME → $SERVER_IP (Proxied)"
    echo "   See CLOUDFLARE_SETUP.md for complete DNS and security settings"
    echo ""
    echo "2. SSL Certificate (see above):"
    echo "   • Obtain certificate for *.$DOMAIN or both subdomains"
    echo "   • Install to /etc/haproxy/certs/"
    echo ""
    echo "3. Configure HAProxy:"
    echo "   • See HAPROXY_CONFIG.md for complete configuration"
    echo "   • Update domain ACLs and backend routing"
    echo "   • Test: sudo haproxy -c -f /etc/haproxy/haproxy.cfg"
    echo "   • Reload: sudo systemctl reload haproxy"
    echo ""
    echo "4. Restart Docker services:"
    echo "   docker compose down"
    echo "   docker compose build caddy"
    echo "   docker compose up -d"
    echo ""
    echo "5. Test your setup:"
    echo "   • App: https://$APP_DOMAIN"
    echo "   • WordPress: https://$WP_DOMAIN_NAME"
    echo "   • WordPress Admin: https://$WP_DOMAIN_NAME/wp-admin"
    echo ""
    echo "Architecture:"
    echo "  Internet → Cloudflare → HAProxy:443 (SSL) → Caddy:4555 (HTTP)"
    echo "    ├─ $APP_DOMAIN → web:3000 (Next.js)"
    echo "    └─ $WP_DOMAIN_NAME → wordpress:80"
else
    echo "1. Ensure DNS points to this server"
    echo "2. Set up SSL certificate (see above)"
    echo "3. Configure reverse proxy:"
    echo "   - Nginx: See docker/nginx/nginx.conf"
    echo "   - HAProxy: See HAPROXY_CONFIG.md"
    echo "   - Traefik: See docker/traefik/docker-compose.traefik.yml"
    echo "   - Caddy: See docker/caddy/Caddyfile"
    echo "4. Restart services with production config:"
    echo "   docker compose -f docker-compose.production.yml up -d"
    echo "5. Test: https://$DOMAIN"
fi

echo ""
echo -e "${GREEN}Configuration complete!${NC}"
echo ""
echo "For help, see:"
echo "  • HAPROXY_CONFIG.md - Complete HAProxy setup"
echo "  • CLOUDFLARE_SETUP.md - DNS and security settings"
echo "  • docker/caddy/Caddyfile - Caddy configuration"

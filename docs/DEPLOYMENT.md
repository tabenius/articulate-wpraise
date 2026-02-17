# Production Deployment Guide

Complete guide for deploying WP-AI to production with SSL, reverse proxy, and security hardening.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Reverse Proxy Options](#reverse-proxy-options)
  - [Nginx](#option-1-nginx)
  - [HAProxy](#option-2-haproxy)
  - [Traefik](#option-3-traefik-easiest-for-docker)
  - [Caddy](#option-4-caddy-easiest-overall)
- [SSL/TLS Setup](#ssltls-setup)
- [Security Hardening](#security-hardening)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

## Overview

Production deployment architecture:

```
Internet (443/80)
    ↓
Reverse Proxy (Nginx/HAProxy/Traefik/Caddy)
    ├─> Next.js Frontend (internal:3000)
    ├─> WordPress (internal:80)
    └─> MCP Server (internal:8000)
         ├─> MariaDB (internal:3306)
         └─> Redis (internal:6379)
```

**Key differences from development:**
- ✅ All ports isolated except reverse proxy
- ✅ HTTPS with automatic SSL renewal
- ✅ Rate limiting at proxy level
- ✅ Security headers enabled
- ✅ Production environment variables

## Prerequisites

- **Server**: Linux VPS with 2GB+ RAM, 20GB+ storage
- **Domain**: Registered domain pointing to server IP
- **Software**: Docker, Docker Compose, Node.js 20+
- **Port 80/443**: Open in firewall for HTTPS

## Quick Start

### 1. Automated Setup

```bash
# Clone repository
git clone https://github.com/yourusername/wp-ai.git
cd wp-ai

# Run setup script (validates, generates secrets)
chmod +x scripts/*.sh
./scripts/setup.sh
```

The setup script will:
- ✅ Check prerequisites (Docker, Node.js)
- ✅ Create .env from template
- ✅ Generate secure passwords and encryption keys
- ✅ Start Docker services
- ✅ Display WordPress admin credentials

### 2. Configure Domain

```bash
# Run domain configuration helper
./scripts/configure-domain.sh
```

This will:
- Check DNS resolution
- Update .env with domain
- Update WordPress URLs
- Guide you through SSL setup

### 3. Choose Reverse Proxy

See [Reverse Proxy Options](#reverse-proxy-options) below.

### 4. Start Production Stack

```bash
# Stop development stack
docker compose down

# Start production stack (no exposed ports)
docker compose -f docker-compose.production.yml up -d

# Build and start Next.js
cd web
npm install
npm run build
npm start  # Or use PM2/systemd (see Process Management)
```

### 5. Verify

- WordPress admin: `https://yourdomain.com/wp-admin`
- Frontend: `https://yourdomain.com`
- GraphQL: `https://yourdomain.com/graphql`

## Reverse Proxy Options

### Option 1: Nginx

**Best for:** Traditional deployments, fine-grained control

**Pros:**
- Most widely used
- Excellent performance
- Extensive documentation
- Mature and stable

**Cons:**
- Manual SSL renewal setup
- More configuration required

**Setup:**

```bash
# Install Nginx
sudo apt update
sudo apt install nginx

# Copy configuration
sudo cp docker/nginx/nginx.conf /etc/nginx/sites-available/wp-ai

# Update domain
sudo sed -i 's/yourdomain.com/your-actual-domain.com/g' /etc/nginx/sites-available/wp-ai

# Enable site
sudo ln -s /etc/nginx/sites-available/wp-ai /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload
sudo systemctl reload nginx
```

**SSL Setup:**

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com

# Auto-renewal is configured automatically
sudo certbot renew --dry-run
```

---

### Option 2: HAProxy

**Best for:** High availability, advanced load balancing, existing HAProxy infrastructure

**Pros:**
- Excellent performance
- Advanced load balancing
- Built-in statistics
- Can integrate with existing HAProxy setups

**Cons:**
- Steeper learning curve
- Manual SSL renewal

**Setup:**

- **New HAProxy Setup**: See [README.md](../README.md#production-deployment-with-haproxy)
- **Existing HAProxy**: See [HAPROXY_WITH_CADDY.md](HAPROXY_WITH_CADDY.md) for integration guide
  - Option 1: HAProxy routes directly to WP-AI services
  - Option 2: HAProxy + Caddy internal proxy (recommended for cleaner setup)

```bash
# Install HAProxy
sudo apt install haproxy

# Configure (see README.md)
sudo nano /etc/haproxy/haproxy.cfg

# Get SSL certificate
sudo certbot certonly --standalone -d yourdomain.com

# Combine for HAProxy
sudo cat /etc/letsencrypt/live/yourdomain.com/fullchain.pem \
         /etc/letsencrypt/live/yourdomain.com/privkey.pem \
         > /etc/haproxy/certs/yourdomain.pem
sudo chmod 600 /etc/haproxy/certs/yourdomain.pem

# Reload
sudo systemctl reload haproxy
```

---

### Option 3: Traefik (Easiest for Docker)

**Best for:** Docker-first deployments, automatic SSL

**Pros:**
- ✨ Docker-native (labels-based config)
- ✨ Automatic SSL with Let's Encrypt
- ✨ Automatic renewal
- Web dashboard

**Cons:**
- Requires all services in Docker

**Setup:**

```bash
# Add to .env
echo "LETSENCRYPT_EMAIL=your@email.com" >> .env
echo "DOMAIN=yourdomain.com" >> .env

# Generate dashboard password
sudo apt install apache2-utils
htpasswd -nb admin yourpassword

# Add to .env (escape dollar signs)
echo "TRAEFIK_AUTH=admin:$$apr1$$xyz$$hash" >> .env

# Start with Traefik
docker compose -f docker-compose.production.yml -f docker/traefik/docker-compose.traefik.yml up -d
```

**That's it!** Traefik automatically:
- Obtains SSL certificates
- Renews certificates before expiry
- Routes traffic based on labels
- Enables HTTPS redirect

**Dashboard:** `https://traefik.yourdomain.com` (configure subdomain DNS)

---

### Option 4: Caddy (Easiest Overall)

**Best for:** Simple deployments, zero-config SSL

**Pros:**
- ✨ **Easiest option** - automatic HTTPS out of the box
- ✨ Automatic SSL with Let's Encrypt
- ✨ Automatic renewal
- Simple configuration
- Modern HTTP/3 support

**Cons:**
- Less mature than Nginx
- Fewer community resources

**Setup:**

```bash
# Install Caddy
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy

# Update Caddyfile
sed -i 's/yourdomain.com/your-actual-domain.com/g' docker/caddy/Caddyfile

# Run Caddy
sudo caddy run --config docker/caddy/Caddyfile

# Or as systemd service
sudo cp docker/caddy/Caddyfile /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

**That's it!** Caddy automatically:
- Obtains SSL certificates on first request
- Renews certificates before expiry
- Redirects HTTP to HTTPS
- Sets security headers

**Recommended for beginners!**

## SSL/TLS Setup

### Let's Encrypt (Free, Automated)

**With Certbot (for Nginx/HAProxy):**

```bash
# Install
sudo apt install certbot

# Standalone mode (stop your web server first)
sudo systemctl stop nginx  # or haproxy
sudo certbot certonly --standalone -d yourdomain.com
sudo systemctl start nginx

# Or with Nginx plugin (automatic)
sudo certbot --nginx -d yourdomain.com

# Auto-renewal
sudo certbot renew --dry-run
```

**With Caddy/Traefik:**
- No manual steps needed!
- SSL is fully automatic

### Custom Certificate

If you have a commercial certificate:

1. Place files on server:
   - `fullchain.pem` - Certificate + chain
   - `privkey.pem` - Private key

2. Update reverse proxy config with paths

3. Reload reverse proxy

## Security Hardening

### 1. Firewall Configuration

```bash
# UFW (Ubuntu)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# Verify
sudo ufw status
```

### 2. Fail2ban for WordPress

Protect against brute force attacks:

```bash
# Install
sudo apt install fail2ban

# Create WordPress filter
sudo nano /etc/fail2ban/filter.d/wordpress.conf
```

```ini
[Definition]
failregex = ^<HOST> .* "POST /wp-login.php
ignoreregex =
```

```bash
# Create jail
sudo nano /etc/fail2ban/jail.d/wordpress.conf
```

```ini
[wordpress]
enabled = true
filter = wordpress
logpath = /var/log/nginx/wp-ai-access.log  # Adjust for your proxy
maxretry = 5
bantime = 3600
```

```bash
# Restart
sudo systemctl restart fail2ban
```

### 3. Rate Limiting

Already configured in all reverse proxy examples:
- API: 10 requests/second
- WordPress: 20 requests/second
- GraphQL: 10 requests/second with burst

### 4. Security Headers

All reverse proxy configs include:
- `Strict-Transport-Security` (HSTS)
- `X-Frame-Options`
- `X-Content-Type-Options`
- `X-XSS-Protection`
- `Referrer-Policy`

### 5. Database Security

```bash
# Secure MariaDB
docker exec -it wp-ai-db mysql -uroot -p

# Run security commands
DELETE FROM mysql.user WHERE User='';
DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');
DROP DATABASE IF EXISTS test;
DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';
FLUSH PRIVILEGES;
```

### 6. Regular Updates

```bash
# Update Docker images
docker compose pull
docker compose up -d

# Update WordPress
docker exec wp-ai-wordpress wp core update --allow-root
docker exec wp-ai-wordpress wp plugin update --all --allow-root

# Update Node.js dependencies
cd web
npm audit fix
npm update
```

## Process Management

### Option 1: PM2 (Recommended)

```bash
# Install PM2
npm install -g pm2

# Start Next.js
cd web
pm2 start npm --name "wp-ai" -- start

# Save configuration
pm2 save

# Auto-start on boot
pm2 startup
# Follow the instructions it prints

# Monitor
pm2 monit
pm2 logs wp-ai
```

### Option 2: Systemd

Create `/etc/systemd/system/wp-ai-web.service`:

```ini
[Unit]
Description=WP-AI Next.js Frontend
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/wp-ai/web
ExecStart=/usr/bin/npm start
Restart=on-failure
RestartSec=10
Environment=NODE_ENV=production

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable wp-ai-web
sudo systemctl start wp-ai-web

# Check status
sudo systemctl status wp-ai-web

# View logs
sudo journalctl -u wp-ai-web -f
```

## Monitoring

### HAProxy Stats

Access at `http://yourserver:8404/stats` (if enabled)

### Nginx Logs

```bash
tail -f /var/log/nginx/wp-ai-access.log
tail -f /var/log/nginx/wp-ai-error.log
```

### Docker Container Logs

```bash
# All containers
docker compose logs -f

# Specific service
docker compose logs -f wordpress
docker compose logs -f mcp-server
```

### PM2 Monitoring

```bash
pm2 monit
pm2 logs wp-ai
```

## Troubleshooting

### SSL Certificate Issues

```bash
# Check certificate
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com

# Force renewal
sudo certbot renew --force-renewal

# Check Caddy logs
sudo journalctl -u caddy -f
```

### WordPress "Too Many Redirects"

```bash
# Fix WordPress URLs
docker exec wp-ai-wordpress wp option update home "https://yourdomain.com" --allow-root
docker exec wp-ai-wordpress wp option update siteurl "https://yourdomain.com" --allow-root
```

### 502 Bad Gateway

```bash
# Check if services are running
docker compose ps

# Check Next.js
pm2 status

# Check logs
docker compose logs wordpress
docker compose logs mcp-server
```

### Database Connection Failed

```bash
# Check MariaDB
docker compose exec mariadb mysql -uroot -p

# Check credentials in .env
grep MYSQL_ .env

# Restart services
docker compose restart
```

### Port Already in Use

```bash
# Find process using port 80/443
sudo lsof -i :80
sudo lsof -i :443

# Stop conflicting service
sudo systemctl stop apache2  # or nginx, haproxy, etc.
```

## Deployment Checklist

- [ ] Domain DNS configured (A record → server IP)
- [ ] Firewall configured (ports 80, 443, 22 only)
- [ ] .env file configured with strong passwords
- [ ] ENCRYPTION_KEY generated
- [ ] WP_APP_PASSWORD generated in WordPress admin
- [ ] Production docker-compose started
- [ ] Reverse proxy configured
- [ ] SSL certificate obtained
- [ ] HTTPS working (test at https://yourdomain.com)
- [ ] WordPress URLs updated
- [ ] Fail2ban configured
- [ ] PM2 or systemd configured for Next.js
- [ ] Auto-renewal tested (`certbot renew --dry-run`)
- [ ] Backups configured (database, uploads)
- [ ] Monitoring set up

## Backup Strategy

### Database Backup

```bash
# Manual backup
docker exec wp-ai-db mysqldump -uroot -p${MYSQL_ROOT_PASSWORD} wordpress > backup-$(date +%Y%m%d).sql

# Automated with cron
echo "0 2 * * * docker exec wp-ai-db mysqldump -uroot -pPASSWORD wordpress > /backups/wp-$(date +\%Y\%m\%d).sql" | crontab -
```

### WordPress Files Backup

```bash
# Backup uploads
docker cp wp-ai-wordpress:/var/www/html/wp-content/uploads ./backups/uploads-$(date +%Y%m%d)

# Or use volume backup
docker run --rm -v wp-ai_wp_data:/data -v $(pwd)/backups:/backup ubuntu tar czf /backup/wp-data-$(date +%Y%m%d).tar.gz -C /data .
```

## Support

- **Documentation**: See [README.md](../README.md)
- **Security**: See [SECURITY.md](../SECURITY.md)
- **Issues**: GitHub Issues

---

**Recommended Stack for Beginners:**
- **Reverse Proxy**: Caddy (automatic HTTPS, zero config)
- **Process Manager**: PM2 (easy monitoring)
- **Server**: Ubuntu 22.04 LTS on DigitalOcean/Linode/Hetzner

**Recommended Stack for Production:**
- **Reverse Proxy**: Nginx or Traefik
- **Process Manager**: Systemd
- **Monitoring**: Add Prometheus + Grafana (see task #28)
- **Server**: Ubuntu 22.04 LTS with 4GB+ RAM

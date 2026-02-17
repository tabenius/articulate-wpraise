# Production Deployment - Quick Reference

One-page cheat sheet for deploying WP-AI to production.

## 🚀 Fastest Setup (5 minutes)

### Prerequisites
- Ubuntu 22.04 server
- Domain pointing to server IP
- Ports 80, 443 open

### Commands

```bash
# 1. Clone and setup
git clone https://github.com/yourusername/wp-ai.git
cd wp-ai
./scripts/setup.sh

# 2. Configure domain
./scripts/configure-domain.sh

# 3. Install Caddy (easiest reverse proxy)
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install caddy

# 4. Update Caddyfile domain
sed -i 's/yourdomain.com/YOUR_ACTUAL_DOMAIN/g' docker/caddy/Caddyfile
sudo cp docker/caddy/Caddyfile /etc/caddy/Caddyfile

# 5. Start production stack
docker compose -f docker-compose.production.yml up -d

# 6. Start Next.js
cd web && npm install && npm run build
npm install -g pm2
pm2 start npm --name wp-ai -- start
pm2 save && pm2 startup

# 7. Start Caddy
sudo systemctl restart caddy

# Done! Access at https://YOUR_DOMAIN
```

## 🔧 Alternative Setups

### With Nginx

```bash
# After step 2 above:
sudo apt install nginx certbot python3-certbot-nginx
sudo cp docker/nginx/nginx.conf /etc/nginx/sites-available/wp-ai
sudo sed -i 's/yourdomain.com/YOUR_DOMAIN/g' /etc/nginx/sites-available/wp-ai
sudo ln -s /etc/nginx/sites-available/wp-ai /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d YOUR_DOMAIN
```

### With Traefik (Docker-native)

```bash
# Add to .env:
echo "LETSENCRYPT_EMAIL=your@email.com" >> .env
echo "DOMAIN=YOUR_DOMAIN" >> .env

# Start with Traefik:
docker compose -f docker-compose.production.yml \
               -f docker/traefik/docker-compose.traefik.yml up -d
```

## 📋 Pre-Flight Checklist

- [ ] DNS A record: `YOUR_DOMAIN` → `SERVER_IP`
- [ ] Firewall: Ports 80, 443, 22 open
- [ ] .env configured (run `./scripts/setup.sh`)
- [ ] Domain configured (run `./scripts/configure-domain.sh`)

## 🔐 Generate WordPress App Password

After deployment:

1. Visit `https://YOUR_DOMAIN/wp-admin`
2. Go to Users → Profile → Application Passwords
3. Name: "MCP Server"
4. Click "Add New Application Password"
5. Copy the password
6. Add to `.env`: `WP_APP_PASSWORD="xxxx xxxx xxxx xxxx xxxx xxxx"`
7. Restart MCP: `docker compose -f docker-compose.production.yml restart mcp-server`

## 🔍 Verify Deployment

```bash
# Check SSL
curl -I https://YOUR_DOMAIN

# Check services
docker compose ps
pm2 status

# Check logs
docker compose logs -f
pm2 logs wp-ai

# Test endpoints
curl https://YOUR_DOMAIN/                    # Next.js
curl https://YOUR_DOMAIN/wp-admin/           # WordPress
curl https://YOUR_DOMAIN/graphql             # GraphQL
```

## 🛠️ Common Issues

### 502 Bad Gateway
```bash
# Check if Next.js is running
pm2 status
pm2 restart wp-ai

# Check Docker services
docker compose ps
docker compose restart
```

### SSL Certificate Errors
```bash
# Caddy: Check logs
sudo journalctl -u caddy -f

# Nginx: Force renewal
sudo certbot renew --force-renewal
```

### WordPress Redirect Loop
```bash
# Fix URLs
docker exec wp-ai-wordpress wp option update home "https://YOUR_DOMAIN" --allow-root
docker exec wp-ai-wordpress wp option update siteurl "https://YOUR_DOMAIN" --allow-root
```

## 📊 Monitoring Commands

```bash
# HAProxy stats
http://SERVER_IP:8404/stats

# Nginx logs
tail -f /var/log/nginx/wp-ai-access.log

# Docker logs
docker compose logs -f wordpress
docker compose logs -f mcp-server

# PM2 monitoring
pm2 monit
pm2 logs wp-ai
```

## 🔄 Update Deployment

```bash
# Pull latest code
git pull

# Update Docker images
docker compose pull
docker compose -f docker-compose.production.yml up -d

# Update Next.js
cd web
npm install
npm run build
pm2 restart wp-ai

# Update WordPress
docker exec wp-ai-wordpress wp core update --allow-root
docker exec wp-ai-wordpress wp plugin update --all --allow-root
```

## 🛡️ Security Hardening

```bash
# Firewall
sudo ufw allow 22,80,443/tcp
sudo ufw enable

# Fail2ban
sudo apt install fail2ban
sudo systemctl enable fail2ban

# Auto-updates
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

## 📦 Backup

```bash
# Database
docker exec wp-ai-db mysqldump -uroot -p${MYSQL_ROOT_PASSWORD} wordpress > backup.sql

# Uploads
docker cp wp-ai-wordpress:/var/www/html/wp-content/uploads ./uploads-backup

# .env (contains secrets!)
cp .env .env.backup
```

## 🆘 Emergency Rollback

```bash
# Stop services
docker compose -f docker-compose.production.yml down
pm2 stop wp-ai

# Restore database
docker compose -f docker-compose.production.yml up -d mariadb
cat backup.sql | docker exec -i wp-ai-db mysql -uroot -p${MYSQL_ROOT_PASSWORD} wordpress

# Restart
docker compose -f docker-compose.production.yml up -d
pm2 restart wp-ai
```

---

**Need more details?** See [DEPLOYMENT.md](DEPLOYMENT.md) for complete guide.

**Security concerns?** See [../SECURITY.md](../SECURITY.md) for security documentation.

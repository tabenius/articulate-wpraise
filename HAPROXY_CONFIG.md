# HAProxy Configuration for app.ragbaz.cc and my.ragbaz.cc

Add this configuration to your HAProxy setup. HAProxy will handle SSL termination and forward HTTP traffic to Caddy.

## HAProxy Configuration

**Requirements:**
- HAProxy 2.0+ (for http-check syntax)
- For HAProxy 1.8 or older, see "Alternative Health Check Syntax" below

```haproxy
global
    log /dev/log local0
    log /dev/log local1 notice
    chroot /var/lib/haproxy
    stats socket /run/haproxy/admin.sock mode 660 level admin
    stats timeout 30s
    user haproxy
    group haproxy
    daemon

    # SSL Configuration
    ssl-default-bind-ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384
    ssl-default-bind-ciphersuites TLS_AES_128_GCM_SHA256:TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256
    ssl-default-bind-options ssl-min-ver TLSv1.2 no-tls-tickets

    # Performance tuning
    maxconn 4096
    tune.ssl.default-dh-param 2048

defaults
    log     global
    mode    http
    option  httplog
    option  dontlognull
    option  forwardfor
    option  http-server-close
    timeout connect 5000
    timeout client  50000
    timeout server  50000
    errorfile 400 /etc/haproxy/errors/400.http
    errorfile 403 /etc/haproxy/errors/403.http
    errorfile 408 /etc/haproxy/errors/408.http
    errorfile 500 /etc/haproxy/errors/500.http
    errorfile 502 /etc/haproxy/errors/502.http
    errorfile 503 /etc/haproxy/errors/503.http
    errorfile 504 /etc/haproxy/errors/504.http

# Frontend for HTTP traffic (redirect to HTTPS)
frontend http_frontend
    bind *:80
    mode http
    
    # Redirect all HTTP to HTTPS
    redirect scheme https code 301 if !{ ssl_fc }

# Frontend for HTTPS traffic
frontend https_frontend
    bind *:443 ssl crt /etc/haproxy/certs/ragbaz.cc.pem alpn h2,http/1.1
    mode http
    
    # Security headers (added by HAProxy)
    http-response set-header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
    http-response set-header X-Frame-Options "SAMEORIGIN"
    http-response set-header X-Content-Type-Options "nosniff"
    http-response set-header X-XSS-Protection "1; mode=block"
    http-response set-header Referrer-Policy "strict-origin-when-cross-origin"
    http-response del-header Server
    
    # Add X-Forwarded-* headers for backend
    http-request set-header X-Forwarded-Proto https
    http-request set-header X-Forwarded-Port 443
    http-request add-header X-Real-IP %[src]
    
    # ACL for domain matching
    acl is_app_domain hdr(host) -i app.ragbaz.cc
    acl is_my_domain hdr(host) -i my.ragbaz.cc
    acl is_www_app hdr(host) -i www.app.ragbaz.cc
    acl is_www_my hdr(host) -i www.my.ragbaz.cc
    
    # WWW redirects
    redirect prefix https://app.ragbaz.cc code 301 if is_www_app
    redirect prefix https://my.ragbaz.cc code 301 if is_www_my
    
    # Route to backends based on domain
    use_backend app_backend if is_app_domain
    use_backend wp_backend if is_my_domain
    
    # Default backend (app)
    default_backend app_backend

# Backend for app.ragbaz.cc (Next.js + APIs via Caddy)
backend app_backend
    mode http
    balance roundrobin

    # Health check (HAProxy 2.x+ syntax)
    option httpchk
    http-check send meth GET uri /health ver HTTP/1.1 hdr Host app.ragbaz.cc
    http-check expect status 200

    # Caddy server (running in Docker)
    server caddy1 127.0.0.1:4555 check inter 5000 rise 2 fall 3

    # Connection settings
    http-reuse safe
    timeout server 30s

# Backend for my.ragbaz.cc (WordPress via Caddy)
backend wp_backend
    mode http
    balance roundrobin

    # Health check (HAProxy 2.x+ syntax)
    option httpchk
    http-check send meth GET uri /wp-json/ ver HTTP/1.1 hdr Host my.ragbaz.cc
    http-check expect status 200

    # Caddy server (running in Docker)
    server caddy1 127.0.0.1:4555 check inter 5000 rise 2 fall 3

    # Connection settings
    http-reuse safe
    timeout server 60s

    # Longer timeout for WordPress admin
    timeout client 60s

# Statistics page (optional - secure this!)
listen stats
    bind *:8404
    mode http
    stats enable
    stats uri /stats
    stats refresh 30s
    stats admin if TRUE
    # Add basic auth:
    # stats auth admin:your_secure_password_here
```

## Alternative Health Check Syntax

### For HAProxy 1.8 or Older

If you're using HAProxy 1.8 or older and get errors about the `http-check` syntax, use this simpler format:

```haproxy
# Backend for app.ragbaz.cc
backend app_backend
    mode http
    balance roundrobin

    # Simple health check (no Host header)
    option httpchk GET /health

    server caddy1 127.0.0.1:4555 check inter 5000 rise 2 fall 3
    http-reuse safe
    timeout server 30s

# Backend for my.ragbaz.cc
backend wp_backend
    mode http
    balance roundrobin

    # Simple health check (no Host header)
    option httpchk GET /wp-json/

    server caddy1 127.0.0.1:4555 check inter 5000 rise 2 fall 3
    http-reuse safe
    timeout server 60s
    timeout client 60s
```

**Note:** This simpler syntax doesn't send the Host header, but Caddy can route based on the incoming request path. If you need Host header support, upgrade to HAProxy 2.0+.

### Check Your HAProxy Version

```bash
haproxy -v
```

If you see version 1.8 or older, consider upgrading:

```bash
# Ubuntu/Debian - Add HAProxy PPA for latest version
sudo add-apt-repository ppa:vbernat/haproxy-2.8
sudo apt update
sudo apt install haproxy
```

## SSL Certificate Setup

### Option 1: Cloudflare Origin Certificate (Recommended)

Since you're using Cloudflare, get an Origin Certificate:

1. Go to Cloudflare Dashboard → SSL/TLS → Origin Server
2. Click "Create Certificate"
3. Select:
   - Private key type: RSA (2048)
   - Hostnames: `*.ragbaz.cc`, `ragbaz.cc`
   - Validity: 15 years
4. Click "Create"
5. Save the certificate and private key:

```bash
# On your server
sudo mkdir -p /etc/haproxy/certs
sudo nano /etc/haproxy/certs/ragbaz.cc.crt   # Paste certificate
sudo nano /etc/haproxy/certs/ragbaz.cc.key   # Paste private key

# Combine cert and key for HAProxy
sudo cat /etc/haproxy/certs/ragbaz.cc.crt \
         /etc/haproxy/certs/ragbaz.cc.key \
         > /etc/haproxy/certs/ragbaz.cc.pem

# Set permissions
sudo chmod 600 /etc/haproxy/certs/ragbaz.cc.pem
sudo chown haproxy:haproxy /etc/haproxy/certs/ragbaz.cc.pem
```

### Option 2: Let's Encrypt with Certbot

```bash
# Install certbot
sudo apt install certbot

# Get certificate (use DNS challenge for wildcard)
sudo certbot certonly --standalone -d app.ragbaz.cc -d my.ragbaz.cc

# Combine for HAProxy
sudo cat /etc/letsencrypt/live/app.ragbaz.cc/fullchain.pem \
         /etc/letsencrypt/live/app.ragbaz.cc/privkey.pem \
         > /etc/haproxy/certs/ragbaz.cc.pem

# Set permissions
sudo chmod 600 /etc/haproxy/certs/ragbaz.cc.pem
sudo chown haproxy:haproxy /etc/haproxy/certs/ragbaz.cc.pem

# Auto-renewal (add to crontab)
0 0 * * * certbot renew --post-hook "cat /etc/letsencrypt/live/app.ragbaz.cc/fullchain.pem /etc/letsencrypt/live/app.ragbaz.cc/privkey.pem > /etc/haproxy/certs/ragbaz.cc.pem && systemctl reload haproxy"
```

## Testing HAProxy Configuration

```bash
# Test configuration syntax
sudo haproxy -c -f /etc/haproxy/haproxy.cfg

# Reload HAProxy (zero downtime)
sudo systemctl reload haproxy

# Check status
sudo systemctl status haproxy

# View logs
sudo journalctl -u haproxy -f
```

## Architecture Overview

```
Internet
   ↓
Cloudflare (DDoS protection, CDN)
   ↓
Your Server IP (via DNS)
   ↓
HAProxy (Port 443) - SSL termination, routing
   ↓
Caddy (Port 4555) - HTTP routing to services
   ↓
┌─────────────────┬──────────────────┐
↓                 ↓                  ↓
Next.js (3000)    WordPress (80)     MCP (8000)
app.ragbaz.cc    my.ragbaz.cc      (internal)
```

## Ports Summary

- **80** (HTTP) → HAProxy → Redirects to HTTPS
- **443** (HTTPS) → HAProxy → SSL termination
- **4555** (HTTP) → Caddy → Internal routing
- **8404** (HTTP) → HAProxy Stats (optional, secure this!)

## Firewall Rules

```bash
# Allow only necessary ports
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 22/tcp    # SSH (if remote)

# Block everything else
sudo ufw enable
```

## WordPress URL Configuration

Update WordPress to recognize the new domain in `.env`:

```bash
WP_DOMAIN=https://my.ragbaz.cc
```

And update `docker-compose.production.yml`:

```yaml
wordpress:
  environment:
    WORDPRESS_CONFIG_EXTRA: |
      define('WP_HOME', 'https://my.ragbaz.cc');
      define('WP_SITEURL', 'https://my.ragbaz.cc');
```

Then restart WordPress:

```bash
docker compose restart wordpress
```

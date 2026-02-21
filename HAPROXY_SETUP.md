# HAProxy Setup for ragbaz.xyz

This guide helps you configure HAProxy for Articulate production deployment.

## Quick Setup

### 1. Apply HAProxy Configuration

The `haproxy.cfg.patch` file contains the configuration to add to your HAProxy.

**Option A: Manual Addition (Recommended)**

Simply append the content to your existing `/etc/haproxy/haproxy.cfg`:

```bash
# Backup your current config
sudo cp /etc/haproxy/haproxy.cfg /etc/haproxy/haproxy.cfg.backup

# Add Articulate configuration (edit the file and paste the content)
sudo nano /etc/haproxy/haproxy.cfg
```

Paste the content from `haproxy.cfg.patch` at the end of the file.

**Option B: Using cat (Quick)**

```bash
# Backup
sudo cp /etc/haproxy/haproxy.cfg /etc/haproxy/haproxy.cfg.backup

# Append (skip the diff header lines)
tail -n +3 haproxy.cfg.patch | sudo tee -a /etc/haproxy/haproxy.cfg
```

### 2. Set Up SSL Certificate

**Using Let's Encrypt (Recommended):**

```bash
# Stop HAProxy temporarily
sudo systemctl stop haproxy

# Get certificate
sudo certbot certonly --standalone -d ragbaz.xyz

# Create HAProxy certificate directory
sudo mkdir -p /etc/haproxy/certs

# Combine cert and key for HAProxy
sudo cat /etc/letsencrypt/live/ragbaz.xyz/fullchain.pem \
         /etc/letsencrypt/live/ragbaz.xyz/privkey.pem \
         | sudo tee /etc/haproxy/certs/ragbaz.xyz.pem

# Secure the certificate
sudo chmod 600 /etc/haproxy/certs/ragbaz.xyz.pem
sudo chown haproxy:haproxy /etc/haproxy/certs/ragbaz.xyz.pem

# Restart HAProxy
sudo systemctl start haproxy
```

**Auto-renewal setup:**

```bash
# Create renewal hook
sudo tee /etc/letsencrypt/renewal-hooks/post/haproxy-reload.sh << 'EOF'
#!/bin/bash
cat /etc/letsencrypt/live/ragbaz.xyz/fullchain.pem \
    /etc/letsencrypt/live/ragbaz.xyz/privkey.pem \
    > /etc/haproxy/certs/ragbaz.xyz.pem
chmod 600 /etc/haproxy/certs/ragbaz.xyz.pem
chown haproxy:haproxy /etc/haproxy/certs/ragbaz.xyz.pem
systemctl reload haproxy
EOF

# Make it executable
sudo chmod +x /etc/letsencrypt/renewal-hooks/post/haproxy-reload.sh
```

**Using existing certificate:**

```bash
sudo mkdir -p /etc/haproxy/certs
sudo cat /path/to/your/cert.crt /path/to/your/key.key \
    | sudo tee /etc/haproxy/certs/ragbaz.xyz.pem
sudo chmod 600 /etc/haproxy/certs/ragbaz.xyz.pem
```

### 3. Test and Apply

```bash
# Test HAProxy configuration
sudo haproxy -c -f /etc/haproxy/haproxy.cfg

# If test passes, reload HAProxy
sudo systemctl reload haproxy

# Check status
sudo systemctl status haproxy

# View logs
sudo tail -f /var/log/haproxy.log
```

### 4. Verify Deployment

Test the following URLs:

- **Frontend**: https://ragbaz.xyz
- **Documentation**: https://ragbaz.xyz/docs
- **WordPress Admin**: https://ragbaz.xyz/wp-admin
- **GraphQL**: https://ragbaz.xyz/graphql

## Troubleshooting

### Certificate Error

If you see SSL errors:
```bash
# Check certificate file exists
sudo ls -la /etc/haproxy/certs/ragbaz.xyz.pem

# Verify certificate is valid
sudo openssl x509 -in /etc/haproxy/certs/ragbaz.xyz.pem -text -noout
```

### 503 Service Unavailable

If backends are down:
```bash
# Check if Articulate containers are running
docker ps --filter "name=wp-ai"

# Check HAProxy can reach backends
curl http://localhost:4500/api/auth/me
curl http://localhost:8080
curl http://localhost:8091
```

### Port 80 Already in Use

If you get "address already in use" error:
```bash
# Check what's using port 80
sudo lsof -i :80

# The wpai_http frontend might conflict with existing frontend
# Modify the patch to add ACLs to your existing frontend instead
```

### Configuration Test Fails

```bash
# Check syntax
sudo haproxy -c -f /etc/haproxy/haproxy.cfg

# Common issues:
# - Missing certificate file
# - Duplicate backend names
# - ACL syntax errors
```

## Configuration Explained

### Frontends

- **wpai_https** (port 443): Handles HTTPS traffic for ragbaz.xyz
- **wpai_http** (port 80): Redirects HTTP to HTTPS

### Backends

- **wpai_frontend**: Next.js app on localhost:4500
- **wpai_wordpress**: WordPress on localhost:8080
- **wpai_docs**: Documentation on localhost:8091

### ACLs (Access Control Lists)

- `is_wpai`: Matches ragbaz.xyz domain
- `is_docs`: Matches /docs/* paths
- `is_graphql`: Matches /graphql path
- `is_wp_admin`: Matches WordPress admin paths
- `is_wp_content`: Matches WordPress content paths

### Health Checks

- Frontend: `GET /api/auth/me`
- WordPress: `GET /`
- Docs: Default TCP check

## Security Notes

1. **SSL Certificate**: Store in `/etc/haproxy/certs/` with 600 permissions
2. **Auto-renewal**: Set up Let's Encrypt renewal hook
3. **Headers**: Security headers are automatically added
4. **Forwarding**: Real client IP is preserved via X-Forwarded-For

## Alternative: Using Existing Frontend

If you already have a frontend handling port 443, you can add ACLs to it instead:

```haproxy
# In your existing frontend
frontend your_existing_frontend
    bind *:443 ssl crt /path/to/certs

    # Add Articulate ACLs
    acl is_wpai hdr(host) -i ragbaz.xyz
    acl is_docs path_beg /docs
    acl is_graphql path_beg /graphql

    # Add routing
    use_backend wpai_docs if is_wpai is_docs
    use_backend wpai_wordpress if is_wpai is_graphql
    use_backend wpai_frontend if is_wpai

    # ... your existing rules ...

# Then add the backends from haproxy.cfg.patch
```

## Need Help?

Check the logs:
```bash
sudo tail -f /var/log/haproxy.log
docker logs wp-ai-web
docker logs wp-ai-wordpress
docker logs wp-ai-mcp
```

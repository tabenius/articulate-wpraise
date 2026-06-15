# Cloudflare DNS Configuration

## DNS Records to Create

In your Cloudflare dashboard for `ragbaz.cc`, create the following DNS records:

### 1. Web Application
```
Type: A
Name: app
Content: YOUR_SERVER_IP
Proxy status: ✓ Proxied (orange cloud)
TTL: Auto
```

### 2. WordPress Backend
```
Type: A
Name: my
Content: YOUR_SERVER_IP
Proxy status: ✓ Proxied (orange cloud)
TTL: Auto
```

### 3. WWW Redirects (Optional)
```
Type: CNAME
Name: www.app
Content: app.ragbaz.cc
Proxy status: ✓ Proxied

Type: CNAME
Name: www.my
Content: my.ragbaz.cc
Proxy status: ✓ Proxied
```

## Cloudflare SSL/TLS Configuration

1. **SSL/TLS Mode**: Full (strict)
   - Navigate to: SSL/TLS → Overview
   - Select: "Full (strict)"
   - This ensures end-to-end encryption

2. **Always Use HTTPS**: On
   - Navigate to: SSL/TLS → Edge Certificates
   - Enable: "Always Use HTTPS"

3. **Minimum TLS Version**: TLS 1.2
   - Navigate to: SSL/TLS → Edge Certificates
   - Set: Minimum TLS Version to 1.2 or higher

4. **Automatic HTTPS Rewrites**: On
   - Navigate to: SSL/TLS → Edge Certificates
   - Enable: "Automatic HTTPS Rewrites"

5. **HTTP Strict Transport Security (HSTS)**: Enable
   - Navigate to: SSL/TLS → Edge Certificates
   - Enable HSTS with these settings:
     - Max Age: 12 months
     - Include subdomains: Yes
     - Preload: Yes (optional)

## Cloudflare Speed Optimizations

1. **Auto Minify**
   - Navigate to: Speed → Optimization
   - Enable: JavaScript, CSS, HTML

2. **Brotli**
   - Navigate to: Speed → Optimization
   - Enable: Brotli compression

3. **HTTP/2 & HTTP/3**
   - Navigate to: Network
   - Enable: HTTP/2, HTTP/3 (with QUIC)

4. **Caching**
   - Navigate to: Caching → Configuration
   - Caching Level: Standard
   - Browser Cache TTL: Respect Existing Headers

## Cloudflare Security Settings

1. **WAF (Web Application Firewall)**
   - Navigate to: Security → WAF
   - Enable: OWASP Core Ruleset
   - Set to: Medium sensitivity

2. **DDoS Protection**
   - Navigate to: Security → DDoS
   - Verify it's enabled (should be automatic)

3. **Bot Fight Mode** (Free tier)
   - Navigate to: Security → Bots
   - Enable: "Bot Fight Mode"

4. **Rate Limiting Rules** (Recommended)
   Create rules at: Security → WAF → Rate limiting rules

   **Rule 1: Protect wp-login.php**
   ```
   If incoming requests match:
   - URI Path equals "/wp-login.php"
   - Hostname equals "my.ragbaz.cc"
   
   Then:
   - Throttle requests when rate exceeds: 5 requests / 1 minute
   - Duration: 10 minutes
   - Action: Block
   ```

   **Rule 2: Protect REST API**
   ```
   If incoming requests match:
   - URI Path starts with "/wp-json/"
   - Hostname equals "my.ragbaz.cc"
   
   Then:
   - Throttle requests when rate exceeds: 100 requests / 1 minute
   - Duration: 1 minute
   - Action: Challenge
   ```

## Firewall Rules (Optional but Recommended)

Navigate to: Security → WAF → Firewall rules

**Rule 1: Block known bad user agents**
```
If: (http.user_agent contains "sqlmap") or 
    (http.user_agent contains "nikto") or
    (http.user_agent contains "masscan")
Then: Block
```

**Rule 2: Protect sensitive WordPress files**
```
If: (http.request.uri.path contains "wp-config.php") or
    (http.request.uri.path contains ".env") or
    (http.request.uri.path contains "debug.log")
Then: Block
```

## Page Rules (Optional - Requires paid plan)

Navigate to: Rules → Page Rules

**Rule 1: Cache WordPress static assets**
```
If URL matches: my.ragbaz.cc/wp-content/*
Then:
- Cache Level: Cache Everything
- Edge Cache TTL: 1 month
- Browser Cache TTL: 1 month
```

**Rule 2: Bypass cache for WordPress admin**
```
If URL matches: my.ragbaz.cc/wp-admin/*
Then:
- Cache Level: Bypass
```

## Testing Your Setup

After DNS propagation (can take up to 48 hours, usually 5-15 minutes):

1. **Test app.ragbaz.cc**
   ```bash
   curl -I https://app.ragbaz.cc
   # Should return 200 OK with Next.js content
   ```

2. **Test my.ragbaz.cc**
   ```bash
   curl -I https://my.ragbaz.cc
   # Should return 200 OK with WordPress content
   ```

3. **Test HTTPS redirect**
   ```bash
   curl -I http://app.ragbaz.cc
   # Should redirect to https://app.ragbaz.cc
   ```

4. **Verify SSL**
   ```bash
   openssl s_client -connect app.ragbaz.cc:443 -servername app.ragbaz.cc
   # Should show valid Cloudflare SSL certificate
   ```

5. **Check security headers**
   ```bash
   curl -I https://app.ragbaz.cc | grep -E "Strict-Transport|X-Content-Type|X-Frame"
   # Should show security headers from Caddy
   ```

## Troubleshooting

### DNS not resolving
- Wait for DNS propagation (5-15 minutes)
- Check with: `dig app.ragbaz.cc` or `nslookup app.ragbaz.cc`

### SSL errors
- Ensure Cloudflare SSL mode is "Full (strict)"
- Verify Caddy is running: `docker ps | grep caddy`
- Check Caddy logs: `docker logs wp-ai-caddy`

### 502/504 errors
- Check backend services: `docker compose ps`
- Check Caddy can reach services: `docker exec wp-ai-caddy curl http://web:3000`
- Review Caddy logs: `docker logs wp-ai-caddy --tail 100`

### Rate limiting too aggressive
- Adjust Cloudflare rate limit thresholds
- Add your IP to allowlist in Cloudflare

## Monitoring

1. **Cloudflare Analytics**
   - Navigate to: Analytics & Logs
   - Monitor traffic, requests, bandwidth

2. **Security Events**
   - Navigate to: Security → Events
   - Review blocked requests and threats

3. **Application Logs**
   ```bash
   # Caddy access logs
   docker exec wp-ai-caddy tail -f /var/log/caddy/app-access.log
   docker exec wp-ai-caddy tail -f /var/log/caddy/wp-access.log
   ```

## Support

- Cloudflare Docs: https://developers.cloudflare.com/
- Caddy Docs: https://caddyserver.com/docs/

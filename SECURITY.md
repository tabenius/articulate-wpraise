# Security Policy

## Reporting Security Issues

If you discover a security vulnerability, please email the maintainers directly instead of opening a public issue.

## Secret Management

### Never Commit Secrets

**Never commit the following to git:**
- `.env` files with real credentials
- API keys, tokens, or passwords
- Private keys or certificates
- Database credentials
- Encryption keys

### Use Environment Variables

All secrets must be stored in environment variables:

```bash
# .env (NEVER COMMIT THIS FILE)
MYSQL_ROOT_PASSWORD=your_actual_password
WP_ADMIN_PASS=your_actual_password
ANTHROPIC_API_KEY=sk-ant-api03-...
ENCRYPTION_KEY=your_fernet_key
```

### Template Files

Use `.example` files with placeholders for documentation:

```bash
# .env.example (safe to commit)
MYSQL_ROOT_PASSWORD=your_secure_password_here
WP_ADMIN_PASS=your_secure_admin_password_here
```

### Pre-commit Hook

A pre-commit hook automatically scans for secrets before each commit. To install:

```bash
# Already installed in .git/hooks/pre-commit
# Hook runs automatically on git commit
```

To bypass (NOT RECOMMENDED):
```bash
git commit --no-verify
```

### Secrets Scanner

Run the secrets scanner manually:

```bash
./scripts/scan-secrets.sh
```

This scans the entire codebase for:
- API keys
- Private keys
- Passwords in code
- Authorization tokens
- Database connection strings

## Authentication & Authorization

### Session-Based Authentication

The application uses secure session-based authentication:

- **HTTP-only cookies**: Prevents XSS attacks
- **bcrypt password hashing**: 12 rounds, timing-attack resistant
- **7-day session expiration**: Automatic cleanup of old sessions
- **CSRF protection**: Built into Next.js

### Rate Limiting

Rate limits protect against brute force attacks:

- **Auth endpoints** (/register, /login): 10 requests/minute per IP
- **MCP tool endpoints** (/mcp/*): 100 requests/minute per user
- **Connection management**: 10 requests/minute per user

### Encryption

Sensitive data is encrypted:

- **User passwords**: bcrypt with 12 rounds
- **WordPress app passwords**: Fernet (AES-256-GCM)
- **Cache keys**: SHA256 with user isolation

## Security Headers

The application sets secure HTTP headers:

```
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Strict-Transport-Security: max-age=31536000
X-XSS-Protection: 1; mode=block
```

## SSRF Protection

URL validation prevents Server-Side Request Forgery:

- **Private IPs blocked**: 192.168.x.x, 10.x.x.x, 172.16-31.x.x
- **Metadata endpoints blocked**: 169.254.169.254
- **Localhost allowed**: For development only

## Audit Logging

Security events are logged:

- Login attempts (success/failure)
- Logout events
- Rate limit violations
- Permission denials
- Connection changes

View audit logs:
```bash
docker exec wp-ai-mcp python -c "from wp_mcp.audit import get_recent_events; print(get_recent_events())"
```

## Database Security

### Encryption at Rest

WordPress application passwords are encrypted in the database using Fernet (AES-256-GCM).

### Connection Security

Database connections use:
- **Strong passwords**: Minimum 16 characters
- **Connection pooling**: Limits concurrent connections
- **Prepared statements**: Prevents SQL injection

## Docker Security

### Container Hardening

Containers run with:
- **Non-root users**: Where possible
- **Read-only filesystem**: For immutable layers
- **Resource limits**: CPU and memory constraints
- **Network isolation**: Internal networks for backend services

### Secrets in Production

For production deployments, use Docker secrets:

```yaml
secrets:
  db_password:
    external: true
  encryption_key:
    external: true
```

## Security Checklist

### Before Deployment

- [ ] All secrets in environment variables
- [ ] `.env` files in `.gitignore`
- [ ] Pre-commit hook installed
- [ ] Secrets scanner passes
- [ ] HTTPS enabled
- [ ] Security headers configured
- [ ] Rate limiting enabled
- [ ] Audit logging active
- [ ] Database backups configured
- [ ] Monitoring and alerts set up

### Regular Maintenance

- [ ] Review audit logs weekly
- [ ] Update dependencies monthly
- [ ] Rotate credentials quarterly
- [ ] Security audit annually
- [ ] Penetration testing (as needed)

## Dependency Security

### Automated Scanning

Dependencies are scanned for vulnerabilities:

```bash
# Python dependencies
cd mcp-server && pip-audit

# Node.js dependencies
cd web && npm audit
```

### Update Policy

- **Security patches**: Applied immediately
- **Minor updates**: Reviewed weekly
- **Major updates**: Tested in staging first

## Incident Response

### If Secrets Are Exposed

1. **Rotate immediately**: Change all affected credentials
2. **Revoke access**: Invalidate compromised tokens/keys
3. **Audit logs**: Check for unauthorized access
4. **Notify users**: If user data affected
5. **Document**: Record incident and response

### If Breach Detected

1. **Isolate**: Disconnect affected systems
2. **Preserve evidence**: Capture logs and forensics
3. **Contain**: Stop ongoing attacks
4. **Eradicate**: Remove attacker access
5. **Recover**: Restore from clean backups
6. **Review**: Improve security posture

## Security Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [Next.js Security](https://nextjs.org/docs/app/building-your-application/configuring/security)

## Contact

For security concerns, contact: security@[your-domain].com

Last updated: 2026-02-16

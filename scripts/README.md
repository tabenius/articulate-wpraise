# WP-AI Configuration Scripts

This directory contains setup and configuration tools for WP-AI.

## 1. configure.py - Domain & Proxy Configuration (⭐ New)

Modern Python-based configuration tool for setting up domains, SSL, and reverse proxy with HAProxy management capabilities.

### Features

- **Interactive Configuration**: Guided setup for domains, SSL, and reverse proxy
- **HAProxy Management**: Automatic HAProxy configuration, testing, and reloading
- **DNS Validation**: Checks DNS resolution and provides setup instructions
- **Caddy Integration**: Automatically updates Caddyfile with your domains
- **WordPress Integration**: Updates WordPress URLs in the database
- **SSL Setup**: Guided SSL certificate setup (Cloudflare, Let's Encrypt, Manual)
- **CLI & Interactive Modes**: Use as interactive wizard or with command-line arguments

### Requirements

- Python 3.6+ (standard library only, no dependencies)
- sudo access (for HAProxy management)
- Docker (for WordPress URL updates)

### Usage

#### Interactive Mode (Recommended)

```bash
./scripts/configure.py
```

Follow the prompts to configure your domain, proxy type, and SSL.

#### Non-Interactive Mode

```bash
# HAProxy mode with split domains
./scripts/configure.py \
  --haproxy \
  --app-domain app.example.com \
  --wp-domain my.example.com

# Single domain mode
./scripts/configure.py \
  --wp-domain example.com
```

#### Quick HAProxy Management

```bash
# Test HAProxy configuration
./scripts/configure.py --test-haproxy

# Reload HAProxy service
./scripts/configure.py --reload-haproxy

# Test custom config path
./scripts/configure.py --test-haproxy --haproxy-config /etc/haproxy/haproxy.cfg
```

### What It Does

1. **Detects Proxy Type**: HAProxy, direct Caddy, or other
2. **Collects Domains**: Prompts for app and WordPress domains (or single domain)
3. **Validates DNS**: Checks if domains resolve to your server IP
4. **Updates .env**: Sets DOMAIN, WP_DOMAIN, APP_DOMAIN, WP_SUBDOMAIN
5. **Updates Caddyfile**: Replaces default domains with your domains
6. **Updates WordPress**: Sets WordPress home and siteurl in database
7. **Configures SSL**: Provides Cloudflare/Let's Encrypt/Manual instructions
8. **Manages HAProxy** (if selected):
   - Updates domain ACLs and routing rules
   - Updates SSL certificate paths
   - Updates health check Host headers
   - Tests configuration validity
   - Offers to reload HAProxy service

### Example Workflow

```bash
./scripts/configure.py

# Select HAProxy mode (option 1)
# Enter app domain: app.ragbaz.cc
# Enter WordPress domain: my.ragbaz.cc

# Script will:
# - Check DNS resolution for both domains
# - Update .env, Caddyfile, WordPress URLs
# - Guide you through SSL certificate setup
# - Ask if you want to update HAProxy config
# - Test HAProxy config validity
# - Ask if you want to reload HAProxy
```

### Safety Features

- **Automatic Backups**: Creates .backup files before modifying configs
- **Configuration Testing**: Tests HAProxy config before reloading
- **Confirmation Prompts**: Asks before making changes to HAProxy
- **Color-Coded Output**: Green ✓, Red ✗, Yellow ⚠, Blue info

---

## 2. setup-remote-wordpress.py - Remote WordPress Setup

Automatically configure remote WordPress instances for WP-AI MCP Server integration via SSH.

## Features

- 🔌 SSH connection to remote WordPress servers
- 📦 Automatic plugin installation (WPGraphQL, JWT Authentication)
- 👤 Creates API user with application password
- 🔐 Configures JWT authentication
- ✅ Validates setup and returns connection details

## Requirements

- Python 3.8+
- SSH access to remote server
- WP-CLI installed on remote server
- Remote WordPress installation

## Installation

```bash
cd scripts
pip install -r requirements.txt
```

## Usage

### Basic Usage (with SSH key)

```bash
python setup-remote-wordpress.py \
  --host example.com \
  --user ubuntu \
  --key ~/.ssh/id_rsa
```

### With Password (not recommended)

```bash
python setup-remote-wordpress.py \
  --host example.com \
  --user ubuntu \
  --password your-password
```

### Custom Port and Username

```bash
python setup-remote-wordpress.py \
  --host example.com \
  --user ubuntu \
  --key ~/.ssh/id_rsa \
  --port 2222 \
  --username my-api-user
```

### Save Connection Info to File

```bash
python setup-remote-wordpress.py \
  --host example.com \
  --user ubuntu \
  --key ~/.ssh/id_rsa \
  --output connection.json
```

## What It Does

1. **Connects via SSH** to your remote server
2. **Locates WordPress** installation (searches common paths)
3. **Verifies WP-CLI** is installed
4. **Installs Required Plugins:**
   - wp-graphql
   - wp-graphql-jwt-authentication
5. **Configures JWT Authentication** in wp-config.php
6. **Creates API User** with administrator role
7. **Generates Application Password** for secure API access
8. **Returns Connection Details** ready for MCP Server

## Output

The script outputs connection details in JSON format:

```json
{
  "name": "My WordPress Site (example.com)",
  "wp_url": "https://example.com",
  "wp_graphql_endpoint": "https://example.com/graphql",
  "wp_user": "mcp-api-user",
  "wp_app_password": "xxZB jQ1v noOQ ElSl wNya C4jD",
  "host": "example.com",
  "setup_timestamp": "2026-02-18T10:30:00.000000"
}
```

## Using Connection Details with MCP Server

After running the script, use the connection details to add a connection via:

1. **Web UI:**
   - Navigate to Connections page
   - Click "Add Connection"
   - Paste the connection details

2. **Direct API Call:**
   ```bash
   curl -X POST http://localhost:8000/connections \
     -H "Content-Type: application/json" \
     -H "X-Session-ID: your-session-id" \
     -d '{
       "name": "My WordPress Site",
       "wp_url": "https://example.com",
       "wp_graphql_endpoint": "https://example.com/graphql",
       "wp_user": "mcp-api-user",
       "wp_app_password": "xxZB jQ1v noOQ ElSl wNya C4jD"
     }'
   ```

## Troubleshooting

### WP-CLI Not Found

Install WP-CLI on your remote server:

```bash
# On remote server
curl -O https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar
chmod +x wp-cli.phar
sudo mv wp-cli.phar /usr/local/bin/wp
```

### WordPress Not Found

The script searches common paths:
- `/var/www/html`
- `/var/www/wordpress`
- `/usr/share/nginx/html`
- `/home/*/public_html`
- `/opt/wordpress`

If your WordPress is elsewhere, manually specify in the script or create a symlink.

### Permission Denied

Ensure your SSH user has sudo privileges or can write to WordPress directory:

```bash
# On remote server
sudo chown -R www-data:www-data /var/www/html
sudo chmod -R 755 /var/www/html
```

### Plugin Installation Failed

Verify internet connectivity on remote server and check WordPress permissions:

```bash
# Test on remote server
wp plugin search wpgraphql --path=/var/www/html
```

## Security Notes

- ✅ Uses application passwords (secure, revocable)
- ✅ SSH key authentication recommended
- ✅ JWT secret automatically generated
- ⚠️  Avoid using `--password` flag (use SSH keys instead)
- ⚠️  Keep connection JSON files secure (contains credentials)

## Examples

### Setup Multiple Sites

```bash
# Site 1
python setup-remote-wordpress.py \
  --host site1.example.com \
  --user deploy \
  --key ~/.ssh/id_rsa \
  --output site1-connection.json

# Site 2
python setup-remote-wordpress.py \
  --host site2.example.com \
  --user deploy \
  --key ~/.ssh/id_rsa \
  --output site2-connection.json
```

### Use with Ansible/Automation

```yaml
# ansible-playbook.yml
- name: Setup WordPress for MCP
  hosts: wordpress_servers
  tasks:
    - name: Run setup script
      local_action:
        module: command
        cmd: >
          python setup-remote-wordpress.py
          --host {{ inventory_hostname }}
          --user {{ ansible_user }}
          --key {{ ansible_ssh_private_key_file }}
          --output connections/{{ inventory_hostname }}.json
```

## License

MIT

---

## 3. configure_project.py - Project Env Config REPL (Menu-Driven)

Interactive, colorized project configuration assistant for:

- `/.env`
- `/web/.env.local`

### Features

- Menu-driven workflow (no command memorization needed)
- Clear variable meaning and where to find each key/value
- Strong validation before save (URLs, emails, endpoint shapes, key formats)
- Guided wizard for required-only or full configuration
- Secret masking when listing values
- One-click ENCRYPTION_KEY generation
- Safe save back to both env files
- Profile support (`default`, `dev`, `staging`, `prod`, or custom) with separate env files
- Non-interactive CLI mode for automation/CI (`--set`, `--save`, `--validate`, `--run`)
- Built-in operations menu for:
  - web build (`npm run build`)
  - Docker build/start
  - production deploy (`docker compose -f docker-compose.production.yml up -d --build`)
  - web development server (`npm run dev`)
  - Cloudflare/Wrangler:
    - `wrangler login`
    - `wrangler whoami`
    - `wrangler dev`
    - `wrangler deploy`
    - `wrangler pages deploy`

### Usage

```bash
python3 scripts/configure_project.py
```

### Non-Interactive Examples

```bash
# Validate and save staging profile
python3 scripts/configure_project.py --profile staging --set DOMAIN=staging.example.com --validate --save

# Run production deploy from configured values
python3 scripts/configure_project.py --profile prod --run deploy-prod

# Wrangler deploy for custom profile
python3 scripts/configure_project.py --profile prod --run wrangler-deploy
```

### Notes

- The script shows an ASCII header and colored menus.
- If `.env` or `web/.env.local` is missing, it initializes from example files.
- Use "Save" before quitting to persist updates.

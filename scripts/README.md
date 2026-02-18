# Remote WordPress Setup Script

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

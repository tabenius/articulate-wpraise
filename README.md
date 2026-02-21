# Articulate

AI-powered WordPress content editor. Chat with Claude to create and edit WordPress posts using a block editor, or edit blocks directly in a split-view interface.

## 🚀 Quick Links

- **Development Setup**: See [Quick Start](#quick-start) below
- **Production Deployment**: See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) or [Quick Reference](docs/DEPLOYMENT_QUICK_REFERENCE.md)
- **Security Guide**: See [SECURITY.md](SECURITY.md)

## Architecture

```
Browser  <--SSE/HTTP-->  Next.js API  <--JSON-RPC-->  Python MCP Server (Docker)  <--GraphQL-->  WordPress + MariaDB (Docker)
```

- **Frontend**: Next.js 15, React 19, TypeScript, Tailwind CSS, shadcn/ui
- **AI**: Claude Sonnet 4.5 with streaming and tool use
- **MCP Server**: Python 3.12, FastMCP with HTTP transport
- **CMS**: WordPress 6.7 + WPGraphQL + WPGraphQL Content Blocks
- **Database**: MariaDB 11

## Prerequisites

- Docker & Docker Compose
- Node.js 20+
- An Anthropic API key (optional if using BYOK in the UI)

## Quick Start (Development)

> **⚠️ This is for local development only. For production deployment, see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**

### Automated Setup

```bash
# Run setup script (validates prerequisites, generates secrets)
./scripts/setup.sh
```

The setup script will:
- ✅ Check Docker, Node.js prerequisites
- ✅ Create .env with secure auto-generated passwords
- ✅ Start Docker services (MariaDB, WordPress, Redis, MCP Server)
- ✅ Display WordPress admin credentials

### Manual Setup

If you prefer manual setup:

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env and set passwords (or let setup.sh generate them)

# 2. Start Docker services
docker compose up -d

# 3. Wait for setup to complete
docker compose logs -f wp-setup

# 4. Start the frontend
cd web
cp .env.local.example .env.local
npm install
npm run dev
```

The app will be available at **http://localhost:3000**.

### 4. Verify services

- WordPress admin: http://localhost:8080/wp-admin (admin / admin123)
- GraphQL endpoint: http://localhost:8080/graphql
- MCP Server: http://localhost:8000

## Python Development

For local Python development on the MCP server:

### Setup Virtual Environment

```bash
cd mcp-server

# Create virtual environment with uv (fast package installer)
uv venv

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate  # Windows

# Install dependencies (including dev tools)
uv pip install -e ".[dev]"
```

### Type Checking

```bash
# Run mypy type checker (from mcp-server directory with venv activated)
mypy src/wp_mcp
```

The project uses gradual typing with mypy. See `mypy.ini` for configuration.

### Running Tests

```bash
# Run pytest (from mcp-server directory with venv activated)
pytest
```

### Rebuilding Docker Images

**Important**: When you modify Python source files, you must rebuild the Docker image before testing:

```bash
# Rebuild MCP server image (from project root)
docker compose build mcp-server

# Restart with new image
docker compose down mcp-server
docker compose up -d mcp-server

# Or rebuild and restart in one command
docker compose up -d --build mcp-server
```

## Usage

### Chat Mode
Type in the chat panel to interact with Claude. The AI can:
- Create, edit, and delete posts
- Add, remove, and modify blocks
- Search content
- Manage media

### Editor Mode
Click on any block in the editor panel to edit it directly. Changes are auto-saved to WordPress after 2 seconds of inactivity.

### Supported Block Types
Paragraph, Heading, Image, List, Quote, Code, Columns, Group, Buttons, Spacer, Separator

### API Key (BYOK)
Click the settings icon in the header to enter your own Anthropic API key. The key is stored in your browser's localStorage and sent via request headers. It is never logged or stored server-side.

## Project Structure

```
wp-ai/
├── docker-compose.yml          # All services
├── docker/
│   ├── wordpress/              # WP image + setup script
│   └── mcp-server/             # Python MCP image
├── mcp-server/                 # Python MCP server source
│   └── src/wp_mcp/
│       ├── server.py           # FastMCP entry point
│       ├── tools/              # MCP tools (posts, blocks, pages, media, search)
│       ├── graphql/            # GraphQL client, queries, mutations
│       └── blocks/             # Block parser/serializer
└── web/                        # Next.js frontend
    └── src/
        ├── app/api/            # API routes (chat, posts, blocks, media)
        ├── components/         # UI components (chat, editor, layout)
        ├── stores/             # Zustand state (chat, editor, post)
        ├── hooks/              # Custom hooks (chat, blocks, autosave, sync)
        └── lib/                # Utilities (claude, mcp-client, api)
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `get_posts` | List posts with optional filters |
| `get_post` | Get single post with content |
| `create_post` | Create new post |
| `update_post` | Update post title/content/status |
| `delete_post` | Delete post |
| `get_blocks` | Get structured block tree |
| `update_blocks` | Replace all blocks |
| `insert_block` | Insert block at position |
| `remove_block` | Remove block by clientId |
| `move_block` | Move block to new position |
| `get_pages` / `get_page` | Page read operations |
| `create_page` / `update_page` | Page write operations |
| `get_media` | List media library |
| `search_content` | Search posts and pages |

## Production Deployment

> **📚 Complete deployment guide with multiple reverse proxy options available at [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**
>
> **🚀 Quick reference for fast deployment: [docs/DEPLOYMENT_QUICK_REFERENCE.md](docs/DEPLOYMENT_QUICK_REFERENCE.md)**

### Deployment Options

WP-AI supports multiple production deployment configurations:

1. **Caddy** (Easiest - automatic HTTPS) - Recommended for beginners
2. **Traefik** (Docker-native - automatic HTTPS) - Recommended for Docker deployments
3. **Nginx** (Most popular - manual SSL setup)
4. **HAProxy** (High performance - manual SSL setup)

### Quick Production Setup

```bash
# 1. Run automated setup
./scripts/setup.sh

# 2. Configure your domain
./scripts/configure-domain.sh

# 3. Deploy with production compose (no exposed ports)
docker compose -f docker-compose.production.yml up -d

# 4. Choose and configure reverse proxy (see docs/DEPLOYMENT.md)
# - Caddy: Automatic HTTPS, zero config
# - Traefik: Docker-native, automatic HTTPS
# - Nginx: Traditional, requires Certbot for SSL
# - HAProxy: High performance, requires manual SSL
```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed instructions for each option.

---

### Legacy: HAProxy Configuration

<details>
<summary>Click to expand HAProxy configuration (for reference)</summary>

This section describes how to deploy WP-AI to a production server using HAProxy as a reverse proxy with SSL termination.

### Architecture

```
Internet --> HAProxy (443/80) --> Next.js (3000)
                              --> WordPress (8080)
                              --> MCP Server (8000)
```

### Prerequisites

- HAProxy installed (`sudo apt install haproxy`)
- SSL certificate for your domain
- Docker & Docker Compose running the backend services
- Node.js for the Next.js frontend

### HAProxy Configuration

Add the following to your `/etc/haproxy/haproxy.cfg`:

```haproxy
#---------------------------------------------------------------------
# WP-AI Project Configuration
#---------------------------------------------------------------------

# Frontend for HTTPS (port 443)
frontend https_front
    bind *:443 ssl crt /etc/haproxy/certs/yourdomain.pem
    mode http

    # Security headers
    http-response set-header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
    http-response set-header X-Frame-Options "SAMEORIGIN"
    http-response set-header X-Content-Type-Options "nosniff"
    http-response set-header X-XSS-Protection "1; mode=block"

    # ACL rules for routing
    acl is_your_domain hdr(host) -i yourdomain.com
    acl is_wp_admin path_beg /wp-admin
    acl is_wp_login path_beg /wp-login.php
    acl is_wp_includes path_beg /wp-includes
    acl is_wp_content path_beg /wp-content
    acl is_graphql path_beg /graphql
    acl is_mcp_api path_beg /api/mcp

    # Route to appropriate backend
    use_backend wp_backend if is_your_domain is_wp_admin
    use_backend wp_backend if is_your_domain is_wp_login
    use_backend wp_backend if is_your_domain is_wp_includes
    use_backend wp_backend if is_your_domain is_wp_content
    use_backend wp_backend if is_your_domain is_graphql
    use_backend mcp_backend if is_your_domain is_mcp_api
    use_backend nextjs_backend if is_your_domain

    default_backend nextjs_backend

# Frontend for HTTP (port 80) - redirect to HTTPS
frontend http_front
    bind *:80
    mode http

    acl is_your_domain hdr(host) -i yourdomain.com

    # Redirect HTTP to HTTPS
    redirect scheme https code 301 if is_your_domain !{ ssl_fc }

# Backend for Next.js frontend
backend nextjs_backend
    mode http
    balance roundrobin
    option httpchk GET /
    http-check expect status 200

    # WebSocket support for Next.js HMR
    option forwardfor
    http-request set-header X-Forwarded-Proto https
    http-request set-header X-Forwarded-For %[src]

    server nextjs1 127.0.0.1:3000 check

# Backend for WordPress
backend wp_backend
    mode http
    balance roundrobin
    option httpchk GET /wp-admin/
    http-check expect status 200-399

    option forwardfor
    http-request set-header X-Forwarded-Proto https
    http-request set-header X-Forwarded-For %[src]
    http-request set-header X-Real-IP %[src]

    server wordpress1 127.0.0.1:8080 check

# Backend for MCP Server
backend mcp_backend
    mode http
    balance roundrobin
    option httpchk GET /health
    http-check expect status 200-399

    option forwardfor
    http-request set-header X-Forwarded-Proto https
    http-request set-header X-Forwarded-For %[src]

    # Remove /api/mcp prefix before forwarding to MCP server
    http-request replace-path /api/mcp(/)?(.*) /\2

    server mcp1 127.0.0.1:8000 check

# Stats page (optional)
listen stats
    bind *:8404
    mode http
    stats enable
    stats uri /stats
    stats refresh 30s
    stats auth admin:change_this_password
```

### SSL Certificate Setup

Create a combined PEM file for HAProxy:

```bash
# Create certificate directory
sudo mkdir -p /etc/haproxy/certs

# Combine certificate and private key (e.g., from Let's Encrypt)
sudo cat /etc/letsencrypt/live/yourdomain.com/fullchain.pem \
        /etc/letsencrypt/live/yourdomain.com/privkey.pem \
        > /etc/haproxy/certs/yourdomain.pem

# Secure the certificate
sudo chmod 600 /etc/haproxy/certs/yourdomain.pem
```

### Deployment Steps

1. **Start Docker services**:
   ```bash
   cd /path/to/wp-ai
   docker compose up -d
   ```

2. **Build and start Next.js in production mode**:
   ```bash
   cd web
   npm install
   npm run build
   npm start  # Runs on port 3000
   ```

3. **Configure HAProxy**:
   - Edit `/etc/haproxy/haproxy.cfg` with the configuration above
   - Replace `yourdomain.com` with your actual domain
   - Update certificate path if needed

4. **Test HAProxy configuration**:
   ```bash
   sudo haproxy -c -f /etc/haproxy/haproxy.cfg
   ```

5. **Reload HAProxy**:
   ```bash
   sudo systemctl reload haproxy
   ```

### Routing

- `https://yourdomain.com/` → Next.js frontend (main application)
- `https://yourdomain.com/wp-admin` → WordPress admin panel
- `https://yourdomain.com/graphql` → WordPress GraphQL endpoint
- `https://yourdomain.com/api/mcp/*` → MCP server API

### Process Management

For production, use a process manager like PM2 or systemd to keep Next.js running:

**Using PM2:**
```bash
npm install -g pm2
cd /path/to/wp-ai/web
pm2 start npm --name "wp-ai-web" -- start
pm2 save
pm2 startup  # Follow instructions to enable on boot
```

**Using systemd:**
Create `/etc/systemd/system/wp-ai-web.service`:
```ini
[Unit]
Description=WP-AI Next.js Frontend
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/wp-ai/web
ExecStart=/usr/bin/npm start
Restart=on-failure
Environment=NODE_ENV=production

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable wp-ai-web
sudo systemctl start wp-ai-web
```

### Monitoring

Access HAProxy stats at `http://yourserver:8404/stats` (username: admin, password: as configured).

</details>

---

For complete production deployment instructions with all reverse proxy options, see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## License

MIT

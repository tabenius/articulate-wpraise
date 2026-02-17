# WP-AI Documentation Site

VitePress-powered documentation site with Solarized light and dark themes.

## Features

- 🎨 **Solarized Theme**: Beautiful light and dark themes based on Ethan Schoonover's Solarized color scheme
- 🔍 **Search**: Built-in search functionality
- 📱 **Responsive**: Mobile-friendly design
- ⚡ **Fast**: Static site generation with VitePress
- 🔗 **Integrated**: Automatically deployed with WP-AI production stack

## Development

```bash
# Install dependencies
npm install

# Start development server
npm run docs:dev

# Build static site
npm run docs:build

# Preview built site
npm run docs:preview
```

## Deployment

The documentation site is automatically included in the production deployment:

### Via Docker Compose

```bash
# Build and start all services including docs
docker compose -f docker-compose.production.yml up -d

# Docs will be available at http://localhost:8091
```

### Access via Reverse Proxy

The docs site is automatically routed when using any reverse proxy:

- **URL**: `https://yourdomain.com/docs/`
- **Caddy**: Automatically configured in `docker/caddy/Caddyfile`
- **Nginx**: Automatically configured in `docker/nginx/nginx.conf`
- **Traefik**: Add labels to docker-compose.traefik.yml
- **HAProxy**: Add backend configuration

## Solarized Theme

The documentation uses custom Solarized light and dark themes:

### Solarized Light
- Background: `#fdf6e3` (base3)
- Text: `#657b83` (base00)
- Brand color: `#268bd2` (blue)

### Solarized Dark
- Background: `#002b36` (base03)
- Text: `#839496` (base0)
- Brand color: `#268bd2` (blue)

Theme switching is automatic based on system preference.

## Structure

```
docs-site/
├── .vitepress/
│   ├── config.mts          # VitePress configuration
│   └── theme/
│       ├── index.ts        # Theme entry point
│       └── solarized.css   # Solarized color scheme
├── deployment/             # Deployment guides (symlinked from ../docs)
├── index.md                # Home page
├── getting-started.md      # Getting started guide
├── security.md             # Security documentation
├── Dockerfile              # Production Docker image
├── nginx.conf              # Nginx config for serving docs
└── package.json            # NPM dependencies and scripts
```

## Adding Documentation

### Method 1: Symlink existing docs

```bash
cd docs-site
ln -s ../docs/YOUR_DOC.md your-section.md
```

### Method 2: Create new markdown file

```bash
# Create new page
echo "# My Page" > my-page.md

# Add to sidebar in .vitepress/config.mts
```

### Method 3: Add to subdirectory

```bash
mkdir -p config
cd config
ln -s ../../docs/CONFIG_DOC.md index.md
```

## Customization

### Update Theme Colors

Edit `.vitepress/theme/solarized.css` to customize colors.

### Update Navigation

Edit `.vitepress/config.mts`:

```typescript
nav: [
  { text: 'Home', link: '/' },
  { text: 'Your Section', link: '/your-section' }
]
```

### Update Sidebar

Edit `.vitepress/config.mts`:

```typescript
sidebar: {
  '/': [
    {
      text: 'Your Section',
      items: [
        { text: 'Page 1', link: '/section/page1' },
        { text: 'Page 2', link: '/section/page2' }
      ]
    }
  ]
}
```

## Production Build

The Dockerfile creates a multi-stage build:

1. **Builder stage**: Installs dependencies and builds static site
2. **Production stage**: Serves with Nginx

The built site is optimized and cached for fast serving.

## Reverse Proxy Configuration

### Caddy (Automatic)

Already configured in `docker/caddy/Caddyfile`:
```caddyfile
@docs {
    path /docs*
}
handle @docs {
    reverse_proxy localhost:8091
}
```

### Nginx (Automatic)

Already configured in `docker/nginx/nginx.conf`:
```nginx
location /docs/ {
    proxy_pass http://127.0.0.1:8091/;
}
```

### Traefik

Add to `docker-compose.production.yml`:
```yaml
docs:
  labels:
    - "traefik.enable=true"
    - "traefik.http.routers.docs.rule=Host(`${DOMAIN}`) && PathPrefix(`/docs`)"
    - "traefik.http.routers.docs.entrypoints=websecure"
    - "traefik.http.routers.docs.tls.certresolver=letsencrypt"
```

### HAProxy

Add to `/etc/haproxy/haproxy.cfg`:
```haproxy
acl is_docs path_beg /docs

backend docs_backend
    server docs1 127.0.0.1:8091 check
```

## License

MIT - Same as WP-AI project

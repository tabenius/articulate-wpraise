---
layout: home

hero:
  name: WP-AI
  text: AI-Powered WordPress Editor
  tagline: Chat with Claude to create and edit WordPress content using a block editor
  actions:
    - theme: brand
      text: Get Started
      link: /getting-started
    - theme: alt
      text: View on GitHub
      link: https://github.com/tabenius/wpraise

features:
  - icon: 🤖
    title: AI-Powered Editing
    details: Chat with Claude Sonnet 4.5 to create, edit, and manage WordPress posts using natural language

  - icon: 🎨
    title: Visual Block Editor
    details: Direct manipulation of WordPress blocks with live preview and real-time synchronization

  - icon: 🔧
    title: MCP Server Integration
    details: Python FastMCP server provides WordPress GraphQL tools for AI interaction

  - icon: 🚀
    title: Production Ready
    details: Multiple deployment options with SSL, rate limiting, authentication, and audit logging

  - icon: 🔒
    title: Multi-User & Secure
    details: JWT authentication, per-user WordPress connections, encrypted credentials, SSRF protection

  - icon: 📊
    title: Advanced Features
    details: Featured images, categories/tags, post scheduling, undo/redo, revision timeline, design tools
---

## Quick Example

```bash
# Start development environment
./scripts/setup.sh

# Access the application
open http://localhost:3000
```

## Architecture

```
Browser  <--SSE/HTTP-->  Next.js API  <--JSON-RPC-->  Python MCP Server  <--GraphQL-->  WordPress + MariaDB
```

## Production Deployment

Deploy WP-AI with your choice of reverse proxy:

- **Caddy** - Automatic HTTPS, zero configuration (recommended for beginners)
- **Traefik** - Docker-native with automatic SSL (recommended for containers)
- **Nginx** - Traditional setup with Certbot for SSL
- **HAProxy** - High performance with advanced load balancing

See the [Deployment Guide](/deployment/) for detailed instructions.

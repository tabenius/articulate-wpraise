# Articulate Feature List

> **Last Updated:** 2026-02-19

## 🤖 AI-Powered Content Management
- **Claude AI Integration** - Chat with Claude Sonnet 4.5 to create and edit WordPress content
- **Streaming Responses** - Real-time AI responses with Server-Sent Events (SSE)
- **Tool Use** - Claude can directly manipulate WordPress content via MCP tools
- **BYOK Support** - Bring Your Own API Key or use pre-configured keys

## 📝 WordPress Content Operations
- **Posts & Pages** - Create, read, update, delete posts and pages
- **Block Editor** - Full Gutenberg block support via WPGraphQL Content Blocks
- **Taxonomies** - Manage categories, tags, and custom taxonomies
- **Media Library** - Upload and manage images, files via REST API
- **Font Management** - Upload custom fonts with auto-generated @font-face CSS
- **Revisions** - Track and manage content revisions
- **Search** - Full-text search across WordPress content

## 🏢 Multi-Tenancy & Organizations
- **Organizations** - Create and manage organizations with team members
- **Roles & Permissions** - Admin, member, and owner roles
- **Organization Discovery** - Public/private organization visibility
- **Invitations** - Invite users to organizations via email
- **Multi-WordPress Connections** - Connect multiple WordPress instances per organization

## 🔐 Authentication & Security
- **Session Management** - Redis-backed session storage with JWT
- **WordPress App Passwords** - HTTP Basic Auth with WordPress application passwords
- **Profile Management** - User profiles with avatars, banners, bios
- **Secure Secrets** - Auto-generated secure passwords and API keys

## 🔧 Technical Features
- **MCP Server** - Python FastMCP server with HTTP/SSE transport
- **GraphQL API** - WPGraphQL for efficient data fetching
- **Redis Caching** - Response caching and session storage
- **Celery Workers** - Background task processing (optional)
- **Database Migrations** - Version-controlled database schema changes
- **Health Checks** - Liveness/readiness endpoints for monitoring
- **Docker Deployment** - Full containerized stack with Caddy reverse proxy
- **Type Safety** - TypeScript frontend, MyPy type-checked Python backend

## 🎨 User Interface
- **Modern UI** - Next.js 15 + React 19 + Tailwind CSS + shadcn/ui
- **Responsive Design** - Mobile-friendly interface
- **Real-time Updates** - Live content updates during AI generation
- **Split View** - Side-by-side editor and preview (where applicable)
- **Toast Notifications** - User-friendly error and success messages
- **Progress Tracking** - Upload progress bars with speed indicators

## 🚀 DevOps & Infrastructure
- **Docker Compose** - Multi-container orchestration
- **Production Ready** - Caddy reverse proxy with automatic HTTPS
- **Development Mode** - Hot-reload for rapid development
- **Automated Setup** - One-command setup script
- **Secrets Management** - Auto-generated secure credentials
- **Logging** - Structured JSON logging with request tracking

---

## Recent Additions

### Font Management (2026-02-19)
- Upload custom fonts (WOFF2, WOFF, TTF, OTF, EOT)
- Automatic @font-face CSS generation and injection
- Font family auto-detection from filenames
- Font weight and style configuration
- Live font preview in UI
- Delete and manage uploaded fonts

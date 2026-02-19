# Project Overview

> **Last Updated:** 2026-02-19

## 📖 Description

WP-AI is an AI-powered WordPress content management platform that bridges Claude AI with WordPress through the Model Context Protocol (MCP). It provides a modern web interface where users can chat with Claude to create, edit, and manage WordPress content using natural language, while Claude directly manipulates WordPress data through a Python MCP server that communicates via GraphQL and REST APIs.

## 🎯 Project Aims

### Primary Goals

- Enable natural language content creation for WordPress without technical knowledge
- Provide programmatic WordPress control through AI with full block editor support
- Create a multi-tenant SaaS platform for AI-assisted content management
- Demonstrate MCP integration patterns for complex CMS operations

### Target Use Cases

- Content creators who want AI assistance for WordPress blogging
- Agencies managing multiple client WordPress sites
- Teams collaborating on WordPress content with AI augmentation
- Developers building AI-powered CMS tools

## ✨ Possibilities & Use Cases

### Content Creation

- "Write a blog post about X and publish it with featured image"
- "Convert this outline into a series of WordPress posts"
- "Update all posts in category Y with new information"

### Site Management

- Bulk content operations across multiple WordPress instances
- AI-driven content optimization and SEO improvements
- Automated content translation and localization
- Smart content scheduling and revision management

### Team Collaboration

- Organization-based WordPress access control
- Shared AI conversations for content planning
- Custom font libraries per organization
- Multi-site management dashboard

## ✅ Pros

### Technical Strengths

- **Type-Safe Architecture** - Full TypeScript frontend + MyPy backend
- **Modern Stack** - Next.js 15, React 19, Python 3.12, FastMCP
- **Production Ready** - Docker deployment with Caddy, HTTPS, health checks
- **Scalable Design** - Redis caching, Celery workers, connection pooling
- **Standards-Based** - Uses WordPress GraphQL/REST APIs, no core modifications
- **Well-Documented** - Comprehensive setup guides and deployment docs

### User Experience

- **No WordPress Login** - Manage content without touching wp-admin
- **Natural Language** - No need to learn WordPress UI
- **Real-time Streaming** - See AI responses as they generate
- **Multi-Tenancy** - Organizations can manage multiple sites
- **BYOK Support** - Users can bring their own API keys

### Developer Experience

- **One-Command Setup** - Automated environment configuration
- **Hot Reload** - Fast development iteration
- **Database Migrations** - Version-controlled schema changes
- **MCP Tools** - Extensible plugin architecture

## ❌ Cons

### Current Limitations

- **WordPress Dependency** - Requires specific WordPress plugins (WPGraphQL, WPGraphQL Content Blocks)
- **Docker Required** - No native installation option
- **Single AI Provider** - Only works with Anthropic Claude (no OpenAI/other LLMs)
- **Block Editor Only** - Doesn't support classic WordPress editor
- **No Visual Preview** - Can't see rendered WordPress theme during editing
- **Session-Based Auth** - No OAuth/SSO support yet
- **Limited Error Recovery** - AI errors require manual retry

### Performance Concerns

- **API Latency** - Multiple hops (Browser → Next.js → MCP → WordPress → MariaDB)
- **Cost** - Claude API costs for every operation
- **No Offline Mode** - Requires constant internet connection
- **GraphQL Overhead** - Complex queries for simple operations

### Operational Challenges

- **Multi-Container Stack** - 7+ Docker containers to manage
- **WordPress Versioning** - Must keep WordPress/plugins updated
- **No Built-in Backups** - Manual WordPress backup responsibility
- **Limited Monitoring** - Basic health checks only

## 🔧 Room for Improvement

### High Priority

1. **Visual Block Editor** - Split-view WYSIWYG editor with live WordPress theme preview
2. **Multi-LLM Support** - Add OpenAI GPT-4, Google Gemini, local models
3. **Error Handling** - Retry logic, partial success handling, rollback capabilities
4. **Content Preview** - Render WordPress content with actual theme styles
5. **Offline Drafts** - Local storage for working without connectivity

### Medium Priority

6. **OAuth/SSO** - Support Google, GitHub login
7. **Advanced Caching** - Query result caching, CDN integration
8. **Webhook Support** - Real-time WordPress updates → UI notifications
9. **Plugin Marketplace** - Custom MCP tools/extensions from community
10. **Bulk Operations UI** - Batch edit multiple posts with progress tracking
11. **Content Templates** - Reusable AI prompts and content structures
12. **Analytics Dashboard** - Track AI usage, costs, content performance

### Nice-to-Have

13. **Mobile App** - Native iOS/Android apps
14. **AI Training** - Fine-tune models on organization's content style
15. **Collaboration Features** - Real-time co-editing, comments, suggestions
16. **WordPress Theme Builder** - AI-assisted theme customization
17. **E-commerce Support** - WooCommerce integration
18. **Backup/Restore** - Automated WordPress backups via MCP
19. **A/B Testing** - AI-generated content variants with performance tracking
20. **Localization** - Multi-language UI and content management

### Technical Debt

- Fix TypeScript errors in profile/connections/organizations pages
- Add comprehensive test coverage (unit, integration, e2e)
- Implement rate limiting and abuse prevention
- Add database query optimization and indexing
- Create CI/CD pipeline for automated deployments
- Improve error messages and user feedback
- Add observability (OpenTelemetry, metrics, tracing)

## 🎓 Learning Outcomes

### What This Project Demonstrates

- Production MCP server architecture patterns
- AI-CMS integration techniques
- Multi-tenant SaaS application design
- WordPress API programmatic manipulation
- Real-time streaming AI responses
- Docker microservices orchestration

### Target Audience

- Developers learning MCP/AI integration
- Teams needing AI-powered CMS workflows
- Agencies managing client WordPress sites
- Content creators seeking AI assistance

---

## Architecture Overview

```
Browser  <--SSE/HTTP-->  Next.js API  <--JSON-RPC-->  Python MCP Server  <--GraphQL/REST-->  WordPress + MariaDB
```

**Technology Stack:**

- **Frontend**: Next.js 15, React 19, TypeScript, Tailwind CSS, shadcn/ui
- **AI**: Claude Sonnet 4.5 with streaming and tool use
- **MCP Server**: Python 3.12, FastMCP with HTTP transport
- **CMS**: WordPress 6.7 + WPGraphQL + WPGraphQL Content Blocks
- **Database**: MariaDB 11 with Redis caching
- **Infrastructure**: Docker Compose, Caddy reverse proxy

## Quick Links

- [Features](./features.md)
- [Getting Started](./getting-started.md)
- [Deployment Guide](./deployment/)
- [Security Guide](./security.md)

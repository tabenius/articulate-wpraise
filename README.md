# WP-AI

AI-powered WordPress content editor. Chat with Claude to create and edit WordPress posts using a block editor, or edit blocks directly in a split-view interface.

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

## Quick Start

### 1. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set your `ANTHROPIC_API_KEY` (or leave it blank and use the BYOK option in the UI settings).

### 2. Start Docker services

```bash
docker compose up -d
```

This starts:
- **MariaDB** on port 3306
- **WordPress** on port 8080
- **wp-setup** (one-shot) - installs WPGraphQL plugins, creates app password, adds sample content
- **MCP Server** on port 8000

Wait for the `wp-ai-setup` container to finish (it exits after setup). You can check with:

```bash
docker compose logs wp-setup
```

### 3. Start the frontend

```bash
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

## License

MIT

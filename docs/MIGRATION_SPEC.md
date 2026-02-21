# WordPress Migration Technical Specification

**Version:** 1.0
**Date:** 2026-02-19
**Status:** Draft

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Database Schema](#database-schema)
4. [Migration Options](#migration-options)
5. [API Specification](#api-specification)
6. [Implementation Details](#implementation-details)
7. [Error Handling](#error-handling)
8. [Performance Considerations](#performance-considerations)
9. [Testing Strategy](#testing-strategy)
10. [Implementation Phases](#implementation-phases)

---

## 1. Overview

### 1.1 Purpose

Enable users to migrate WordPress content between different WordPress installations through the Articulate MCP server, with granular control over what content is migrated and how.

### 1.2 Goals

- **Selective Migration**: Allow users to choose what to migrate (posts, pages, media, taxonomies)
- **ID Preservation**: Maintain relationships between content through persistent ID mapping
- **Flexible Media Handling**: Support multiple media transfer strategies
- **Resumable Operations**: Support large migrations with progress tracking and resume capability
- **Safe Operations**: Dry-run mode, validation, and rollback support

### 1.3 Non-Goals

- Live synchronization between sites (one-time migration only)
- Plugin/theme code migration (settings/data only)
- User password migration (security risk)
- Full database cloning (selective content only)

---

## 2. Architecture

### 2.1 System Overview

```
┌─────────────────────────────────────────────────────────┐
│                    User / AI Agent                       │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              MCP Server (FastMCP)                        │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Migration Tools (tools/migration.py)             │  │
│  │  - start_migration()                              │  │
│  │  - get_migration_status()                         │  │
│  │  - cancel_migration()                             │  │
│  │  - list_migration_jobs()                          │  │
│  └───────────────────────────────────────────────────┘  │
│                     │                                    │
│  ┌─────────────────┼────────────────────────────────┐  │
│  │  Migration Engine (migration_engine.py)          │  │
│  │  - MigrationJob class                            │  │
│  │  - CategoryMigrator                              │  │
│  │  - TagMigrator                                   │  │
│  │  - MediaMigrator (3 strategies)                  │  │
│  │  - PostMigrator                                  │  │
│  │  - PageMigrator                                  │  │
│  └──────────────────────────────────────────────────┘  │
│                     │                                    │
│  ┌─────────────────┴────────────────────────────────┐  │
│  │  ID Map Manager (id_map.py)                      │  │
│  │  - store_mapping()                               │  │
│  │  - get_mapping()                                 │  │
│  │  - remap_content()                               │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────┬───────────────────┬───────────────────────┘
              │                   │
      ┌───────▼──────┐    ┌──────▼────────┐
      │  Source WP   │    │  Target WP    │
      │  (GraphQL)   │    │  (GraphQL +   │
      │              │    │   REST API)   │
      └──────────────┘    └───────────────┘
```

### 2.2 Component Responsibilities

#### Migration Tools (MCP Layer)
- Validate user permissions
- Accept migration requests
- Return job status
- Provide user-facing API

#### Migration Engine (Core Logic)
- Execute migration phases sequentially
- Manage async operations
- Update progress
- Handle errors and retry logic

#### ID Map Manager
- Store old→new ID mappings
- Retrieve mappings for remapping
- Bulk ID translation operations

### 2.3 Data Flow

```
1. User initiates migration via MCP tool
2. Job record created with status='pending'
3. Background async task spawned
4. Migration phases execute in order:
   a. Categories → build category_map
   b. Tags → build tag_map
   c. Media → build media_map (with file transfer)
   d. Posts → use all maps for remapping
   e. Pages → use media_map for remapping
5. Progress updated in database after each phase
6. Job marked 'completed' or 'failed'
7. User polls status or receives notification
```

---

## 3. Database Schema

### 3.1 Migration Jobs Table

```sql
CREATE TABLE wp_migration_jobs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    source_connection_id INT NOT NULL,
    target_connection_id INT NOT NULL,

    -- Job metadata
    status ENUM('pending', 'running', 'paused', 'completed', 'failed', 'cancelled')
        DEFAULT 'pending',

    -- Migration configuration (JSON)
    -- See section 4 for structure
    options JSON NOT NULL,

    -- Progress tracking (JSON)
    -- Format: {"categories": {"total": 10, "done": 10}, "posts": {"total": 150, "done": 87}}
    progress JSON,

    -- Checkpoint for resumable operations (JSON)
    -- Format: {"current_phase": "posts", "cursor": "Y3Vyc29yOnYyOpK5...", "last_id": 123}
    checkpoint JSON,

    -- Error tracking
    error_log TEXT,
    error_count INT DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,

    -- Foreign keys
    FOREIGN KEY (user_id) REFERENCES wp_users_auth(id) ON DELETE CASCADE,
    FOREIGN KEY (source_connection_id) REFERENCES wp_wordpress_connections(id) ON DELETE CASCADE,
    FOREIGN KEY (target_connection_id) REFERENCES wp_wordpress_connections(id) ON DELETE CASCADE,

    -- Indexes
    INDEX idx_user_status (user_id, status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### 3.2 ID Mapping Table

```sql
CREATE TABLE wp_migration_id_map (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    job_id INT NOT NULL,

    -- Entity identification
    entity_type ENUM('post', 'page', 'media', 'category', 'tag', 'user', 'custom_post_type') NOT NULL,
    source_id INT NOT NULL,
    target_id INT NOT NULL,

    -- Optional metadata (JSON)
    -- Format: {"source_slug": "old-post", "target_slug": "old-post-1", "conflict": true}
    metadata JSON,

    -- Timestamp
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Foreign key
    FOREIGN KEY (job_id) REFERENCES wp_migration_jobs(id) ON DELETE CASCADE,

    -- Unique constraint: one mapping per source entity per job
    UNIQUE KEY unique_mapping (job_id, entity_type, source_id),

    -- Indexes for fast lookups
    INDEX idx_job_entity (job_id, entity_type),
    INDEX idx_source_lookup (job_id, entity_type, source_id),
    INDEX idx_target_lookup (job_id, entity_type, target_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### 3.3 Migration Errors Table

```sql
CREATE TABLE wp_migration_errors (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    job_id INT NOT NULL,

    -- Error details
    phase ENUM('categories', 'tags', 'media', 'posts', 'pages', 'custom_post_types') NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id INT,
    error_type VARCHAR(100) NOT NULL,  -- 'network_error', 'validation_error', 'permission_error', etc.
    error_message TEXT NOT NULL,

    -- Context (JSON)
    -- Format: {"url": "...", "response_code": 404, "retry_count": 3}
    context JSON,

    -- Timestamp
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Foreign key
    FOREIGN KEY (job_id) REFERENCES wp_migration_jobs(id) ON DELETE CASCADE,

    -- Indexes
    INDEX idx_job_phase (job_id, phase),
    INDEX idx_error_type (error_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

## 4. Migration Options

### 4.1 Options Structure (JSON)

```json
{
  "include": {
    "posts": true,
    "pages": true,
    "media": true,
    "categories": true,
    "tags": true,
    "custom_post_types": ["portfolio", "product"],
    "users": false,
    "settings": false
  },

  "filters": {
    "post_status": ["publish", "draft", "pending"],
    "date_from": "2023-01-01T00:00:00Z",
    "date_to": "2025-12-31T23:59:59Z",
    "author_ids": [1, 2, 3],
    "category_ids": [5, 6],
    "tag_ids": null,
    "exclude_post_ids": [100, 101],
    "include_post_ids": null,
    "min_word_count": null,
    "has_featured_image": null
  },

  "media": {
    "strategy": "download_upload",
    "allowed_mime_types": ["image/*", "video/mp4", "application/pdf"],
    "max_file_size_mb": 50,
    "skip_existing": true,
    "regenerate_thumbnails": false
  },

  "content": {
    "preserve_dates": true,
    "preserve_authors": true,
    "author_mapping": {"1": 2, "3": 4},
    "default_author_id": null,
    "update_content_urls": true,
    "strip_shortcodes": false
  },

  "advanced": {
    "dry_run": false,
    "batch_size": 20,
    "concurrency_limit": 3,
    "retry_failed": true,
    "max_retries": 3,
    "continue_on_error": true,
    "use_wp_cli_for_serialized": true
  }
}
```

### 4.2 Media Migration Strategies

#### Strategy 1: Download/Upload (Default)
```json
{
  "media": {
    "strategy": "download_upload",
    "timeout_seconds": 60,
    "chunk_size_kb": 1024
  }
}
```
- Downloads files from source via HTTP
- Re-uploads to target via WP REST API `/wp/v2/media`
- **Pros:** Works everywhere, no special access needed
- **Cons:** Slower, bandwidth-intensive

#### Strategy 2: Direct Filesystem Copy
```json
{
  "media": {
    "strategy": "filesystem_copy",
    "ssh_host": "source.example.com",
    "ssh_user": "deploy",
    "ssh_key_path": "/home/user/.ssh/id_rsa",
    "source_wp_content": "/var/www/html/wp-content",
    "target_wp_content": "/var/www/newsite/wp-content"
  }
}
```
- Uses SSH/rsync to copy files directly
- Updates database via WP-CLI: `wp media regenerate`
- **Pros:** Very fast for large libraries
- **Cons:** Requires SSH access, server permissions

#### Strategy 3: URL Import
```json
{
  "media": {
    "strategy": "url_import",
    "preserve_source_urls": false
  }
}
```
- Creates media entries with external URLs (no file transfer)
- Optionally triggers background download via `wp media import <url>`
- **Pros:** Instant, good for CDN-hosted media
- **Cons:** External dependencies, may have CORS issues

---

## 5. API Specification

### 5.1 MCP Tool: `start_migration`

**Signature:**
```python
async def start_migration(
    source_connection_id: int,
    target_connection_id: int,
    options: dict,
    context: dict | None = None,
) -> dict[str, Any]
```

**Parameters:**
- `source_connection_id` (int, required): ID of source WordPress connection
- `target_connection_id` (int, required): ID of target WordPress connection
- `options` (dict, required): Migration options (see section 4.1)
- `context` (dict, optional): MCP context with user info

**Returns:**
```json
{
  "job_id": 123,
  "status": "pending",
  "message": "Migration job created successfully",
  "estimated_items": {
    "categories": 10,
    "tags": 25,
    "media": 150,
    "posts": 200,
    "pages": 15
  },
  "dry_run": false
}
```

**Errors:**
- `ValueError`: Invalid connection IDs, user doesn't own connections
- `PermissionError`: User lacks permission for source/target
- `ValidationError`: Invalid options structure

**Example:**
```python
result = await start_migration(
    source_connection_id=2,
    target_connection_id=3,
    options={
        "include": {
            "posts": True,
            "pages": True,
            "media": True,
            "categories": True,
            "tags": True,
        },
        "media": {"strategy": "download_upload"},
        "advanced": {"dry_run": True}
    }
)
# Returns: {"job_id": 42, "status": "pending", "dry_run": True}
```

---

### 5.2 MCP Tool: `get_migration_status`

**Signature:**
```python
async def get_migration_status(
    job_id: int,
    include_errors: bool = False,
    context: dict | None = None,
) -> dict[str, Any]
```

**Parameters:**
- `job_id` (int, required): Migration job ID
- `include_errors` (bool, optional): Include detailed error log (default: False)
- `context` (dict, optional): MCP context

**Returns:**
```json
{
  "job_id": 123,
  "status": "running",
  "current_phase": "posts",
  "progress": {
    "categories": {"total": 10, "done": 10, "failed": 0},
    "tags": {"total": 25, "done": 25, "failed": 0},
    "media": {"total": 150, "done": 150, "failed": 3},
    "posts": {"total": 200, "done": 87, "failed": 2},
    "pages": {"total": 15, "done": 0, "failed": 0}
  },
  "percent_complete": 58,
  "created_at": "2026-02-19T10:00:00Z",
  "started_at": "2026-02-19T10:00:05Z",
  "estimated_completion": "2026-02-19T10:15:00Z",
  "error_count": 5,
  "errors": [
    {
      "phase": "media",
      "entity_id": 456,
      "message": "Failed to download: Connection timeout"
    }
  ]
}
```

---

### 5.3 MCP Tool: `cancel_migration`

**Signature:**
```python
async def cancel_migration(
    job_id: int,
    context: dict | None = None,
) -> dict[str, Any]
```

**Returns:**
```json
{
  "job_id": 123,
  "status": "cancelled",
  "message": "Migration cancelled. Partial progress saved.",
  "rollback_available": false
}
```

---

### 5.4 MCP Tool: `resume_migration`

**Signature:**
```python
async def resume_migration(
    job_id: int,
    context: dict | None = None,
) -> dict[str, Any]
```

**Returns:**
```json
{
  "job_id": 123,
  "status": "running",
  "resumed_from_phase": "posts",
  "message": "Migration resumed from last checkpoint"
}
```

---

### 5.5 MCP Tool: `list_migration_jobs`

**Signature:**
```python
async def list_migration_jobs(
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
    context: dict | None = None,
) -> list[dict[str, Any]]
```

**Returns:**
```json
[
  {
    "job_id": 123,
    "source_connection_id": 2,
    "target_connection_id": 3,
    "status": "completed",
    "created_at": "2026-02-19T10:00:00Z",
    "completed_at": "2026-02-19T10:12:34Z",
    "items_migrated": 385,
    "error_count": 5
  }
]
```

---

## 6. Implementation Details

### 6.1 Core Migration Engine

**File:** `mcp-server/src/wp_mcp/migration_engine.py`

```python
"""Core migration engine for WordPress content migration."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from wp_mcp.database import db
from wp_mcp.graphql.client import get_graphql_client
from wp_mcp.connection_manager import connection_manager

logger = logging.getLogger(__name__)


class MigrationJob:
    """Manages a single migration job execution."""

    def __init__(
        self,
        job_id: int,
        user_id: int,
        source_connection_id: int,
        target_connection_id: int,
        options: dict[str, Any],
    ):
        self.job_id = job_id
        self.user_id = user_id
        self.source_connection_id = source_connection_id
        self.target_connection_id = target_connection_id
        self.options = options

        # Runtime state
        self.source_client = None
        self.target_client = None
        self.target_connection = None
        self.progress = self._init_progress()
        self.checkpoint = {}
        self.id_maps = {
            "category": {},
            "tag": {},
            "media": {},
            "post": {},
            "page": {},
        }

    def _init_progress(self) -> dict[str, dict[str, int]]:
        """Initialize progress tracking structure."""
        return {
            "categories": {"total": 0, "done": 0, "failed": 0},
            "tags": {"total": 0, "done": 0, "failed": 0},
            "media": {"total": 0, "done": 0, "failed": 0},
            "posts": {"total": 0, "done": 0, "failed": 0},
            "pages": {"total": 0, "done": 0, "failed": 0},
        }

    async def run(self) -> None:
        """Execute the migration job."""
        try:
            await self._update_status("running", started_at=datetime.now(timezone.utc))

            # Initialize clients
            self.source_client = await get_graphql_client(
                self.source_connection_id, self.user_id
            )
            self.target_client = await get_graphql_client(
                self.target_connection_id, self.user_id
            )
            self.target_connection = await connection_manager.get_connection(
                self.target_connection_id, self.user_id
            )

            # Execute migration phases
            include = self.options.get("include", {})

            if include.get("categories"):
                await self._migrate_categories()

            if include.get("tags"):
                await self._migrate_tags()

            if include.get("media"):
                await self._migrate_media()

            if include.get("posts"):
                await self._migrate_posts()

            if include.get("pages"):
                await self._migrate_pages()

            # Complete
            await self._update_status("completed", completed_at=datetime.now(timezone.utc))
            logger.info(f"Migration job {self.job_id} completed successfully")

        except Exception as e:
            logger.error(f"Migration job {self.job_id} failed: {e}", exc_info=True)
            await self._update_status("failed", error_log=str(e))
            raise

    async def _migrate_categories(self) -> None:
        """Migrate categories from source to target."""
        from wp_mcp.migration.category_migrator import CategoryMigrator

        migrator = CategoryMigrator(
            self.job_id,
            self.source_client,
            self.target_client,
            self.options,
        )

        self.id_maps["category"] = await migrator.migrate(self.progress)
        await self._save_progress()

    async def _migrate_tags(self) -> None:
        """Migrate tags from source to target."""
        from wp_mcp.migration.tag_migrator import TagMigrator

        migrator = TagMigrator(
            self.job_id,
            self.source_client,
            self.target_client,
            self.options,
        )

        self.id_maps["tag"] = await migrator.migrate(self.progress)
        await self._save_progress()

    async def _migrate_media(self) -> None:
        """Migrate media from source to target."""
        from wp_mcp.migration.media_migrator import MediaMigrator

        strategy = self.options.get("media", {}).get("strategy", "download_upload")

        migrator = MediaMigrator(
            self.job_id,
            self.source_client,
            self.target_connection,
            self.options,
            strategy=strategy,
        )

        self.id_maps["media"] = await migrator.migrate(self.progress)
        await self._save_progress()

    async def _migrate_posts(self) -> None:
        """Migrate posts from source to target with ID remapping."""
        from wp_mcp.migration.post_migrator import PostMigrator

        migrator = PostMigrator(
            self.job_id,
            self.source_client,
            self.target_client,
            self.id_maps,
            self.options,
        )

        self.id_maps["post"] = await migrator.migrate(self.progress, self.checkpoint)
        await self._save_progress()

    async def _migrate_pages(self) -> None:
        """Migrate pages from source to target."""
        from wp_mcp.migration.page_migrator import PageMigrator

        migrator = PageMigrator(
            self.job_id,
            self.source_client,
            self.target_client,
            self.id_maps,
            self.options,
        )

        self.id_maps["page"] = await migrator.migrate(self.progress, self.checkpoint)
        await self._save_progress()

    async def _save_progress(self) -> None:
        """Persist current progress to database."""
        import json
        await db.execute(
            """UPDATE wp_migration_jobs
               SET progress = %s, checkpoint = %s, updated_at = NOW()
               WHERE id = %s""",
            (json.dumps(self.progress), json.dumps(self.checkpoint), self.job_id)
        )

    async def _update_status(
        self,
        status: str,
        error_log: str | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        """Update job status in database."""
        import json

        query_parts = ["UPDATE wp_migration_jobs SET status = %s, updated_at = NOW()"]
        params: list[Any] = [status]

        if error_log is not None:
            query_parts.append("error_log = %s")
            params.append(error_log)

        if started_at is not None:
            query_parts.append("started_at = %s")
            params.append(started_at)

        if completed_at is not None:
            query_parts.append("completed_at = %s")
            params.append(completed_at)

        query_parts.append("WHERE id = %s")
        params.append(self.job_id)

        await db.execute(", ".join(query_parts), tuple(params))


async def start_migration_job(
    job_id: int,
    user_id: int,
    source_connection_id: int,
    target_connection_id: int,
    options: dict[str, Any],
) -> None:
    """Start a migration job in the background."""
    job = MigrationJob(job_id, user_id, source_connection_id, target_connection_id, options)
    await job.run()
```

### 6.2 ID Map Manager

**File:** `mcp-server/src/wp_mcp/migration/id_map.py`

```python
"""ID mapping utilities for migration."""

from __future__ import annotations

from typing import Any
from wp_mcp.database import db


async def store_mapping(
    job_id: int,
    entity_type: str,
    source_id: int,
    target_id: int,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Store an ID mapping in the database."""
    import json

    await db.execute(
        """INSERT INTO wp_migration_id_map
           (job_id, entity_type, source_id, target_id, metadata)
           VALUES (%s, %s, %s, %s, %s)
           ON DUPLICATE KEY UPDATE target_id = %s, metadata = %s""",
        (
            job_id,
            entity_type,
            source_id,
            target_id,
            json.dumps(metadata or {}),
            target_id,
            json.dumps(metadata or {}),
        )
    )


async def get_mapping(
    job_id: int,
    entity_type: str,
    source_id: int,
) -> int | None:
    """Retrieve the target ID for a source ID."""
    result = await db.fetchone(
        """SELECT target_id FROM wp_migration_id_map
           WHERE job_id = %s AND entity_type = %s AND source_id = %s""",
        (job_id, entity_type, source_id)
    )
    return result["target_id"] if result else None


async def get_all_mappings(
    job_id: int,
    entity_type: str,
) -> dict[int, int]:
    """Retrieve all mappings for an entity type as {source_id: target_id}."""
    rows = await db.fetchall(
        """SELECT source_id, target_id FROM wp_migration_id_map
           WHERE job_id = %s AND entity_type = %s""",
        (job_id, entity_type)
    )
    return {row["source_id"]: row["target_id"] for row in rows}


async def remap_featured_image(
    job_id: int,
    source_media_id: int | None,
) -> int | None:
    """Remap a featured image ID, return None if not found."""
    if source_media_id is None:
        return None
    return await get_mapping(job_id, "media", source_media_id)


async def remap_category_ids(
    job_id: int,
    source_category_ids: list[int],
) -> list[int]:
    """Remap a list of category IDs, filtering out unmapped ones."""
    category_map = await get_all_mappings(job_id, "category")
    return [category_map[cid] for cid in source_category_ids if cid in category_map]


async def remap_tag_ids(
    job_id: int,
    source_tag_ids: list[int],
) -> list[int]:
    """Remap a list of tag IDs, filtering out unmapped ones."""
    tag_map = await get_all_mappings(job_id, "tag")
    return [tag_map[tid] for tid in source_tag_ids if tid in tag_map]
```

### 6.3 Media Migrator with Multiple Strategies

**File:** `mcp-server/src/wp_mcp/migration/media_migrator.py`

```python
"""Media migration with multiple strategies."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from wp_mcp.migration.id_map import store_mapping
from wp_mcp.migration.base_migrator import BaseMigrator

logger = logging.getLogger(__name__)


# GraphQL query for paginated media
GET_MEDIA_PAGINATED = """
query GetMediaPaginated($first: Int, $after: String) {
  mediaItems(first: $first, after: $after) {
    pageInfo { hasNextPage endCursor }
    nodes {
      databaseId
      title
      sourceUrl
      altText
      caption
      description
      mimeType
      date
      mediaDetails { file width height }
    }
  }
}
"""


class MediaMigrator(BaseMigrator):
    """Migrates media files between WordPress sites."""

    def __init__(
        self,
        job_id: int,
        source_client,
        target_connection: dict,
        options: dict,
        strategy: str = "download_upload",
    ):
        super().__init__(job_id, source_client, None, options)
        self.target_connection = target_connection
        self.strategy = strategy

        # Extract media options
        self.media_opts = options.get("media", {})
        self.allowed_mimes = self.media_opts.get("allowed_mime_types", ["*"])
        self.max_size_mb = self.media_opts.get("max_file_size_mb", 50)
        self.skip_existing = self.media_opts.get("skip_existing", True)

    async def migrate(self, progress: dict) -> dict[int, int]:
        """Execute media migration and return ID mapping."""
        logger.info(f"Starting media migration (strategy: {self.strategy})")

        # Fetch all media from source
        all_media = await self._fetch_all_media()

        # Filter by options
        filtered_media = self._filter_media(all_media)

        progress["media"]["total"] = len(filtered_media)

        # Execute migration based on strategy
        if self.strategy == "download_upload":
            id_map = await self._download_upload_strategy(filtered_media, progress)
        elif self.strategy == "filesystem_copy":
            id_map = await self._filesystem_copy_strategy(filtered_media, progress)
        elif self.strategy == "url_import":
            id_map = await self._url_import_strategy(filtered_media, progress)
        else:
            raise ValueError(f"Unknown media strategy: {self.strategy}")

        logger.info(f"Media migration complete: {progress['media']['done']} migrated")
        return id_map

    async def _fetch_all_media(self) -> list[dict]:
        """Fetch all media items from source using pagination."""
        all_items = []
        after = None

        while True:
            data = await self.source_client.query(
                GET_MEDIA_PAGINATED,
                variables={"first": 50, "after": after}
            )

            items = data.get("mediaItems", {})
            nodes = items.get("nodes", [])
            all_items.extend(nodes)

            page_info = items.get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                break
            after = page_info["endCursor"]

        return all_items

    def _filter_media(self, media_items: list[dict]) -> list[dict]:
        """Filter media by MIME type and size constraints."""
        filtered = []

        for item in media_items:
            mime = item.get("mimeType", "")

            # Check MIME type
            if not self._is_allowed_mime(mime):
                continue

            # Size check would require fetching Content-Length
            # Skip for now, handle during download

            filtered.append(item)

        return filtered

    def _is_allowed_mime(self, mime: str) -> bool:
        """Check if MIME type is allowed."""
        if "*" in self.allowed_mimes:
            return True

        for allowed in self.allowed_mimes:
            if allowed.endswith("/*"):
                prefix = allowed[:-2]
                if mime.startswith(prefix):
                    return True
            elif mime == allowed:
                return True

        return False

    async def _download_upload_strategy(
        self,
        media_items: list[dict],
        progress: dict,
    ) -> dict[int, int]:
        """Download from source and re-upload to target."""
        id_map = {}

        target_url = self.target_connection["wp_url"]
        target_auth = (
            self.target_connection["wp_user"],
            self.target_connection["wp_app_password"]
        )

        # Process with concurrency limit
        concurrency = self.options.get("advanced", {}).get("concurrency_limit", 3)
        semaphore = asyncio.Semaphore(concurrency)

        async def process_item(item: dict) -> None:
            async with semaphore:
                try:
                    new_id = await self._download_and_upload(
                        item,
                        target_url,
                        target_auth,
                    )

                    if new_id:
                        id_map[item["databaseId"]] = new_id
                        await store_mapping(
                            self.job_id,
                            "media",
                            item["databaseId"],
                            new_id,
                            metadata={"source_url": item["sourceUrl"]}
                        )
                        progress["media"]["done"] += 1
                    else:
                        progress["media"]["failed"] += 1

                except Exception as e:
                    logger.warning(f"Failed to migrate media {item['databaseId']}: {e}")
                    progress["media"]["failed"] += 1
                    await self._log_error("media", item["databaseId"], str(e))

        # Execute all uploads concurrently
        await asyncio.gather(*[process_item(item) for item in media_items])

        return id_map

    async def _download_and_upload(
        self,
        item: dict,
        target_url: str,
        target_auth: tuple,
    ) -> int | None:
        """Download a file and upload to target."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Download
            try:
                download_resp = await client.get(item["sourceUrl"])
                download_resp.raise_for_status()
            except Exception as e:
                logger.error(f"Download failed for {item['sourceUrl']}: {e}")
                return None

            # Check size
            size_mb = len(download_resp.content) / (1024 * 1024)
            if size_mb > self.max_size_mb:
                logger.warning(f"Skipping {item['title']}: {size_mb:.1f}MB exceeds limit")
                return None

            # Upload
            filename = item["sourceUrl"].split("/")[-1].split("?")[0]
            content_type = download_resp.headers.get("content-type", item["mimeType"])

            try:
                upload_resp = await client.post(
                    f"{target_url}/wp-json/wp/v2/media",
                    files={"file": (filename, download_resp.content, content_type)},
                    data={
                        "title": item.get("title", filename),
                        "alt_text": item.get("altText", ""),
                        "caption": item.get("caption", ""),
                    },
                    auth=target_auth,
                )
                upload_resp.raise_for_status()

                result = upload_resp.json()
                return result["id"]

            except Exception as e:
                logger.error(f"Upload failed for {item['title']}: {e}")
                return None

    async def _filesystem_copy_strategy(
        self,
        media_items: list[dict],
        progress: dict,
    ) -> dict[int, int]:
        """Copy files directly via filesystem (requires SSH)."""
        # TODO: Implement SSH/rsync approach
        raise NotImplementedError("Filesystem copy strategy not yet implemented")

    async def _url_import_strategy(
        self,
        media_items: list[dict],
        progress: dict,
    ) -> dict[int, int]:
        """Import media by URL without downloading."""
        # TODO: Implement URL import via wp media import
        raise NotImplementedError("URL import strategy not yet implemented")
```

---

## 7. Error Handling

### 7.1 Error Categories

| Category | Description | Action |
|----------|-------------|--------|
| **Network Errors** | Connection timeouts, DNS failures | Retry with exponential backoff (max 3 retries) |
| **Permission Errors** | 401/403 responses | Fail immediately, log error |
| **Validation Errors** | Invalid data, missing fields | Skip item, log warning, continue |
| **Conflict Errors** | Duplicate slugs, existing content | Use conflict resolution strategy |
| **Rate Limit Errors** | 429 Too Many Requests | Back off, wait, retry |
| **File Errors** | File too large, unsupported format | Skip, log warning |

### 7.2 Retry Logic

```python
async def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    initial_delay: float = 1.0,
) -> Any:
    """Execute function with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return await func()
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            if attempt == max_retries - 1:
                raise
            delay = initial_delay * (2 ** attempt)
            logger.warning(f"Retry {attempt + 1}/{max_retries} after {delay}s: {e}")
            await asyncio.sleep(delay)
```

### 7.3 Conflict Resolution

When a slug already exists on the target site:

1. **Auto-increment slug**: `old-post` → `old-post-1` → `old-post-2`
2. **Log mapping**: Store both source and target slugs in metadata
3. **Continue migration**: Don't fail the entire job

---

## 8. Performance Considerations

### 8.1 Pagination & Cursors

WPGraphQL supports cursor-based pagination:

```graphql
query GetPosts($first: Int, $after: String) {
  posts(first: $first, after: $after) {
    pageInfo {
      hasNextPage
      endCursor
    }
    nodes { ... }
  }
}
```

**Strategy:**
- Fetch 20-50 items per page
- Store `endCursor` in checkpoint
- Resume from cursor on failure

### 8.2 Concurrency Control

```python
semaphore = asyncio.Semaphore(3)  # Max 3 concurrent operations

async with semaphore:
    await upload_media(item)
```

### 8.3 Rate Limiting

Respect target site limits:
- Wait 100ms between requests
- Back off on 429 responses
- Monitor error rates, slow down if >5% fail

### 8.4 Memory Management

For large migrations (10,000+ items):
- Stream results, don't load all into memory
- Process in batches
- Commit ID maps incrementally
- Use database for state, not in-memory

---

## 9. Testing Strategy

### 9.1 Unit Tests

**File:** `mcp-server/tests/test_migration_id_map.py`

```python
import pytest
from wp_mcp.migration.id_map import store_mapping, get_mapping

@pytest.mark.asyncio
async def test_store_and_retrieve_mapping(db_session):
    job_id = 1
    await store_mapping(job_id, "media", 123, 456)

    result = await get_mapping(job_id, "media", 123)
    assert result == 456

@pytest.mark.asyncio
async def test_remap_category_ids(db_session):
    job_id = 1
    await store_mapping(job_id, "category", 5, 10)
    await store_mapping(job_id, "category", 6, 11)

    from wp_mcp.migration.id_map import remap_category_ids
    remapped = await remap_category_ids(job_id, [5, 6, 7])

    assert remapped == [10, 11]  # 7 not mapped, excluded
```

### 9.2 Integration Tests

Test against real WordPress instances:

1. **Setup:** Spin up source WP with test content
2. **Execute:** Run migration with test options
3. **Verify:** Query target WP, confirm content matches
4. **Teardown:** Clean up test instances

### 9.3 E2E Tests

Simulate full user workflow:

```python
@pytest.mark.e2e
async def test_full_post_migration():
    # Start migration
    result = await start_migration(
        source_connection_id=1,
        target_connection_id=2,
        options={"include": {"posts": True}},
    )
    job_id = result["job_id"]

    # Wait for completion
    while True:
        status = await get_migration_status(job_id)
        if status["status"] in ("completed", "failed"):
            break
        await asyncio.sleep(1)

    assert status["status"] == "completed"
    assert status["progress"]["posts"]["done"] > 0
```

---

## 10. Implementation Phases

### Phase 1: Foundation (Week 1-2)

**Goal:** Database schema, basic job management

- [x] Create migration tables SQL
- [ ] Add migration file to `docker/wordpress/migrations/`
- [ ] Implement `MigrationJob` class
- [ ] Implement ID map utilities
- [ ] Add `start_migration`, `get_migration_status` MCP tools
- [ ] Write unit tests for ID mapping

**Deliverable:** Can create migration jobs and track status

---

### Phase 2: Category/Tag Migration (Week 3)

**Goal:** Prove end-to-end flow with simple entities

- [ ] Implement `CategoryMigrator`
- [ ] Implement `TagMigrator`
- [ ] Add pagination support to GraphQL queries
- [ ] Test category/tag migration E2E
- [ ] Add error logging

**Deliverable:** Can migrate categories and tags successfully

---

### Phase 3: Media Migration - Download/Upload (Week 4-5)

**Goal:** Implement default media strategy

- [ ] Implement `MediaMigrator` with download/upload
- [ ] Add concurrency control
- [ ] Add MIME type filtering
- [ ] Add file size limits
- [ ] Handle upload failures gracefully
- [ ] Test with image/video files

**Deliverable:** Can migrate media library via HTTP

---

### Phase 4: Post Migration with ID Remapping (Week 6-7)

**Goal:** Migrate posts with full relationship preservation

- [ ] Implement `PostMigrator`
- [ ] Add featured image remapping
- [ ] Add category/tag remapping
- [ ] Add content URL rewriting
- [ ] Handle serialized PHP data via WP-CLI
- [ ] Add post filtering (date, status, author)
- [ ] Test with complex posts

**Deliverable:** Can migrate posts with all relationships intact

---

### Phase 5: Page Migration & Hierarchy (Week 8)

**Goal:** Handle page parent-child relationships

- [ ] Implement `PageMigrator`
- [ ] Handle page hierarchy (parent_id remapping)
- [ ] Test with nested pages

**Deliverable:** Can migrate pages with hierarchy preserved

---

### Phase 6: Advanced Features (Week 9-10)

**Goal:** Polish and production-readiness

- [ ] Add `cancel_migration`, `resume_migration` tools
- [ ] Implement checkpoint/resume logic
- [ ] Add dry-run mode
- [ ] Add progress estimation
- [ ] Implement filesystem_copy strategy
- [ ] Implement url_import strategy
- [ ] Add comprehensive error handling
- [ ] Write integration tests
- [ ] Performance optimization

**Deliverable:** Production-ready migration system

---

### Phase 7: Documentation & UI (Week 11)

**Goal:** User-facing polish

- [ ] Write user documentation
- [ ] Add frontend UI for migration wizard
- [ ] Add progress bar visualization
- [ ] Add migration history view
- [ ] Create tutorial videos

**Deliverable:** Complete user experience

---

## Appendix A: GraphQL Queries

### A.1 Paginated Posts Query

```graphql
query GetPostsPaginated($first: Int, $after: String, $where: RootQueryToPostConnectionWhereArgs) {
  posts(first: $first, after: $after, where: $where) {
    pageInfo {
      hasNextPage
      endCursor
    }
    nodes {
      databaseId
      title
      slug
      status
      content
      excerpt
      date
      modified
      author {
        node {
          databaseId
          name
          email
        }
      }
      featuredImage {
        node {
          databaseId
          sourceUrl
          altText
          caption
        }
      }
      categories {
        nodes {
          databaseId
          name
          slug
        }
      }
      tags {
        nodes {
          databaseId
          name
          slug
        }
      }
    }
  }
}
```

### A.2 Paginated Pages Query

```graphql
query GetPagesPaginated($first: Int, $after: String) {
  pages(first: $first, after: $after) {
    pageInfo {
      hasNextPage
      endCursor
    }
    nodes {
      databaseId
      title
      slug
      status
      content
      date
      modified
      parent {
        node {
          databaseId
        }
      }
      featuredImage {
        node {
          databaseId
          sourceUrl
        }
      }
    }
  }
}
```

---

## Appendix B: WP-CLI Commands

### B.1 Search-Replace for Serialized Data

```bash
# Replace URLs in database (handles PHP serialization)
wp search-replace \
  'http://old-site.com' \
  'https://new-site.com' \
  --allow-root \
  --skip-columns=guid
```

### B.2 Media Regeneration

```bash
# Regenerate thumbnails after filesystem copy
wp media regenerate --yes --allow-root
```

### B.3 URL Import

```bash
# Import media by URL
wp media import https://source-site.com/wp-content/uploads/image.jpg \
  --title="Imported Image" \
  --allow-root
```

---

## Appendix C: Migration Flow Diagram

```
┌──────────────────┐
│ User starts      │
│ migration via AI │
└────────┬─────────┘
         │
         ▼
┌────────────────────────┐
│ Create job record      │
│ status = 'pending'     │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│ Spawn async task       │
│ Update status='running'│
└────────┬───────────────┘
         │
         ├──────────────────────────┐
         │                          │
         ▼                          ▼
    ┌─────────┐              ┌──────────┐
    │Categories│──map──┐     │   Tags   │──map──┐
    └─────────┘        │     └──────────┘       │
                       │                         │
                       ▼                         ▼
                  ┌────────────────────────────────┐
                  │      Media Migration           │
                  │  ┌──────────────────────────┐  │
                  │  │ Strategy Selection:      │  │
                  │  │ • download_upload        │  │
                  │  │ • filesystem_copy        │  │
                  │  │ • url_import             │  │
                  │  └──────────────────────────┘  │
                  └────────┬───────────────────────┘
                           │ media_map
                           │
         ┌─────────────────┴─────────────────┐
         │                                   │
         ▼                                   ▼
    ┌─────────┐                         ┌────────┐
    │  Posts  │ ←─ Remap IDs ────────── │ Pages  │
    │         │    (featured_image,     │        │
    │         │     categories, tags)   │        │
    └─────────┘                         └────────┘
         │                                   │
         └─────────────────┬─────────────────┘
                           │
                           ▼
                  ┌────────────────┐
                  │ URL Rewriting  │
                  │ (via WP-CLI)   │
                  └────────┬───────┘
                           │
                           ▼
                  ┌────────────────┐
                  │ Complete job   │
                  │ status=        │
                  │ 'completed'    │
                  └────────────────┘
```

---

## End of Specification

**Next Steps:**
1. Review and approve this specification
2. Begin Phase 1 implementation
3. Set up CI/CD for migration tests
4. Create GitHub project board for tracking

**Questions/Feedback:**
Please provide feedback on:
- Database schema design
- Migration options structure
- Error handling strategy
- Performance targets
- Testing approach

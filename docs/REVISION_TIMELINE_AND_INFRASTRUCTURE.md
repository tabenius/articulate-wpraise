# Revision Timeline & Backend Infrastructure Improvements

## Current State Analysis

### WordPress Revision System
WordPress has a built-in revision system that:
- Stores revisions in `wp_posts` table with `post_type = 'revision'`
- Automatically creates revisions on save (configurable via `WP_POST_REVISIONS`)
- Tracks author, date, and full content for each revision
- Supports revision comparison and restoration

### Current MCP Implementation Gap
- No GraphQL queries for fetching revisions
- No MCP tools for revision operations (compare, restore)
- No UI components for viewing revision history

---

## Implementation Plan: Revision Timeline

### Phase 1: Backend - Revision Support (Week 1)

#### 1. GraphQL Queries for Revisions

**File**: `/mcp-server/src/wp_mcp/graphql/queries.py`

```python
GET_POST_REVISIONS = """
query GetPostRevisions($id: ID!, $first: Int = 20) {
  post(id: $id, idType: DATABASE_ID) {
    databaseId
    revisions(first: $first, where: {orderby: {field: DATE, order: DESC}}) {
      nodes {
        databaseId
        date
        modified
        author {
          node {
            name
            email
          }
        }
        content
        title
      }
    }
  }
}
"""

GET_REVISION_DETAILS = """
query GetRevision($id: ID!) {
  post(id: $id, idType: DATABASE_ID) {
    databaseId
    date
    modified
    title
    content
    author {
      node {
        name
        email
      }
    }
  }
}
"""
```

#### 2. MCP Tool: Get Revisions

**File**: `/mcp-server/src/wp_mcp/tools/revisions.py` (NEW)

```python
"""WordPress revision operations."""

from typing import Any
from ..graphql.client import gql_client
from ..graphql.queries import GET_POST_REVISIONS, GET_REVISION_DETAILS

@mcp.tool()
async def get_post_revisions(post_id: int, limit: int = 20) -> list[dict[str, Any]]:
    """Get revision history for a post.

    Args:
        post_id: WordPress post database ID
        limit: Maximum number of revisions to return (default 20)

    Returns:
        List of revisions with id, date, author, title preview
    """
    result = await gql_client.execute(
        GET_POST_REVISIONS,
        {"id": str(post_id), "first": limit}
    )

    post = result.get("post")
    if not post:
        return []

    revisions = post.get("revisions", {}).get("nodes", [])

    return [
        {
            "id": rev["databaseId"],
            "date": rev["date"],
            "author": rev["author"]["node"]["name"],
            "title": rev["title"][:50],
            "contentPreview": rev["content"][:200],
        }
        for rev in revisions
    ]


@mcp.tool()
async def compare_revisions(
    post_id: int,
    revision_id_1: int,
    revision_id_2: int
) -> dict[str, Any]:
    """Compare two post revisions.

    Args:
        post_id: WordPress post database ID
        revision_id_1: First revision ID
        revision_id_2: Second revision ID

    Returns:
        Comparison data with both revision contents
    """
    result1 = await gql_client.execute(
        GET_REVISION_DETAILS,
        {"id": str(revision_id_1)}
    )
    result2 = await gql_client.execute(
        GET_REVISION_DETAILS,
        {"id": str(revision_id_2)}
    )

    return {
        "revision1": result1.get("post"),
        "revision2": result2.get("post"),
    }


@mcp.tool()
async def restore_revision(post_id: int, revision_id: int) -> dict[str, Any]:
    """Restore a post to a previous revision.

    Args:
        post_id: WordPress post database ID
        revision_id: Revision ID to restore

    Returns:
        Updated post data
    """
    # Use WP-CLI to restore revision (GraphQL doesn't support this directly)
    import subprocess

    result = subprocess.run(
        ["wp", "post", "update", str(post_id),
         "--from-revision", str(revision_id),
         "--allow-root"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(f"Failed to restore revision: {result.stderr}")

    # Fetch updated post
    from .posts import get_post
    return await get_post(post_id)
```

#### 3. Register Revision Tools

**File**: `/mcp-server/src/wp_mcp/tools/__init__.py`

```python
from . import revisions  # Add this import
```

### Phase 2: Frontend - Revision Timeline UI (Week 1-2)

#### 1. Revision Type Definitions

**File**: `/web/src/types/revision.ts` (NEW)

```typescript
export interface Revision {
  id: number;
  date: string;
  author: string;
  title: string;
  contentPreview: string;
}

export interface RevisionComparison {
  revision1: {
    id: number;
    date: string;
    author: { name: string };
    title: string;
    content: string;
  };
  revision2: {
    id: number;
    date: string;
    author: { name: string };
    title: string;
    content: string;
  };
}
```

#### 2. Revision API Routes

**File**: `/web/src/app/api/revisions/route.ts` (NEW)

```typescript
import { NextRequest, NextResponse } from "next/server";
import { callMcpTool } from "@/lib/mcp";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const postId = searchParams.get("postId");
  const limit = searchParams.get("limit") || "20";

  if (!postId) {
    return NextResponse.json(
      { error: "Post ID required" },
      { status: 400 }
    );
  }

  try {
    const revisions = await callMcpTool("get_post_revisions", {
      post_id: parseInt(postId),
      limit: parseInt(limit),
    });

    return NextResponse.json(revisions);
  } catch (error) {
    return NextResponse.json(
      { error: "Failed to fetch revisions" },
      { status: 500 }
    );
  }
}
```

**File**: `/web/src/app/api/revisions/compare/route.ts` (NEW)

```typescript
import { NextRequest, NextResponse } from "next/server";
import { callMcpTool } from "@/lib/mcp";

export async function POST(request: NextRequest) {
  const { postId, revisionId1, revisionId2 } = await request.json();

  try {
    const comparison = await callMcpTool("compare_revisions", {
      post_id: postId,
      revision_id_1: revisionId1,
      revision_id_2: revisionId2,
    });

    return NextResponse.json(comparison);
  } catch (error) {
    return NextResponse.json(
      { error: "Failed to compare revisions" },
      { status: 500 }
    );
  }
}
```

**File**: `/web/src/app/api/revisions/restore/route.ts` (NEW)

```typescript
import { NextRequest, NextResponse } from "next/server";
import { callMcpTool } from "@/lib/mcp";

export async function POST(request: NextRequest) {
  const { postId, revisionId } = await request.json();

  try {
    const post = await callMcpTool("restore_revision", {
      post_id: postId,
      revision_id: revisionId,
    });

    return NextResponse.json(post);
  } catch (error) {
    return NextResponse.json(
      { error: "Failed to restore revision" },
      { status: 500 }
    );
  }
}
```

#### 3. Revision Timeline Component

**File**: `/web/src/components/editor/revision-timeline.tsx` (NEW)

```typescript
"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Clock, RotateCcw, GitCompare } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { usePostStore } from "@/stores/post-store";
import { Revision } from "@/types/revision";
import { formatDistanceToNow } from "date-fns";

export function RevisionTimeline() {
  const [open, setOpen] = useState(false);
  const [revisions, setRevisions] = useState<Revision[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedRevision, setSelectedRevision] = useState<number | null>(null);
  const currentPost = usePostStore((s) => s.currentPost);
  const { toast } = useToast();

  useEffect(() => {
    if (open && currentPost) {
      fetchRevisions();
    }
  }, [open, currentPost]);

  const fetchRevisions = async () => {
    if (!currentPost) return;

    setLoading(true);
    try {
      const response = await fetch(
        `/api/revisions?postId=${currentPost.id}&limit=50`
      );
      const data = await response.json();
      setRevisions(data);
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to load revisions",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleRestore = async (revisionId: number) => {
    if (!currentPost) return;

    try {
      const response = await fetch("/api/revisions/restore", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          postId: currentPost.id,
          revisionId,
        }),
      });

      if (response.ok) {
        toast({
          variant: "success",
          title: "Revision restored",
          description: "Post has been restored to the selected revision",
        });
        setOpen(false);
        // Trigger post reload
        window.location.reload();
      } else {
        throw new Error("Failed to restore");
      }
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to restore revision",
      });
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm">
          <Clock className="h-4 w-4 mr-2" />
          Revisions
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Revision History
          </DialogTitle>
          <DialogDescription>
            View and restore previous versions of this post
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="h-[calc(80vh-8rem)]">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            </div>
          ) : revisions.length === 0 ? (
            <div className="text-center text-muted-foreground py-12">
              <Clock className="h-12 w-12 mx-auto mb-4 opacity-40" />
              <p>No revisions found</p>
            </div>
          ) : (
            <div className="space-y-2 pr-4">
              {revisions.map((revision, index) => (
                <div
                  key={revision.id}
                  className={`border rounded-lg p-4 hover:bg-accent/50 transition-colors ${
                    selectedRevision === revision.id ? "bg-accent" : ""
                  }`}
                  onClick={() => setSelectedRevision(revision.id)}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-medium text-sm">
                          {revision.author}
                        </span>
                        {index === 0 && (
                          <span className="text-xs bg-primary text-primary-foreground px-2 py-0.5 rounded-full">
                            Current
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {formatDistanceToNow(new Date(revision.date), {
                          addSuffix: true,
                        })}
                      </div>
                    </div>
                    {index !== 0 && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRestore(revision.id);
                        }}
                      >
                        <RotateCcw className="h-4 w-4 mr-1" />
                        Restore
                      </Button>
                    )}
                  </div>
                  <div className="text-sm text-muted-foreground line-clamp-2">
                    {revision.contentPreview}
                  </div>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
```

#### 4. Integrate into Editor

**File**: `/web/src/components/editor/editor-panel.tsx`

Add to imports:
```typescript
import { RevisionTimeline } from "./revision-timeline";
```

Add to toolbar (right section, after DesignSystemPanel):
```typescript
<RevisionTimeline />
```

---

## Top Priority Backend Infrastructure Improvements

### 1. **Caching Layer (CRITICAL - Week 2-3)**

**Problem**: Every GraphQL query hits WordPress directly, causing:
- Slow response times (200-500ms per query)
- High database load
- Poor scalability

**Solution**: Redis caching layer

```python
# /mcp-server/src/wp_mcp/cache.py (NEW)
import redis.asyncio as redis
import json
from typing import Any, Optional

class CacheManager:
    def __init__(self):
        self.redis = redis.from_url("redis://redis:6379/0")

    async def get(self, key: str) -> Optional[dict[str, Any]]:
        """Get cached value."""
        value = await self.redis.get(key)
        return json.loads(value) if value else None

    async def set(self, key: str, value: dict[str, Any], ttl: int = 300):
        """Set cached value with TTL (default 5 minutes)."""
        await self.redis.setex(key, ttl, json.dumps(value))

    async def invalidate_pattern(self, pattern: str):
        """Invalidate all keys matching pattern."""
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)

cache = CacheManager()

# Usage in tools:
@mcp.tool()
async def get_post(post_id: int):
    cache_key = f"post:{post_id}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    # Fetch from GraphQL
    result = await gql_client.execute(...)
    await cache.set(cache_key, result, ttl=300)
    return result
```

**Impact**:
- 80-95% reduction in response time
- 10x scalability improvement
- Foundation for real-time features

**Docker Compose Addition**:
```yaml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  volumes:
    - redis_data:/data
```

---

### 2. **Background Job Queue (HIGH - Week 3-4)**

**Problem**:
- Long-running tasks (media processing, bulk operations) block API responses
- No retry mechanism for failed operations
- Cannot schedule tasks (e.g., publishing scheduled posts)

**Solution**: Celery + Redis task queue

```python
# /mcp-server/src/wp_mcp/tasks.py (NEW)
from celery import Celery

celery_app = Celery("wp_mcp", broker="redis://redis:6379/1")

@celery_app.task(bind=True, max_retries=3)
def process_media_upload(self, file_url: str, post_id: int):
    """Background task for media processing."""
    try:
        # Download, optimize, upload to WordPress
        # Update post with media ID
        pass
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)

@celery_app.task
def publish_scheduled_posts():
    """Cron task to publish scheduled posts."""
    # Check for posts with status="future" and date <= now
    # Update status to "publish"
    pass
```

**Impact**:
- Instant API responses (offload to background)
- Reliable task execution with retries
- Enable scheduling, batch operations

---

### 3. **Rate Limiting & Throttling (HIGH - Week 4)**

**Problem**:
- No protection against API abuse
- AI chat can flood WordPress with requests
- No per-user quotas

**Solution**: Redis-based rate limiting

```python
# /mcp-server/src/wp_mcp/middleware/rate_limit.py (NEW)
from fastapi import Request, HTTPException
import time

class RateLimiter:
    def __init__(self, redis_client, max_requests: int = 100, window: int = 60):
        self.redis = redis_client
        self.max_requests = max_requests
        self.window = window

    async def check_rate_limit(self, user_id: str) -> bool:
        """Check if user is within rate limit."""
        key = f"rate_limit:{user_id}"
        current = await self.redis.incr(key)

        if current == 1:
            await self.redis.expire(key, self.window)

        if current > self.max_requests:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Max {self.max_requests} requests per {self.window}s"
            )

        return True
```

**Limits**:
- 100 requests/minute for MCP tools
- 1000 requests/hour for GraphQL queries
- 10 concurrent AI chat requests per user

**Impact**:
- Prevent API abuse and DoS
- Fair resource allocation
- Cost control for AI API usage

---

### 4. **Structured Logging & Monitoring (MEDIUM - Week 5)**

**Problem**:
- No visibility into errors, performance bottlenecks
- Debug issues in production
- No metrics for optimization

**Solution**: Structured logging with ELK stack or Grafana Loki

```python
# /mcp-server/src/wp_mcp/logging_config.py (NEW)
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.dev.ConsoleRenderer(),  # Human-readable in dev
        structlog.processors.JSONRenderer(),  # JSON in production
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()

# Usage:
logger.info("post_created", post_id=123, user_id=1, duration_ms=45)
logger.error("graphql_query_failed", query="GET_POST", error=str(e))
```

**Metrics to Track**:
- API response times (p50, p95, p99)
- Error rates by endpoint
- Cache hit/miss ratios
- WordPress database query times
- AI chat token usage

**Impact**:
- Proactive issue detection
- Performance optimization data
- User behavior insights

---

### 5. **Database Connection Pooling (MEDIUM - Week 5)**

**Problem**:
- WordPress REST API/GraphQL creates new DB connection per request
- Connection overhead slows queries
- Exhausts MySQL max_connections under load

**Solution**: ProxySQL as MySQL proxy

```yaml
# docker-compose.yml addition
proxysql:
  image: proxysql/proxysql:2.5
  ports:
    - "6033:6033"  # ProxySQL port
  environment:
    - PROXYSQL_ADMIN_PASSWORD=admin
  volumes:
    - ./docker/proxysql/proxysql.cnf:/etc/proxysql.cnf
```

**ProxySQL Config**:
```cnf
mysql_servers =
(
    { address="mariadb", port=3306, hostgroup=0, max_connections=100 }
)

mysql_users =
(
    { username="wordpress", password="wordpress", default_hostgroup=0, max_connections=50 }
)

# Query caching for read-only queries
mysql_query_rules =
(
    { rule_id=1, active=1, cache_ttl=300, apply=1 }
)
```

**WordPress Config Update**:
```php
// wp-config.php
define('DB_HOST', 'proxysql:6033');  // Instead of mariadb:3306
```

**Impact**:
- 20-30% query performance improvement
- Handle 10x more concurrent requests
- Built-in query caching

---

### 6. **Health Checks & Circuit Breakers (LOW - Week 6)**

**Problem**:
- System continues attempting failed operations
- No graceful degradation when WordPress is down
- Cascading failures

**Solution**: Circuit breaker pattern

```python
# /mcp-server/src/wp_mcp/circuit_breaker.py (NEW)
from datetime import datetime, timedelta

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == "OPEN":
            if datetime.now() - self.last_failure_time > timedelta(seconds=self.timeout):
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            self.failures = 0
            self.state = "CLOSED"
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure_time = datetime.now()

            if self.failures >= self.failure_threshold:
                self.state = "OPEN"

            raise e
```

**Health Check Endpoints**:
```python
@app.get("/health")
async def health_check():
    """Basic health check."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/health/deep")
async def deep_health_check():
    """Check all dependencies."""
    health = {
        "wordpress": await check_wordpress_health(),
        "redis": await check_redis_health(),
        "database": await check_database_health(),
    }

    if not all(health.values()):
        return JSONResponse(status_code=503, content={"status": "unhealthy", "details": health})

    return {"status": "healthy", "details": health}
```

**Impact**:
- Prevent cascading failures
- Faster error detection
- Graceful degradation

---

## Priority Matrix

| Feature | Priority | Effort | Impact | Timeline |
|---------|----------|--------|--------|----------|
| **Revision Timeline** | HIGH | Medium | High | Week 1-2 |
| **Redis Caching** | CRITICAL | Low | Very High | Week 2-3 |
| **Background Jobs** | HIGH | Medium | High | Week 3-4 |
| **Rate Limiting** | HIGH | Low | High | Week 4 |
| **Structured Logging** | MEDIUM | Medium | Medium | Week 5 |
| **Connection Pooling** | MEDIUM | Low | Medium | Week 5 |
| **Circuit Breakers** | LOW | Low | Medium | Week 6 |

---

## Implementation Order

### Weeks 1-2: Revision Timeline (User-Facing)
- Immediate value for content creators
- Low infrastructure risk
- Tests backend tool development workflow

### Weeks 2-4: Critical Infrastructure (Redis, Jobs, Rate Limiting)
- Foundation for scalability
- Enables advanced features (scheduling, media processing)
- Prevents production issues

### Weeks 5-6: Observability & Reliability (Logging, Pooling, Circuit Breakers)
- Production-readiness
- Long-term maintainability
- Performance optimization

---

## Verification & Testing

### Revision Timeline Testing
1. Create post, make 10 edits
2. Open revision timeline → see 10 revisions
3. Click restore on revision #5 → verify content restored
4. Test with concurrent edits from different users

### Infrastructure Testing
1. **Caching**: Compare response times with/without Redis (should see 80%+ improvement)
2. **Jobs**: Upload large media file, verify background processing
3. **Rate Limiting**: Send 101 requests in 60s, verify 429 error
4. **Logging**: Trigger error, verify structured log in Grafana
5. **Load Testing**: Use k6 to simulate 1000 concurrent users

### Performance Benchmarks
- Target: <100ms API response time (cached)
- Target: <500ms API response time (uncached)
- Target: Handle 1000 concurrent requests
- Target: 99.9% uptime

---

## Dependencies & Risks

### Dependencies
- Redis for caching, rate limiting, job queue
- Celery for background jobs
- ProxySQL for connection pooling

### Risks & Mitigations
1. **Redis SPOF**: Mitigation - Redis Sentinel for HA
2. **Cache invalidation complexity**: Mitigation - Simple TTL-based invalidation initially
3. **Background job failures**: Mitigation - Retry mechanism + dead letter queue

---

## Cost Analysis

### Infrastructure Costs (Monthly)
- Redis (1GB): $10-15
- Celery workers (2x): $20-30
- ProxySQL: $0 (self-hosted)
- Monitoring (Grafana Cloud): $0-50

**Total**: ~$30-100/month for production-grade infrastructure

### Performance Gains
- 10x request capacity
- 80% faster response times
- 99.9% uptime vs 95%

**ROI**: Clear positive - infrastructure pays for itself through improved user experience and reduced support costs.

---

This plan provides a clear roadmap from basic revision timeline to production-grade infrastructure, with measurable impact at each stage.

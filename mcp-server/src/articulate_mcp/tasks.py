"""Celery tasks for background job processing."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from celery import Celery
from celery.schedules import crontab

from articulate_mcp.config import config
from articulate_mcp.graphql.client import gql_client
from articulate_mcp.graphql.queries import GET_POSTS
from articulate_mcp.graphql.mutations import UPDATE_POST

logger = logging.getLogger(__name__)

# Initialize Celery app
celery_app = Celery(
    "articulate_mcp",
    broker=config.celery_broker_url,
    backend=config.celery_result_backend,
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max
    task_soft_time_limit=240,  # 4 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)

# Scheduled tasks (Celery Beat)
celery_app.conf.beat_schedule = {
    "publish-scheduled-posts": {
        "task": "articulate_mcp.tasks.publish_scheduled_posts",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes
    },
}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_media_upload(self, file_url: str, post_id: int, title: str = "", alt_text: str = ""):
    """Background task for media processing and upload.

    Args:
        file_url: URL of the file to download and upload
        post_id: WordPress post ID to attach media to
        title: Media title
        alt_text: Alt text for images

    Returns:
        Media ID if successful
    """
    try:
        logger.info("Processing media upload: %s for post %d", file_url, post_id)

        # TODO: Implement actual media processing
        # 1. Download file from file_url
        # 2. Optimize/resize if image
        # 3. Upload to WordPress via REST API
        # 4. Attach to post

        # Placeholder for now
        logger.info("Media upload completed for post %d", post_id)
        return {"success": True, "media_id": None}

    except Exception as exc:
        logger.error("Media upload failed for post %d: %s", post_id, exc)
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3)
def publish_scheduled_posts(self):
    """Scheduled task to publish posts with future status.

    Runs every 5 minutes to check for posts that should be published.
    """
    try:
        logger.info("Checking for scheduled posts to publish")

        # Run async code in sync context
        async def _publish():
            # Query for future posts
            result = await gql_client.query(
                GET_POSTS,
                variables={"first": 100, "where": {"status": "FUTURE"}},
            )

            posts = result.get("posts", {}).get("nodes", [])
            published_count = 0

            for post in posts:
                post_id = post["databaseId"]
                post_date = datetime.fromisoformat(post["date"].replace("Z", "+00:00"))

                # Check if post should be published now
                if post_date <= datetime.now(post_date.tzinfo):
                    try:
                        # Update post status to publish
                        await gql_client.query(
                            UPDATE_POST,
                            variables={
                                "id": str(post_id),
                                "status": "PUBLISH",
                            },
                        )
                        logger.info("Published scheduled post: %d", post_id)
                        published_count += 1
                    except Exception as e:
                        logger.error("Failed to publish post %d: %s", post_id, e)

            return published_count

        # Run async function
        published_count = asyncio.run(_publish())
        logger.info("Published %d scheduled posts", published_count)

        return {"success": True, "published_count": published_count}

    except Exception as exc:
        logger.error("Scheduled post publishing failed: %s", exc)
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3)
def bulk_update_posts(self, post_ids: list[int], updates: dict):
    """Background task for bulk post updates.

    Args:
        post_ids: List of post IDs to update
        updates: Dictionary of fields to update

    Returns:
        Number of successfully updated posts
    """
    try:
        logger.info("Bulk updating %d posts", len(post_ids))

        async def _update():
            success_count = 0
            for post_id in post_ids:
                try:
                    await gql_client.query(
                        UPDATE_POST,
                        variables={"id": str(post_id), **updates},
                    )
                    success_count += 1
                except Exception as e:
                    logger.error("Failed to update post %d: %s", post_id, e)

            return success_count

        success_count = asyncio.run(_update())
        logger.info("Bulk update completed: %d/%d posts updated", success_count, len(post_ids))

        return {"success": True, "updated_count": success_count}

    except Exception as exc:
        logger.error("Bulk update failed: %s", exc)
        raise self.retry(exc=exc)


@celery_app.task
def clear_cache_pattern(pattern: str):
    """Background task to invalidate cache by pattern.

    Args:
        pattern: Redis key pattern to invalidate
    """
    try:
        from articulate_mcp.cache import cache

        async def _clear():
            await cache.invalidate_pattern(pattern)

        asyncio.run(_clear())
        logger.info("Cache cleared for pattern: %s", pattern)
        return {"success": True, "pattern": pattern}

    except Exception as exc:
        logger.error("Cache clear failed for pattern %s: %s", pattern, exc)
        return {"success": False, "error": str(exc)}

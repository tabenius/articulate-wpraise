"""Media file migration for Next.js export."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

MediaStrategy = Literal["download", "keep_urls", "cdn", "next_image"]


class MediaMigrator:
    """Handle media file migration during Next.js export."""

    def __init__(
        self,
        media_list: list[dict[str, Any]],
        output_dir: Path,
        strategy: MediaStrategy = "download",
    ):
        """Initialize media migrator.

        Args:
            media_list: List of media items from WordPress
            output_dir: Next.js project output directory
            strategy: Media handling strategy
        """
        self.media_list = media_list
        self.output_dir = output_dir
        self.strategy = strategy
        self.media_dir = output_dir / "public" / "media"
        self.url_map: dict[str, str] = {}  # Original URL -> New URL mapping

    async def migrate(self) -> dict[str, Any]:
        """Migrate media files based on strategy.

        Returns:
            Migration result with stats and URL mappings
        """
        if self.strategy == "keep_urls":
            return self._keep_urls()
        elif self.strategy in ["download", "next_image"]:
            return await self._download_media()
        elif self.strategy == "cdn":
            return await self._upload_to_cdn()
        else:
            return {"error": f"Unknown media strategy: {self.strategy}"}

    def _keep_urls(self) -> dict[str, Any]:
        """Keep original WordPress URLs (no migration)."""
        # Just create URL mapping with original URLs
        for media in self.media_list:
            original_url = media.get("sourceUrl")
            if original_url:
                self.url_map[original_url] = original_url

        return {
            "success": True,
            "strategy": "keep_urls",
            "files_migrated": 0,
            "url_map": self.url_map,
            "message": "Keeping original WordPress URLs",
        }

    async def _download_media(self) -> dict[str, Any]:
        """Download media files to Next.js public folder."""
        self.media_dir.mkdir(parents=True, exist_ok=True)

        downloaded = 0
        failed = 0
        total_size = 0

        # Download files concurrently (limit to 5 at a time)
        semaphore = asyncio.Semaphore(5)

        async def download_file(media: dict[str, Any]) -> tuple[bool, int]:
            async with semaphore:
                try:
                    source_url = media.get("sourceUrl")
                    if not source_url:
                        return False, 0

                    # Generate filename from URL or use hash
                    parsed_url = urlparse(source_url)
                    original_filename = Path(parsed_url.path).name

                    # Use hash to avoid filename collisions
                    url_hash = hashlib.md5(source_url.encode()).hexdigest()[:8]
                    file_ext = Path(original_filename).suffix
                    filename = f"{url_hash}{file_ext}"

                    local_path = self.media_dir / filename
                    new_url = f"/media/{filename}"

                    # Download file
                    async with httpx.AsyncClient() as client:
                        response = await client.get(source_url, timeout=30.0)
                        response.raise_for_status()

                        # Write to file
                        with open(local_path, "wb") as f:
                            f.write(response.content)

                        file_size = len(response.content)

                        # Store URL mapping
                        self.url_map[source_url] = new_url

                        logger.info(f"Downloaded: {filename} ({file_size} bytes)")
                        return True, file_size

                except Exception as e:
                    logger.error(f"Failed to download {media.get('sourceUrl')}: {e}")
                    return False, 0

        # Download all files
        tasks = [download_file(media) for media in self.media_list]
        results = await asyncio.gather(*tasks)

        for success, size in results:
            if success:
                downloaded += 1
                total_size += size
            else:
                failed += 1

        return {
            "success": True,
            "strategy": self.strategy,
            "files_migrated": downloaded,
            "files_failed": failed,
            "total_size_bytes": total_size,
            "url_map": self.url_map,
            "message": f"Downloaded {downloaded} files ({self._format_size(total_size)})",
        }

    async def _upload_to_cdn(self) -> dict[str, Any]:
        """Upload media to CDN (placeholder for future implementation)."""
        # This would integrate with Cloudflare Images, Vercel Blob, etc.
        # For now, just download locally
        logger.warning("CDN upload not implemented, falling back to download")
        return await self._download_media()

    def update_content_urls(self, content: str) -> str:
        """Update media URLs in content.

        Args:
            content: HTML or markdown content

        Returns:
            Content with updated media URLs
        """
        updated_content = content

        for old_url, new_url in self.url_map.items():
            updated_content = updated_content.replace(old_url, new_url)

        return updated_content

    def generate_next_image_config(self) -> dict[str, Any]:
        """Generate Next.js image configuration."""
        if self.strategy != "next_image":
            return {}

        # Extract domains from media URLs
        domains = set()
        for media in self.media_list:
            source_url = media.get("sourceUrl")
            if source_url:
                parsed = urlparse(source_url)
                if parsed.netloc:
                    domains.add(parsed.netloc)

        return {
            "images": {
                "domains": list(domains),
                "formats": ["image/avif", "image/webp"],
                "deviceSizes": [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
                "imageSizes": [16, 32, 48, 64, 96, 128, 256, 384],
            }
        }

    @staticmethod
    def _format_size(bytes: int) -> str:
        """Format bytes to human-readable size."""
        for unit in ["B", "KB", "MB", "GB"]:
            if bytes < 1024:
                return f"{bytes:.1f} {unit}"
            bytes /= 1024
        return f"{bytes:.1f} TB"


async def migrate_media_for_export(
    media_list: list[dict[str, Any]],
    output_dir: str | Path,
    strategy: MediaStrategy = "download",
) -> dict[str, Any]:
    """Migrate media files for Next.js export.

    Args:
        media_list: List of WordPress media items
        output_dir: Next.js project directory
        strategy: Media handling strategy

    Returns:
        Migration result with URL mappings
    """
    output_path = Path(output_dir) if isinstance(output_dir, str) else output_dir

    migrator = MediaMigrator(
        media_list=media_list,
        output_dir=output_path,
        strategy=strategy,
    )

    result = await migrator.migrate()

    # Store URL mapping for content updates
    result["url_map"] = migrator.url_map

    # Generate Next.js config if needed
    if strategy == "next_image":
        result["next_image_config"] = migrator.generate_next_image_config()

    return result

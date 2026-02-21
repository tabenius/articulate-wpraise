"""File upload endpoint."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


async def upload_file_endpoint(request):
    """Upload avatar or banner image with optional compression."""
    from wp_mcp.user_manager import UserManager
    from wp_mcp.image_compressor import ImageCompressor

    try:
        logger.info("Upload request received")
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return JSONResponse({"error": "Session required"}, status_code=401)

        user = await UserManager.get_user_from_session(session_id)
        if not user:
            return JSONResponse({"error": "Invalid session"}, status_code=401)

        # Get form data
        logger.info(f"Getting form data for user {user['id']}")
        form = await request.form()
        file = form.get("file")
        upload_type = form.get("type", "avatar")  # avatar or banner
        logger.info(f"Form data: file={'present' if file else 'missing'}, type={upload_type}")

        # Compression options (optional)
        compress = form.get("compress", "true").lower() == "true"  # Default: compress
        output_format = form.get("format")  # webp, avif, jpeg, png
        quality = form.get("quality")  # 1-100
        max_width = form.get("max_width")
        max_height = form.get("max_height")

        if not file:
            return JSONResponse({"error": "No file provided"}, status_code=400)

        # Validate file type
        allowed_extensions = {".jpg", ".jpeg", ".png", ".webp", ".avif"}
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in allowed_extensions:
            return JSONResponse(
                {"error": f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"},
                status_code=400
            )

        # Read file content
        content = await file.read()

        # Validate file size (max 10MB before compression)
        max_size = 10 * 1024 * 1024  # 10MB
        if len(content) > max_size:
            return JSONResponse(
                {"error": "File too large. Maximum size is 10MB"},
                status_code=400
            )

        compression_metadata = None

        # Compress image if requested
        if compress and ImageCompressor.is_available():
            try:
                # Parse numeric parameters
                quality_int = int(quality) if quality else None
                max_width_int = int(max_width) if max_width else None
                max_height_int = int(max_height) if max_height else None

                # Apply sane defaults based on upload type
                if not output_format:
                    output_format = "webp"  # Default to WebP

                if not quality_int:
                    quality_int = 85  # Default quality

                if upload_type == "avatar" and not max_width_int:
                    max_width_int = 512  # Max 512px for avatars

                if upload_type == "banner" and not max_width_int:
                    max_width_int = 2048  # Max 2048px for banners

                content, compression_metadata = ImageCompressor.compress_image(
                    content,
                    output_format=output_format,
                    quality=quality_int,
                    max_width=max_width_int,
                    max_height=max_height_int,
                    preserve_exif=False,  # Strip EXIF for privacy
                    auto_orient=True,
                )

                # Update file extension based on output format
                if output_format:
                    file_ext = f".{output_format.lower()}"

                logger.info(f"Image compressed: {compression_metadata}")

            except Exception as e:
                logger.warning(f"Compression failed, using original: {e}")
                # Continue with original file if compression fails

        # Validate final size
        if len(content) > 5 * 1024 * 1024:
            return JSONResponse(
                {"error": "File too large after compression. Maximum size is 5MB"},
                status_code=400
            )

        # Create uploads directory if it doesn't exist
        uploads_dir = Path(__file__).parent.parent.parent.parent / "uploads" / upload_type
        uploads_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        unique_filename = f"{user['id']}_{uuid.uuid4().hex}{file_ext}"
        file_path = uploads_dir / unique_filename

        # Save file
        with open(file_path, "wb") as f:
            f.write(content)

        # Return URL
        file_url = f"/uploads/{upload_type}/{unique_filename}"

        logger.info(f"File uploaded: {file_url} by user {user['id']}")

        response_data = {
            "success": True,
            "url": file_url,
            "filename": unique_filename,
            "size": len(content),
        }

        if compression_metadata:
            response_data["metadata"] = compression_metadata

        return JSONResponse(response_data)

    except ValueError as e:
        logger.warning(f"Upload validation error: {e}")
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error(f"File upload error: {e}", exc_info=True)
        return JSONResponse(
            {"error": "Upload failed", "details": str(e)},
            status_code=500
        )

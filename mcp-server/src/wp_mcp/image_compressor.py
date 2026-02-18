"""Image compression utilities using Pillow."""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Optional, Tuple

try:
    from PIL import Image, ImageOps
except ImportError:
    Image = None
    ImageOps = None

logger = logging.getLogger(__name__)


class ImageCompressor:
    """Compress and optimize images with various formats and settings."""

    # Sane defaults
    DEFAULT_QUALITY = 85
    DEFAULT_FORMAT = "webp"
    MAX_DIMENSION = 4096  # Prevent memory issues

    # Format-specific optimal settings
    FORMAT_DEFAULTS = {
        "webp": {"quality": 85, "method": 6},
        "avif": {"quality": 80},
        "jpeg": {"quality": 85, "optimize": True, "progressive": True},
        "png": {"optimize": True, "compress_level": 6},
    }

    @staticmethod
    def is_available() -> bool:
        """Check if Pillow is available."""
        return Image is not None

    @staticmethod
    def compress_image(
        image_data: bytes,
        output_format: Optional[str] = None,
        quality: Optional[int] = None,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None,
        preserve_exif: bool = True,
        auto_orient: bool = True,
    ) -> Tuple[bytes, dict]:
        """Compress an image with specified settings.

        Args:
            image_data: Raw image bytes
            output_format: Target format (webp, avif, jpeg, png). If None, keeps original
            quality: Quality setting (1-100). If None, uses format default
            max_width: Maximum width (resize if larger)
            max_height: Maximum height (resize if larger)
            preserve_exif: Keep EXIF metadata
            auto_orient: Auto-rotate based on EXIF orientation

        Returns:
            Tuple of (compressed_bytes, metadata_dict)

        Raises:
            ValueError: If image is invalid or settings are wrong
            RuntimeError: If compression fails
        """
        if not ImageCompressor.is_available():
            raise RuntimeError("Pillow is not installed")

        # Defensive: validate inputs
        if not image_data:
            raise ValueError("No image data provided")

        if output_format and output_format.lower() not in ["webp", "avif", "jpeg", "jpg", "png"]:
            raise ValueError(f"Unsupported format: {output_format}")

        if quality is not None and (quality < 1 or quality > 100):
            raise ValueError("Quality must be between 1 and 100")

        if max_width is not None and (max_width < 1 or max_width > ImageCompressor.MAX_DIMENSION):
            raise ValueError(f"max_width must be between 1 and {ImageCompressor.MAX_DIMENSION}")

        if max_height is not None and (max_height < 1 or max_height > ImageCompressor.MAX_DIMENSION):
            raise ValueError(f"max_height must be between 1 and {ImageCompressor.MAX_DIMENSION}")

        try:
            # Open image
            image = Image.open(io.BytesIO(image_data))
            original_format = image.format
            original_size = len(image_data)
            original_dimensions = image.size

            # Auto-orient based on EXIF
            if auto_orient:
                image = ImageOps.exif_transpose(image)

            # Convert format if needed
            target_format = (output_format or original_format or "PNG").upper()
            if target_format == "JPG":
                target_format = "JPEG"

            # Convert RGBA to RGB for JPEG
            if target_format == "JPEG" and image.mode in ("RGBA", "LA", "P"):
                # Create white background
                background = Image.new("RGB", image.size, (255, 255, 255))
                if image.mode == "P":
                    image = image.convert("RGBA")
                background.paste(image, mask=image.split()[-1] if image.mode == "RGBA" else None)
                image = background
            elif image.mode not in ("RGB", "RGBA", "L"):
                # Convert other modes to RGB
                image = image.convert("RGB")

            # Resize if needed
            if max_width or max_height:
                image = ImageCompressor._resize_image(image, max_width, max_height)

            # Get format-specific settings
            save_kwargs = ImageCompressor.FORMAT_DEFAULTS.get(
                target_format.lower(), {}
            ).copy()

            # Override quality if specified
            if quality is not None:
                save_kwargs["quality"] = quality

            # Preserve EXIF if requested and available
            if preserve_exif and hasattr(image, "info") and "exif" in image.info:
                save_kwargs["exif"] = image.info["exif"]

            # Compress image
            output = io.BytesIO()
            image.save(output, format=target_format, **save_kwargs)
            compressed_data = output.getvalue()

            # Calculate metrics
            compressed_size = len(compressed_data)
            compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0

            metadata = {
                "original_format": original_format,
                "output_format": target_format,
                "original_size": original_size,
                "compressed_size": compressed_size,
                "compression_ratio": round(compression_ratio, 2),
                "original_dimensions": original_dimensions,
                "output_dimensions": image.size,
                "quality": save_kwargs.get("quality"),
                "resized": original_dimensions != image.size,
            }

            logger.info(
                f"Compressed image: {original_format} -> {target_format}, "
                f"{original_size} -> {compressed_size} bytes ({compression_ratio:.1f}% reduction)"
            )

            return compressed_data, metadata

        except Exception as e:
            logger.error(f"Image compression failed: {e}")
            raise RuntimeError(f"Failed to compress image: {str(e)}")

    @staticmethod
    def _resize_image(
        image: Image.Image,
        max_width: Optional[int],
        max_height: Optional[int]
    ) -> Image.Image:
        """Resize image maintaining aspect ratio.

        Args:
            image: PIL Image object
            max_width: Maximum width
            max_height: Maximum height

        Returns:
            Resized PIL Image
        """
        width, height = image.size

        # Calculate new dimensions
        if max_width and max_height:
            # Fit within both constraints
            ratio = min(max_width / width, max_height / height)
        elif max_width:
            ratio = max_width / width
        elif max_height:
            ratio = max_height / height
        else:
            return image

        # Only resize if image is larger
        if ratio < 1:
            new_width = int(width * ratio)
            new_height = int(height * ratio)

            # Use high-quality resampling
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        return image

    @staticmethod
    def get_image_info(image_data: bytes) -> dict:
        """Get information about an image without modifying it.

        Args:
            image_data: Raw image bytes

        Returns:
            Dict with image metadata

        Raises:
            ValueError: If image is invalid
        """
        if not ImageCompressor.is_available():
            raise RuntimeError("Pillow is not installed")

        try:
            image = Image.open(io.BytesIO(image_data))

            return {
                "format": image.format,
                "mode": image.mode,
                "size": len(image_data),
                "dimensions": image.size,
                "width": image.size[0],
                "height": image.size[1],
                "has_transparency": image.mode in ("RGBA", "LA", "P"),
            }
        except Exception as e:
            raise ValueError(f"Invalid image: {str(e)}")

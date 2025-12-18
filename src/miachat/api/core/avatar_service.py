"""
Avatar Service for MinouChat

Handles character avatar image uploads with circular cropping and resizing.
Avatars are stored as PNG files in the character_avatars directory.

Security Features:
- File type validation (only image/* MIME types)
- File size limits (max 5MB)
- UUID-based filenames to prevent path traversal
- Image processing to ensure safe output format
"""

import os
import re
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from io import BytesIO
import uuid

from PIL import Image, ImageDraw, ImageOps
from fastapi import UploadFile, HTTPException

logger = logging.getLogger(__name__)

# Configuration
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
AVATAR_SIZE = 256  # Output size in pixels (256x256 for high DPI)
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
AVATAR_DIR = os.getenv("CHARACTER_AVATARS_DIR", "character_avatars")

# UUID validation regex
UUID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE
)


class AvatarError(Exception):
    """Base exception for avatar operations."""
    pass


class InvalidImageError(AvatarError):
    """Raised when the uploaded file is not a valid image."""
    pass


class FileTooLargeError(AvatarError):
    """Raised when the file exceeds the size limit."""
    pass


class AvatarService:
    """
    Service for managing character avatar images.

    Handles upload, processing, and storage of circular avatar images.
    All avatars are resized to a standard size and converted to PNG.
    """

    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize the AvatarService.

        Args:
            storage_dir: Directory to store avatar images.
                         Defaults to CHARACTER_AVATARS_DIR env var or 'character_avatars'.
        """
        self.storage_dir = Path(storage_dir or AVATAR_DIR)
        self.storage_dir.mkdir(exist_ok=True)
        logger.info(f"Avatar storage directory: {self.storage_dir}")

    def _validate_character_id(self, character_id: str) -> None:
        """Validate that a character ID is a valid UUID."""
        if not character_id or not UUID_PATTERN.match(character_id):
            raise ValueError(f"Invalid character ID format: {character_id[:50] if character_id else 'empty'}")

    def _get_avatar_path(self, character_id: str) -> Path:
        """Get the file path for a character's avatar."""
        self._validate_character_id(character_id)
        return self.storage_dir / f"{character_id}.png"

    async def upload_avatar(
        self,
        character_id: str,
        file: UploadFile,
        crop_data: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Upload and process an avatar image.

        Args:
            character_id: UUID of the character
            file: Uploaded file object
            crop_data: Optional crop coordinates {x, y, width, height} as percentages (0-1)

        Returns:
            Dictionary with upload result and avatar URL

        Raises:
            InvalidImageError: If the file is not a valid image
            FileTooLargeError: If the file exceeds the size limit
            ValueError: If character_id is invalid
        """
        self._validate_character_id(character_id)

        # Validate content type
        content_type = file.content_type or ""
        if content_type not in ALLOWED_MIME_TYPES:
            raise InvalidImageError(
                f"Invalid file type: {content_type}. "
                f"Allowed types: {', '.join(ALLOWED_MIME_TYPES)}"
            )

        # Read file content
        content = await file.read()

        # Validate file size
        if len(content) > MAX_FILE_SIZE:
            raise FileTooLargeError(
                f"File size ({len(content)} bytes) exceeds maximum "
                f"({MAX_FILE_SIZE} bytes / {MAX_FILE_SIZE // 1024 // 1024}MB)"
            )

        try:
            # Open and validate image
            image = Image.open(BytesIO(content))
            image.verify()  # Verify it's a valid image

            # Re-open for processing (verify() closes the file)
            image = Image.open(BytesIO(content))

            # Convert to RGB if necessary (for PNG transparency handling)
            if image.mode in ('RGBA', 'LA', 'P'):
                # Create white background
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            elif image.mode != 'RGB':
                image = image.convert('RGB')

            # Apply crop if provided
            if crop_data:
                image = self._apply_crop(image, crop_data)

            # Create circular avatar
            avatar = self._create_circular_avatar(image, AVATAR_SIZE)

            # Save as PNG
            avatar_path = self._get_avatar_path(character_id)
            avatar.save(avatar_path, "PNG", optimize=True)

            # Generate URL path (relative to static files)
            avatar_url = f"/avatars/{character_id}.png"

            logger.info(f"Avatar uploaded for character {character_id}: {avatar_path}")

            return {
                "success": True,
                "character_id": character_id,
                "avatar_url": avatar_url,
                "size": AVATAR_SIZE,
                "file_size": avatar_path.stat().st_size
            }

        except (IOError, OSError) as e:
            logger.error(f"Failed to process image for {character_id}: {e}")
            raise InvalidImageError(f"Failed to process image: {e}")

    def _apply_crop(self, image: Image.Image, crop_data: Dict[str, float]) -> Image.Image:
        """
        Apply crop coordinates to an image.

        Args:
            image: PIL Image to crop
            crop_data: Crop coordinates as percentages {x, y, width, height}

        Returns:
            Cropped PIL Image
        """
        width, height = image.size

        # Convert percentages to pixels
        x = int(crop_data.get('x', 0) * width)
        y = int(crop_data.get('y', 0) * height)
        crop_width = int(crop_data.get('width', 1) * width)
        crop_height = int(crop_data.get('height', 1) * height)

        # Ensure we have a square crop for circular avatar
        size = min(crop_width, crop_height)

        # Center the square in the crop area
        x += (crop_width - size) // 2
        y += (crop_height - size) // 2

        # Ensure bounds are valid
        x = max(0, min(x, width - size))
        y = max(0, min(y, height - size))

        return image.crop((x, y, x + size, y + size))

    def _create_circular_avatar(self, image: Image.Image, size: int) -> Image.Image:
        """
        Create a circular avatar from an image.

        Args:
            image: Source PIL Image
            size: Output size in pixels

        Returns:
            Circular avatar as RGBA PIL Image
        """
        # Resize to target size with high-quality resampling
        image = ImageOps.fit(image, (size, size), Image.Resampling.LANCZOS)

        # Create circular mask
        mask = Image.new('L', (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size - 1, size - 1), fill=255)

        # Apply mask to create circular image with transparency
        output = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        output.paste(image, (0, 0))
        output.putalpha(mask)

        return output

    def get_avatar_url(self, character_id: str) -> Optional[str]:
        """
        Get the URL for a character's avatar if it exists.

        Args:
            character_id: UUID of the character

        Returns:
            Avatar URL if exists, None otherwise
        """
        try:
            self._validate_character_id(character_id)
            avatar_path = self._get_avatar_path(character_id)

            if avatar_path.exists():
                return f"/avatars/{character_id}.png"
            return None

        except ValueError:
            return None

    def delete_avatar(self, character_id: str) -> bool:
        """
        Delete a character's avatar.

        Args:
            character_id: UUID of the character

        Returns:
            True if deleted, False if avatar did not exist
        """
        try:
            self._validate_character_id(character_id)
            avatar_path = self._get_avatar_path(character_id)

            if avatar_path.exists():
                avatar_path.unlink()
                logger.info(f"Deleted avatar for character {character_id}")
                return True

            return False

        except ValueError:
            return False
        except IOError as e:
            logger.error(f"Failed to delete avatar for {character_id}: {e}")
            return False


# Global avatar service instance
avatar_service = AvatarService()

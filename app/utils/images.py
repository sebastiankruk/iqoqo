# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>
#
# pylint: disable=no-member
import io
import logging
import os
import textwrap
from typing import Any

import imagehash
from PIL import Image, ImageDraw, ImageFont, ImageOps

# Safety threshold for decompression bombs.
# Set to 200MP to accommodate even the largest modern smartphone cameras
# (e.g. 200MP Samsung S23 Ultra). PIL default is 50MP.
# Note: optimize_and_save_image always thumbnails down to 1024x1024 after this check.
Image.MAX_IMAGE_PIXELS = 200_000_000

logger = logging.getLogger(__name__)


# Load known junk cover pHashes from environment for configurable rejection
# Use `imagehash.phash(Image.open("your_placeholder.jpg"))` locally to compute.


def _load_known_junk_phashes() -> set[imagehash.ImageHash]:
    """
    Load known junk cover pHashes from the environment.
    Format: IQOQO_KNOWN_JUNK_PHASHES="e1e1e1e1e1e1e1e1,ffffffff00000000,eea4985b94846fe8"
    """
    raw_value = os.getenv("IQOQO_KNOWN_JUNK_PHASHES", "")
    hashes: set[imagehash.ImageHash] = set()

    if not raw_value:
        return hashes

    for token in raw_value.split(","):
        hex_value = token.strip()
        if not hex_value:
            continue
        try:
            hashes.add(imagehash.hex_to_hash(hex_value))
        except (ValueError, TypeError) as exc:  # narrow failures to this token only
            logger.warning("Invalid junk pHash '%s' in IQOQO_KNOWN_JUNK_PHASHES: %s", hex_value, exc)

    return hashes


# Load once at module initialization
KNOWN_JUNK_PHASHES = _load_known_junk_phashes()


def is_valid_cover(image_bytes: bytes) -> bool:
    """Detects if the downloaded cover is a valid image or a known 'not available' placeholder."""
    if not image_bytes:
        return False

    # Heuristic 1: File size. Accept small images > 1KB to be compatible with tests
    if len(image_bytes) < 1000:
        logger.debug(f"Image rejected: File size too small ({len(image_bytes)} bytes).")
        return False

    try:
        # verify image integrity first
        with Image.open(io.BytesIO(image_bytes)) as img:
            img.verify()

        # Re-open to compute perceptual hash
        with Image.open(io.BytesIO(image_bytes)) as img:
            img_hash = imagehash.phash(img)
            if img_hash in KNOWN_JUNK_PHASHES:
                logger.debug(f"Image rejected: Matches known junk pHash ({img_hash}).")
                return False

        return True
    except (OSError, ValueError, SyntaxError, TypeError) as e:
        logger.warning(f"Image validation failed (likely non-image or corrupt payload): {e}")
        return False


def optimize_image_to_bytes(image_bytes: bytes) -> bytes:
    try:
        with Image.open(io.BytesIO(image_bytes)) as raw_img:
            transposed_img = ImageOps.exif_transpose(raw_img)
            out: Image.Image = transposed_img.convert("RGB")
            out.thumbnail((1024, 1024))
            buf = io.BytesIO()
            out.save(buf, format="JPEG", quality=85)
            return buf.getvalue()
    except (OSError, ValueError):
        logger.exception("Error optimizing image")
        raise


def optimize_and_save_image(image_bytes: bytes, filepath: str):
    """Converts image to JPEG, fixes EXIF, resizes to max 1024x1024."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as raw_img:
            # Fix rotation based on EXIF data before doing anything else
            transposed_img = ImageOps.exif_transpose(raw_img)
            out: Image.Image = transposed_img.convert("RGB")
            out.thumbnail((1024, 1024))
            out.save(filepath, "JPEG", quality=85)

        remote = os.environ.get("RCLONE_COVERS_REMOTE")
        if remote and "/covers/" in filepath:
            try:
                import subprocess

                from app.utils.rclone_utils import get_rclone_target

                filename = os.path.basename(filepath)
                target = get_rclone_target(remote, "covers", filename)
                subprocess.run(["rclone", "copyto", filepath, target], check=False)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning("Failed to push cover to rclone cache: %s", e)
    except (OSError, ValueError):
        logger.exception("Error optimizing image")
        raise


def add_text_overlay_bytes(
    image_bytes: bytes,
    title: str,
    author: str,
    branding: str = "iQoQo",
    font_path: str = "arial.ttf",
) -> bytes:
    try:
        with Image.open(io.BytesIO(image_bytes)) as raw_img:
            transposed_img = ImageOps.exif_transpose(raw_img)
            converted: Image.Image = transposed_img.convert("RGB")
            draw = ImageDraw.Draw(converted)
            width, height = converted.size

            max_text_width = int(width * 0.90)
            title_box = (height * 0.60, height * 0.75)
            author_box = (height * 0.80, height * 0.90)
            branding_box = (height * 0.95, height * 1.0)

            valid_font_path: str | None = font_path
            try:
                ImageFont.truetype(font_path, 10)
            except OSError:
                fallbacks = [
                    "Arial.ttf",
                    "/Library/Fonts/Arial.ttf",
                    "/System/Library/Fonts/Supplemental/Arial.ttf",
                    "DejaVuSans.ttf",
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                ]
                for fb in fallbacks:
                    try:
                        ImageFont.truetype(fb, 10)
                        valid_font_path = fb
                        break
                    except OSError:
                        continue
                else:
                    logger.warning(f"Font '{font_path}' not found. Using default.")
                    valid_font_path = None

            def draw_text_in_box(text, y_range, size_ratio):
                y_start, y_end = y_range
                box_height = y_end - y_start
                font_size = int(height * size_ratio)
                min_font_size = 10
                selected_font = None
                final_lines = []
                final_line_height = 0

                while font_size >= min_font_size:
                    if valid_font_path:
                        font = ImageFont.truetype(valid_font_path, font_size)
                    else:
                        font = ImageFont.load_default()
                        if font_size != int(height * size_ratio):
                            selected_font = font
                            break

                    avg_char_width = font.getlength("x") or 10
                    chars_per_line = int(max_text_width / avg_char_width)
                    chars_per_line = max(chars_per_line, 1)

                    lines = textwrap.wrap(text, width=chars_per_line)
                    bbox = font.getbbox("Ay")
                    line_height = (bbox[3] - bbox[1]) * 1.2
                    total_height = line_height * len(lines)

                    if total_height <= box_height:
                        selected_font = font
                        final_lines = lines
                        final_line_height = line_height
                        break
                    font_size -= 2

                if selected_font is None:
                    if valid_font_path:
                        selected_font = ImageFont.truetype(valid_font_path, min_font_size)
                    else:
                        selected_font = ImageFont.load_default()
                    avg_char_width = selected_font.getlength("x") or 10
                    chars_per_line = int(max_text_width / avg_char_width)
                    chars_per_line = max(chars_per_line, 1)
                    final_lines = textwrap.wrap(text, width=chars_per_line)
                    bbox = selected_font.getbbox("Ay")
                    final_line_height = (bbox[3] - bbox[1]) * 1.2

                total_text_height = final_line_height * len(final_lines)
                current_y = y_start + (box_height - total_text_height) / 2

                for line in final_lines:
                    line_bbox = draw.textbbox((0, 0), line, font=selected_font)
                    text_width = line_bbox[2] - line_bbox[0]
                    x = (width - text_width) / 2
                    draw.text(
                        (x, current_y),
                        line,
                        font=selected_font,
                        fill="white",
                        stroke_width=2,
                        stroke_fill="black",
                    )
                    current_y += final_line_height

            draw_text_in_box(title, title_box, 0.10)
            draw_text_in_box(author, author_box, 0.06)
            draw_text_in_box(branding, branding_box, 0.03)

            buf = io.BytesIO()
            converted.save(buf, format="JPEG", quality=85)
            return buf.getvalue()
    except (OSError, ValueError) as e:
        logger.error(f"Error adding text overlay: {e}")
        return image_bytes


def add_text_overlay(
    filepath: str,
    title: str,
    author: str,
    branding: str = "iQoQo",
    font_path: str = "arial.ttf",
):
    """Overlays title, author, and branding text onto an existing image."""
    try:
        with Image.open(filepath) as raw_img:
            # Fix EXIF orientation before overlaying text
            transposed_img = ImageOps.exif_transpose(raw_img)
            converted: Image.Image = transposed_img.convert("RGB")
            draw = ImageDraw.Draw(converted)
            width, height = converted.size

            # Define layout constants
            max_text_width = int(width * 0.90)  # Keep 5% margin on sides

            # Define bounding boxes (y_start, y_end) as ratios of height

            title_box = (height * 0.60, height * 0.75)
            # Author: 20%-10% of bottom -> 0.80 to 0.90
            author_box = (height * 0.80, height * 0.90)
            # Branding: bottom 5% -> 0.95 to 1.0
            branding_box = (height * 0.95, height * 1.0)

            # Resolve font path once
            valid_font_path: str | None = font_path
            try:
                ImageFont.truetype(font_path, 10)
            except OSError:
                fallbacks = [
                    "Arial.ttf",
                    "/Library/Fonts/Arial.ttf",
                    "/System/Library/Fonts/Supplemental/Arial.ttf",
                    "DejaVuSans.ttf",
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                ]
                for fb in fallbacks:
                    try:
                        ImageFont.truetype(fb, 10)
                        valid_font_path = fb
                        break
                    except OSError:
                        continue
                else:
                    logger.warning(f"Font '{font_path}' not found. Using default.")
                    valid_font_path = None

            def draw_text_in_box(text, y_range, size_ratio):
                y_start, y_end = y_range
                box_height = y_end - y_start

                font_size = int(height * size_ratio)
                min_font_size = 10

                selected_font = None
                final_lines = []
                final_line_height = 0

                # Iteratively shrink font until text fits in box_height
                while font_size >= min_font_size:
                    if valid_font_path:
                        font = ImageFont.truetype(valid_font_path, font_size)
                    else:
                        font = ImageFont.load_default()
                        # Default font doesn't scale, so break early if we are using it
                        if font_size != int(height * size_ratio):
                            selected_font = font
                            break

                    # Wrap text
                    avg_char_width = font.getlength("x") or 10
                    chars_per_line = int(max_text_width / avg_char_width)
                    chars_per_line = max(chars_per_line, 1)

                    lines = textwrap.wrap(text, width=chars_per_line)

                    # Calculate total height
                    bbox = font.getbbox("Ay")
                    line_height = (bbox[3] - bbox[1]) * 1.2
                    total_height = line_height * len(lines)

                    if total_height <= box_height:
                        selected_font = font
                        final_lines = lines
                        final_line_height = line_height
                        break

                    font_size -= 2

                if selected_font is None:
                    # Fallback: use min size or default
                    if valid_font_path:
                        selected_font = ImageFont.truetype(valid_font_path, min_font_size)
                    else:
                        selected_font = ImageFont.load_default()

                    # Re-wrap with this font
                    avg_char_width = selected_font.getlength("x") or 10
                    chars_per_line = int(max_text_width / avg_char_width)
                    chars_per_line = max(chars_per_line, 1)
                    final_lines = textwrap.wrap(text, width=chars_per_line)
                    bbox = selected_font.getbbox("Ay")
                    final_line_height = (bbox[3] - bbox[1]) * 1.2

                # Draw centered vertically in the box
                total_text_height = final_line_height * len(final_lines)
                current_y = y_start + (box_height - total_text_height) / 2

                for line in final_lines:
                    line_bbox = draw.textbbox((0, 0), line, font=selected_font)
                    text_width = line_bbox[2] - line_bbox[0]
                    x = (width - text_width) / 2

                    # Outline and text
                    draw.text(
                        (x, current_y),
                        line,
                        font=selected_font,
                        fill="white",
                        stroke_width=2,
                        stroke_fill="black",
                    )
                    current_y += final_line_height

            # Draw text elements
            draw_text_in_box(title, title_box, 0.10)
            draw_text_in_box(author, author_box, 0.06)
            draw_text_in_box(branding, branding_box, 0.03)

            converted.save(filepath, "JPEG", quality=85)
    except (OSError, ValueError) as e:
        logger.error(f"Error adding text overlay: {e}")


def save_upload_image(file, subfolder: str = "gallery", filename: str | None = None) -> str:
    """Saves an uploaded image file, optimizes it, and returns the public URL."""
    from werkzeug.utils import secure_filename

    from app.utils.covers import COVERS_DIR, GALLERY_DIR

    base_dir = COVERS_DIR if subfolder == "covers" else GALLERY_DIR
    raw_filename = filename or file.filename
    target_filename = secure_filename(raw_filename)

    if not target_filename:
        raise ValueError("Invalid filename")

    filepath = os.path.join(base_dir, target_filename)

    # Save and optimize.
    optimize_and_save_image(file.read(), filepath)

    # Return public URL
    return f"/static/{subfolder}/{target_filename}"


def validate_upload_file(file: Any, max_size_bytes: int = 10 * 1024 * 1024) -> str:
    """Validate an uploaded image file: extension, size, and PIL integrity check.

    Returns:
        The file extension (lowercase, e.g. 'jpg') if valid.

    Raises:
        ValueError: With a user-facing message if validation fails.
    """
    if not file or not file.filename:
        raise ValueError("No file provided")

    allowed_extensions = {"png", "jpg", "jpeg", "webp"}
    if "." not in file.filename or file.filename.rsplit(".", 1)[-1].lower() not in allowed_extensions:
        raise ValueError(f"Invalid file type. Allowed: {', '.join(sorted(allowed_extensions))}")

    file.seek(0, os.SEEK_END)
    actual_size = file.tell()
    file.seek(0)
    if actual_size > max_size_bytes:
        raise ValueError(f"File too large. Max size: {max_size_bytes // (1024 * 1024)}MB")

    try:
        with Image.open(file) as img:
            img.verify()
        file.seek(0)
    except Image.DecompressionBombError as exc:
        limit = Image.MAX_IMAGE_PIXELS or 200_000_000
        raise ValueError(
            f"Image is too large to validate safely. Please resize it below {limit // 1_000_000} megapixels and try again."
        ) from exc
    except (OSError, SyntaxError) as exc:
        raise ValueError("Invalid or corrupted image file") from exc

    return str(file.filename.rsplit(".", 1)[-1].lower())

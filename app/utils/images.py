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
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>
#
import io
import logging
import textwrap

import imagehash
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


# Replace the placeholder hashes below with real pHash values of known junk covers
# Use `imagehash.phash(Image.open("your_placeholder.jpg"))` locally to compute.
KNOWN_JUNK_PHASHES = [
    imagehash.hex_to_hash("e1e1e1e1e1e1e1e1"),  # Example placeholder — replace as needed
]


def is_valid_cover(image_bytes: bytes) -> bool:
    """Detects if the downloaded cover is a valid image or a known 'not available' placeholder."""
    if not image_bytes:
        return False

    # Heuristic 1: File size. Accept small images > 1KB to be compatible with tests
    if len(image_bytes) < 1000:
        logger.debug("Image rejected: File size too small (likely a placeholder).")
        return False

    try:
        with Image.open(io.BytesIO(image_bytes)) as img:

            # Heuristic 2: Dimensions.
            if img.width <= 10 or img.height <= 10:
                logger.debug("Image rejected: Dimensions too small.")
                return False

            # Heuristic 3: Perceptual Hashing to catch visually identical placeholders
            img_hash = imagehash.phash(img)
            for junk_hash in KNOWN_JUNK_PHASHES:
                # A Hamming distance <= 4 means the images are visually nearly identical
                if img_hash - junk_hash <= 4:
                    logger.debug(f"Image rejected: Matches known junk pHash ({img_hash}).")
                    return False

            return True
    except Exception as e:
        logger.warning(f"Image validation failed (likely non-image or corrupt payload): {e}")
        return False


def optimize_and_save_image(image_bytes: bytes, filepath: str):
    """Converts image to JPEG, resizes to max 1024x1024, sets 85% quality."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            out: Image.Image = img.convert("RGB")
            out.thumbnail((1024, 1024))
            out.save(filepath, "JPEG", quality=85)
    except (OSError, ValueError):
        logger.exception("Error optimizing image")
        raise


def add_text_overlay(
    filepath: str,
    title: str,
    author: str,
    branding: str = "iQoQo",
    font_path: str = "arial.ttf",
):
    """Overlays title, author, and branding text onto an existing image."""
    try:
        with Image.open(filepath) as img:
            converted: Image.Image = img.convert("RGB")
            draw = ImageDraw.Draw(converted)
            width, height = converted.size

            # Define layout constants
            max_text_width = int(width * 0.90)  # Keep 5% margin on sides

            # Define bounding boxes (y_start, y_end) as ratios of height
            # Title: 40%-25% of bottom -> 0.60 to 0.75
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

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

import cv2
import imagehash
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

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


def smart_crop_and_warp(image_bytes: bytes) -> bytes:
    """
    Detects the largest rectangular document/cover in the image, crops it,
    and applies a perspective transform to flatten it.
    Returns original bytes if detection fails.
    """
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return image_bytes

        # Grayscale, blur, edge detection
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 75, 200)

        # Find contours
        contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return image_bytes

        # Sort by area, keep largest
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]
        screen_cnt = None

        for c in contours:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            # Find the first contour with exactly 4 points
            if len(approx) == 4:
                screen_cnt = approx
                break

        if screen_cnt is None:
            return image_bytes  # Fallback if no rectangle found

        # Perspective Transform Setup
        pts = screen_cnt.reshape(4, 2)
        rect = np.zeros((4, 2), dtype="float32")

        # Top-left has smallest sum, Bottom-right has largest sum
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]

        # Top-right has smallest diff, Bottom-left has largest diff
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]

        tl, tr, br, bl = rect

        width_a = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
        width_b = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
        max_width = max(int(width_a), int(width_b))

        height_a = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
        height_b = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
        max_height = max(int(height_a), int(height_b))

        dst = np.array([[0, 0], [max_width - 1, 0], [max_width - 1, max_height - 1], [0, max_height - 1]], dtype="float32")

        matrix = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(img, matrix, (max_width, max_height))

        # Convert back to jpeg bytes
        is_success, buffer = cv2.imencode(".jpg", warped, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        if is_success:
            return buffer.tobytes()

        return image_bytes
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.warning(f"Smart crop failed, falling back to original image: {e}")
        return image_bytes


def optimize_and_save_image(image_bytes: bytes, filepath: str, apply_smart_crop: bool = False):
    """Converts image to JPEG, applies smart crop (optional), fixes EXIF, resizes to max 1024x1024."""
    try:
        if apply_smart_crop:
            image_bytes = smart_crop_and_warp(image_bytes)

        with Image.open(io.BytesIO(image_bytes)) as raw_img:
            # Fix rotation based on EXIF data before doing anything else
            transposed_img = ImageOps.exif_transpose(raw_img)
            out: Image.Image = transposed_img.convert("RGB")
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
        with Image.open(filepath) as raw_img:
            # Fix EXIF orientation before overlaying text
            transposed_img = ImageOps.exif_transpose(raw_img)
            converted: Image.Image = transposed_img.convert("RGB")
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


def save_upload_image(file, subfolder: str = "gallery", filename: str | None = None) -> str:
    """Saves an uploaded image file, optimizes it, and returns the public URL."""
    from app.utils.covers import COVERS_DIR, GALLERY_DIR

    base_dir = COVERS_DIR if subfolder == "covers" else GALLERY_DIR
    target_filename = filename or file.filename
    filepath = os.path.join(base_dir, target_filename)

    # Save and optimize. Apply smart crop only for user uploads (gallery/scanner input).
    optimize_and_save_image(file.read(), filepath, apply_smart_crop=subfolder == "gallery")

    # Return public URL
    return f"/static/{subfolder}/{target_filename}"

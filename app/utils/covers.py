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
import hashlib
import io
import logging
import os
import threading
from datetime import UTC, datetime

import requests
from PIL import Image, ImageDraw, ImageFont

from app.config import Config
from app.db import db
from app.db.models import Manifestation
from app.utils.images import is_valid_cover, optimize_and_save_image
from app.utils.llm_covers import fetch_llm_cover

logger = logging.getLogger(__name__)

COVERS_DIR = os.path.join(Config.BASE_DIR, "app", "static", "covers")
RAW_DIR = os.path.join(Config.BASE_DIR, "app", "static", "uploads", "raw_covers")

os.makedirs(COVERS_DIR, exist_ok=True)
os.makedirs(RAW_DIR, exist_ok=True)

# Size limits for externally fetched covers
MAX_COVER_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
MIN_COVER_FILE_SIZE = 1000  # ~1 KB


def add_source_badge(filepath: str, source: str):
    """Draws a small source indicator in the bottom right corner."""
    if not filepath or not os.path.exists(filepath):
        return

    # Dictionary mapping for source indicators (Label, Background Color)
    BADGE_MAP = {
        "user_photo": ("U", "blue"),
        "api_openlibrary": ("D", "gray"),  # Download
        "api_google_books": ("D", "gray"),
        "llm_gemini": ("G", "purple"),
        "llm_openai": ("O", "green"),
        "llm_local_stable_diffusion": ("L", "orange"),
        "fallback_pil": ("S", "black"),  # Simple
    }

    text, color = BADGE_MAP.get(source, ("?", "black"))

    try:
        with Image.open(filepath) as img:
            out: Image.Image = img.convert("RGB")

            d = ImageDraw.Draw(out)
            w, h = out.size

            # Draw a 30x30 rectangle in bottom right
            box_size = 30
            d.rectangle([w - box_size, h - box_size, w, h], fill=color)

            # Draw the letter inside the box
            font = ImageFont.load_default()
            # Adjust position for default font
            d.text((w - 20, h - 22), text, fill="white", font=font)

            out.save(filepath)
    except (OSError, ValueError, AttributeError) as e:
        logger.error(f"Failed to apply badge overlay: {e}")


def generate_fallback_cover(isbn: str, title: str, author: str) -> str | None:
    """Tier 5: Generate a deterministic cover using Pillow."""
    filename = f"{isbn}_generated.jpg"
    filepath = os.path.join(COVERS_DIR, filename)

    # Deterministic background color based on ISBN hash
    hash_obj = hashlib.md5(isbn.encode())
    bg_color = f"#{hash_obj.hexdigest()[:6]}"

    try:
        img = Image.new("RGB", (400, 600), color=bg_color)
        d = ImageDraw.Draw(img)

        # Use default font, in production load a TTF
        # font = ImageFont.truetype("arial.ttf", 24)
        font = ImageFont.load_default()

        # Simple text wrapping logic could be added here
        d.text((20, 50), title[:100], fill=(255, 255, 255), font=font)
        d.text((20, 550), author[:50], fill=(220, 220, 220), font=font)

        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format="JPEG")
        optimize_and_save_image(img_byte_arr.getvalue(), filepath)
        return f"{Config.COVERS_BASE_URL}/{filename}"
    except (OSError, ValueError) as e:
        logger.error(f"Fallback generation failed: {e}")
        return None


def fetch_external_api_cover(isbn: str) -> tuple[str, str] | None:
    """Tier 2: Try OpenLibrary then Google Books. Returns (path, source) tuple on success.

    This implementation streams responses with a maximum in-memory cap to avoid
    memory bloat from malicious or misconfigured endpoints. It delegates image
    integrity and placeholder detection to is_valid_cover().
    """

    def process_response(response, source_prefix: str, source_name: str) -> tuple[str, str] | None:
        """Helper to safely stream, size-cap, and validate external cover images."""
        downloaded = bytearray()

        for chunk in response.iter_content(chunk_size=8192):
            if not chunk:
                continue
            downloaded.extend(chunk)
            if len(downloaded) > MAX_COVER_FILE_SIZE:
                logger.warning(f"Cover payload from {source_name} exceeded {MAX_COVER_FILE_SIZE} bytes. Aborting.")
                return None

        if len(downloaded) < MIN_COVER_FILE_SIZE:
            # Too small to be a valid cover
            return None

        content = bytes(downloaded)

        # Validate the image payload (includes pHash/junk detection in is_valid_cover)
        if not is_valid_cover(content):
            return None

        filename = f"{isbn}_{source_prefix}.jpg"
        filepath = os.path.join(COVERS_DIR, filename)
        optimize_and_save_image(content, filepath)
        return f"{Config.COVERS_BASE_URL}/{filename}", source_name

    # 1. Open Library (Direct)
    ol_url = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"
    try:
        response = requests.get(ol_url, stream=True, timeout=5)
        if response.status_code == 200:
            # Fast-fail using header when present and trustworthy
            try:
                header_len_raw = response.headers.get("content-length")
                if header_len_raw is not None:
                    header_len = int(header_len_raw)
                    if 0 < header_len < MIN_COVER_FILE_SIZE:
                        return None
            except (TypeError, ValueError):
                pass

            res = process_response(response, "ol", "api_openlibrary")
            if res:
                return res
    except (requests.RequestException, OSError, ValueError, TypeError):
        pass

    # 2. Google Books (Search -> Thumbnail)
    gb_search = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
    try:
        gb_data = requests.get(gb_search, timeout=5).json()
        if "items" in gb_data:
            thumb = gb_data["items"][0]["volumeInfo"].get("imageLinks", {}).get("thumbnail")
            if thumb:
                # Get higher res
                thumb = thumb.replace("zoom=1", "zoom=0").replace("http:", "https:")
                img_res = requests.get(thumb, stream=True, timeout=10)
                if img_res.status_code == 200:
                    processed = process_response(img_res, "gb", "api_google_books")
                    if processed:
                        return processed
    except (requests.RequestException, OSError, ValueError, TypeError, KeyError, IndexError):
        pass

    return None


def process_fast_cover(manifestation: Manifestation, isbn: str) -> bool:
    """Runs real-time (fast) lookups. Returns True if a cover was found."""
    result = fetch_external_api_cover(isbn)
    if result:
        local_path, source = result
        manifestation.cover_url = local_path
        # Force SQLAlchemy to detect change in JSON field
        manifestation.update_meta(cover_source=source, cover_status="ready")
        return True
    return False


def process_cover_pipeline(
    manifestation_id: int,
    isbn: str,
    title: str,
    author: str,
    llm_permissions: dict[str, bool],
    user_id: str = "system",
    user_image_path: str | None = None,
    description: str = "",
    genre: str = "",
):
    """
    The single cover-generation pipeline (Chain of Responsibility).

    Tiers:
      1. User photo (if provided)
      2. External APIs (OpenLibrary, Google Books)
      3/4. LLM generation (local SD → Gemini → OpenAI)

    If all tiers fail the existing cover_url is left unchanged so the
    frontend can show its book-icon placeholder rather than an empty or
    low-quality fallback image.  cover_status is set to ``"failed"``.

    Can be invoked directly (e.g. from a CLI script) or via
    ``start_cover_processing`` which fires it in a background thread.
    """
    from flask import current_app, has_app_context

    if has_app_context():
        app = current_app
    else:
        from app import create_app

        app = create_app()

    with app.app_context():
        manifestation = db.session.get(Manifestation, manifestation_id)
        if not manifestation:
            return

        local_cover_url: str | None = None
        source: str | None = None

        # Tier 1: User Photo
        if user_image_path and os.path.exists(user_image_path):
            try:
                filename = f"{isbn}_user.jpg"
                dest_path = os.path.join(COVERS_DIR, filename)

                # Normalize/compress the user-provided image before storing it
                with open(user_image_path, "rb") as upload_file:
                    image_bytes = upload_file.read()
                optimize_and_save_image(image_bytes, dest_path)
                # Remove the temporary upload file once it has been processed
                os.remove(user_image_path)

                local_cover_url = f"{Config.COVERS_BASE_URL}/{filename}"
                source = "user_photo"
            except (OSError, ValueError) as e:
                logger.error(f"Failed to process user image: {e}")
                manifestation.update_meta(cover_status="failed")
                db.session.commit()
                return

        # Tier 2: External APIs
        if not local_cover_url:
            result = fetch_external_api_cover(isbn)
            if result:
                local_cover_url, source = result

        # Tier 3/4: LLM Generation
        # Two-layer guard: ALLOW_LLM must be True in Config (operator opt-in)
        # AND the calling user must hold the llm_generate:cover permission
        # (passed in as allow_llm from the API layer).  Both must be satisfied
        # so that neither a misconfigured .env nor a rogue role alone can
        # trigger paid cloud API calls.
        allow_generate_cover = Config.ALLOW_LLM and llm_permissions.get("allow_generate_cover", False)
        if not local_cover_url and allow_generate_cover:
            result = fetch_llm_cover(
                isbn, title, author, user_id, description, genre, allow_cloud_llm=llm_permissions.get("allow_cloud_llm", False)
            )
            if result:
                local_cover_url, source = result

        # Update DB
        # Force SQLAlchemy to detect change in JSON field
        from typing import Any

        updates: dict[str, Any] = {"cover_status_updated_at": datetime.now(UTC).isoformat()}

        if local_cover_url:
            abs_path = os.path.join(COVERS_DIR, os.path.basename(local_cover_url))
            add_source_badge(abs_path, source or "")
            manifestation.cover_url = local_cover_url
            updates["cover_source"] = source
            updates["cover_status"] = "ready"
            logger.info("Cover processed for %s: %s", isbn, source)
        else:
            # All tiers failed — leave cover_url as-is so the frontend shows
            # a book-icon placeholder rather than an empty or text-only image.
            updates["cover_status"] = "failed"
            logger.warning("Cover generation failed for %s: no cover produced, leaving existing", isbn)

        manifestation.update_meta(**updates)
        db.session.commit()


def start_cover_processing(
    manifestation_id: int,
    isbn: str,
    title: str,
    author: str,
    user_id: str = "system",
    llm_permissions: dict[str, bool] | None = None,
    user_image_path: str | None = None,
    description: str = "",
    genre: str = "",
) -> None:
    """Fires off the background thread."""
    thread = threading.Thread(
        target=process_cover_pipeline,
        kwargs={
            "manifestation_id": manifestation_id,
            "isbn": isbn,
            "title": title,
            "author": author,
            "user_id": user_id,
            "llm_permissions": llm_permissions,
            "user_image_path": user_image_path,
            "description": description,
            "genre": genre,
        },
    )
    thread.start()


def rebind_orphaned_covers() -> int:
    """
    Scans the covers directory for images that match books (Manifestations)
    with missing covers, and links them.

    Returns:
        int: The number of covers rebound.
    """
    orphans_rebound = 0

    # 1. Get books without covers
    # Note: This query assumes we are in an app context
    books_missing_covers = Manifestation.query.filter((Manifestation.cover_url.is_(None)) | (Manifestation.cover_url == "")).all()

    if not books_missing_covers:
        logger.info("No books found missing covers.")
        return 0

    # 2. List files
    try:
        files = os.listdir(COVERS_DIR)
    except OSError as e:
        logger.error(f"Failed to list covers directory: {e}")
        return 0

    # 3. Match
    for book in books_missing_covers:
        if not book.isbn13:
            continue

        # Find files starting with ISBN
        candidates = [f for f in files if f.startswith(book.isbn13) and f.lower().endswith((".jpg", ".jpeg", ".png"))]

        if candidates:
            # Sort candidates to pick the "best" one if multiple exist
            # Priority: user > api > generated
            def sort_key(f):
                if "_user" in f:
                    return 0
                if "_ol" in f or "_gb" in f:
                    return 1
                return 2

            candidates.sort(key=sort_key)
            best_match = candidates[0]

            # Update DB
            book.cover_url = f"{Config.COVERS_BASE_URL}/{best_match}"

            # Update meta status
            updates = {"cover_status": "ready"}
            if not (book.meta and "cover_source" in book.meta):
                updates["cover_source"] = "rebind"
            book.update_meta(**updates)

            orphans_rebound += 1
            logger.info(f"Rebound cover for ISBN {book.isbn13}: {best_match}")

    if orphans_rebound > 0:
        db.session.commit()

    return orphans_rebound

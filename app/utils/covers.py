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
import atexit
import hashlib
import io
import logging
import os
from concurrent.futures import ThreadPoolExecutor
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
GALLERY_DIR = os.path.join(Config.BASE_DIR, "app", "static", "gallery")

os.makedirs(COVERS_DIR, exist_ok=True)
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(GALLERY_DIR, exist_ok=True)

# Size limits for externally fetched covers
MAX_COVER_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
MIN_COVER_FILE_SIZE = 1000  # ~1 KB

# Managed thread pool for offloaded cover generation operations
cover_executor = ThreadPoolExecutor(max_workers=4)
atexit.register(cover_executor.shutdown, wait=False)


def add_source_badge(filepath: str, source: str):
    """Draws a small source indicator in the bottom right corner."""
    if not filepath or not os.path.exists(filepath):
        return

    # Dictionary mapping for source indicators (Label, Background Color)
    BADGE_MAP = {
        "user_photo": ("U", "blue"),
        "api_openlibrary": ("D", "gray"),  # Download
        "api_google_books": ("D", "gray"),
        "api_direct_download": ("C", "teal"),  # CD/Audio direct download
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


def generate_fallback_cover(identifier: str, title: str, author: str) -> str | None:
    """Tier 5: Generate a deterministic cover using Pillow."""
    filename = f"{identifier}_generated.jpg"
    filepath = os.path.join(COVERS_DIR, filename)

    # Deterministic background color based on identifier hash
    hash_obj = hashlib.md5(identifier.encode())
    bg_color = f"#{hash_obj.hexdigest()[:6]}"

    try:
        img = Image.new("RGB", (400, 600), color=bg_color)
        d = ImageDraw.Draw(img)

        font = ImageFont.load_default()

        # Simple text wrapping logic could be added here
        d.text((20, 50), title[:100], fill=(255, 255, 255), font=font)
        d.text((20, 550), author[:50], fill=(220, 220, 220), font=font)

        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format="JPEG")
        optimize_and_save_image(img_byte_arr.getvalue(), filepath)
        return f"/static/covers/{filename}"
    except (OSError, ValueError) as e:
        logger.error(f"Fallback generation failed: {e}")
        return None


def download_direct_url(identifier: str, url: str, source_name: str) -> tuple[str, str] | None:
    """Securely downloads a direct image URL to the local filesystem."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, stream=True, timeout=10, headers=headers)
        if response.status_code == 200:
            downloaded = bytearray()
            for chunk in response.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                downloaded.extend(chunk)
                if len(downloaded) > MAX_COVER_FILE_SIZE:
                    logger.warning(f"Direct URL {url} exceeded limits. Aborting.")
                    return None

            if len(downloaded) < MIN_COVER_FILE_SIZE:
                return None

            content = bytes(downloaded)
            if not is_valid_cover(content):
                return None

            filename = f"{identifier}_ext.jpg"
            filepath = os.path.join(COVERS_DIR, filename)
            optimize_and_save_image(content, filepath)
            return f"/static/covers/{filename}", source_name
    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Error fetching direct URL {url}: {e}")

    return None


def fetch_external_api_cover(identifier: str, isbn: str | None = None) -> tuple[str, str] | None:
    """Tier 2 fallback: Try OpenLibrary then Google Books. Returns (path, source) tuple on success."""
    isbn_for_lookup = isbn or identifier

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
            return None

        content = bytes(downloaded)
        if not is_valid_cover(content):
            return None

        filename = f"{identifier}_{source_prefix}.jpg"
        filepath = os.path.join(COVERS_DIR, filename)
        optimize_and_save_image(content, filepath)
        return f"/static/covers/{filename}", source_name

    # 1. Open Library (Direct)
    ol_url = f"https://covers.openlibrary.org/b/isbn/{isbn_for_lookup}-L.jpg"
    try:
        response = requests.get(ol_url, stream=True, timeout=5)
        if response.status_code == 200:
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
    gb_search = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn_for_lookup}"
    try:
        gb_data = requests.get(gb_search, timeout=5).json()
        if "items" in gb_data:
            thumb = gb_data["items"][0]["volumeInfo"].get("imageLinks", {}).get("thumbnail")
            if thumb:
                thumb = thumb.replace("zoom=1", "zoom=0").replace("http:", "https:")
                img_res = requests.get(thumb, stream=True, timeout=10)
                if img_res.status_code == 200:
                    processed = process_response(img_res, "gb", "api_google_books")
                    if processed:
                        return processed
    except (requests.RequestException, OSError, ValueError, TypeError, KeyError, IndexError):
        pass

    return None


def process_fast_cover(manifestation: Manifestation, identifier: str) -> bool:
    """Runs real-time (fast) lookups. Returns True if a cover was found."""
    result = fetch_external_api_cover(identifier)
    if result:
        local_path, source = result
        manifestation.cover_url = local_path
        manifestation.update_meta(cover_source=source, cover_status="ready")
        return True
    return False


def process_cover_pipeline(
    manifestation_id: int,
    identifier: str,
    title: str,
    author: str,
    llm_permissions: dict[str, bool],
    user_id: str = "system",
    user_image_path: str | None = None,
    description: str = "",
    genre: str = "",
    _tag: str = "",  # pylint: disable=unused-argument
):
    """
    The single cover-generation pipeline.
    Tiers:
      1. User photo
      1.5 Direct URL Download (intercepts external hotlinks from MusicBrainz/Discogs)
      2. External APIs (OpenLibrary, Google Books)
      3/4. LLM generation
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
                filename = f"{identifier}_user.jpg"
                dest_path = os.path.join(COVERS_DIR, filename)

                with open(user_image_path, "rb") as upload_file:
                    image_bytes = upload_file.read()
                optimize_and_save_image(image_bytes, dest_path)
                os.remove(user_image_path)

                local_cover_url = f"/static/covers/{filename}"
                source = "user_photo"
            except (OSError, ValueError) as e:
                logger.error(f"Failed to process user image: {e}")
                manifestation.update_meta(cover_status="failed")
                db.session.commit()
                return

        # Tier 1.5 & Tier 2: Direct Hotlinks & External APIs
        if not local_cover_url:
            existing_url = manifestation.meta.get("cover_url") if manifestation.meta else None

            # Intercept existing external URLs and download them locally
            if existing_url and str(existing_url).startswith("http"):
                result = download_direct_url(identifier, existing_url, "api_direct_download")
                if result:
                    local_cover_url, source = result

            # Fallback to book API fetchers
            if not local_cover_url:
                result = fetch_external_api_cover(identifier, isbn=manifestation.isbn13)
                if result:
                    local_cover_url, source = result

        # Tier 3/4: LLM Generation
        allow_generate_cover = Config.ALLOW_LLM and llm_permissions.get("allow_generate_cover", False)
        if not local_cover_url and allow_generate_cover:
            result = fetch_llm_cover(
                identifier, title, author, user_id, description, genre, allow_cloud_llm=llm_permissions.get("allow_cloud_llm", False)
            )
            if result:
                local_cover_url, source = result

        # Update DB
        from typing import Any

        updates: dict[str, Any] = {"cover_status_updated_at": datetime.now(UTC).isoformat()}

        if local_cover_url:
            abs_path = os.path.join(COVERS_DIR, os.path.basename(local_cover_url))
            add_source_badge(abs_path, source or "")
            manifestation.cover_url = local_cover_url
            updates["cover_source"] = source
            updates["cover_status"] = "ready"
            logger.info("Cover processed for %s: %s", identifier, source)
        else:
            updates["cover_status"] = "failed"
            logger.warning("Cover generation failed for %s", identifier)

        manifestation.update_meta(**updates)
        db.session.commit()


def start_cover_processing(
    manifestation_id: int,
    identifier: str,
    title: str,
    author: str,
    user_id: str = "system",
    llm_permissions: dict[str, bool] | None = None,
    user_image_path: str | None = None,
    description: str = "",
    genre: str = "",
) -> None:
    """Fires off the background executor."""
    cover_executor.submit(
        process_cover_pipeline,
        manifestation_id,
        identifier,
        title,
        author,
        llm_permissions or {},
        user_id,
        user_image_path,
        description,
        genre,
    )


def rebind_orphaned_covers() -> int:
    """Scans the covers directory for images that match books with missing covers."""
    orphans_rebound = 0
    books_missing_covers = Manifestation.query.filter((Manifestation.cover_url.is_(None)) | (Manifestation.cover_url == "")).all()

    if not books_missing_covers:
        return 0

    try:
        files = os.listdir(COVERS_DIR)
    except OSError as e:
        logger.error(f"Failed to list covers directory: {e}")
        return 0

    for book in books_missing_covers:
        identifier = book.isbn13 or book.ean or book.upc
        if not identifier:
            continue

        candidates = [f for f in files if f.startswith(identifier) and f.lower().endswith((".jpg", ".jpeg", ".png"))]

        if candidates:

            def sort_key(f):
                if "_user" in f:
                    return 0
                if "_ext" in f:
                    return 1
                if "_ol" in f or "_gb" in f:
                    return 2
                return 3

            candidates.sort(key=sort_key)
            best_match = candidates[0]

            book.cover_url = f"/static/covers/{best_match}"

            updates = {"cover_status": "ready"}
            if not (book.meta and "cover_source" in book.meta):
                updates["cover_source"] = "rebind"
            book.update_meta(**updates)

            orphans_rebound += 1

    if orphans_rebound > 0:
        db.session.commit()

    return orphans_rebound

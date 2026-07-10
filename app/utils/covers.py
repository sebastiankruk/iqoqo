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
from datetime import UTC, datetime, timedelta

import requests
from PIL import Image, ImageDraw, ImageFont

from app.config import Config
from app.core.tasks import submit_task
from app.db import db
from app.db.models import Manifestation
from app.utils.images import is_valid_cover, optimize_and_save_image
from app.utils.isbn import canonicalize_isbn
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


def add_source_badge(filepath: str, source: str):
    """Draws a small source indicator in the bottom right corner."""
    if not filepath or not os.path.exists(filepath):
        return

    # Dictionary mapping for source indicators (Label, Background Color)
    BADGE_MAP = {
        "user_photo": ("U", "blue"),
        "api_openlibrary": ("D", "gray"),  # Download
        "api_google_books": ("D", "gray"),
        "api_allegro": ("A", "orange"),
        "api_direct_download": ("C", "teal"),  # CD/Audio direct download
        "api_igdb": ("I", "purple"),  # IGDB Cover
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


def generate_fallback_cover(identifier: str, title: str, author: str) -> tuple[str, str] | None:
    """Tier 5: Generate a deterministic, beautiful cover using Pillow.

    Phase 4 (0.7.8): Upgraded from a flat solid-colour background to a
    procedural vertical gradient whose colours are derived from a MD5 hash of
    the ``identifier`` and ``title``.  This guarantees that the same book always
    gets the same colour palette, while different books look visually distinct.
    Long titles are word-wrapped and rendered with a drop-shadow for contrast.
    """
    import textwrap  # stdlib – import locally to avoid circular-import risks

    filename = f"{identifier}_generated.jpg"
    filepath = os.path.join(COVERS_DIR, filename)

    try:
        # 1. Deterministic procedural gradient derived from title + identifier
        hash_str = f"{identifier}_{title}"
        hash_val = int(hashlib.md5(hash_str.encode("utf-8")).hexdigest(), 16)

        # Keep colours slightly muted/darker for sufficient contrast with white text
        color1 = (hash_val % 200, (hash_val // 256) % 200, (hash_val // 65536) % 200)
        color2 = (
            (hash_val // 16_777_216) % 150,
            (hash_val // 4_294_967_296) % 150,
            100,
        )

        width, height = 600, 900
        img = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(img)

        # Draw smooth vertical gradient scanline-by-scanline
        for y in range(height):
            r = int(color1[0] + (color2[0] - color1[0]) * y / height)
            g = int(color1[1] + (color2[1] - color1[1]) * y / height)
            b = int(color1[2] + (color2[2] - color1[2]) * y / height)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # 2. Configure typography – prefer a TTF font, fall back to default
        try:
            font_title: ImageFont.FreeTypeFont | ImageFont.ImageFont = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48
            )
            font_author: ImageFont.FreeTypeFont | ImageFont.ImageFont = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36
            )
        except OSError:
            font_title = ImageFont.load_default()
            font_author = ImageFont.load_default()

        # 3. Word-wrap the title so it stays within the image margins
        margin = 40
        offset_y = 80
        wrapped_title = textwrap.fill(title, width=18)

        # 4. Render each wrapped line with a drop-shadow for readability
        for line in wrapped_title.split("\n"):
            # Drop shadow
            draw.text((margin + 3, offset_y + 3), line, font=font_title, fill="black")
            # Foreground text
            draw.text((margin, offset_y), line, font=font_title, fill="white")

            # Advance Y by the actual glyph height, or fall back to a safe default
            bbox = font_title.getbbox(line) if hasattr(font_title, "getbbox") else (0, 0, 0, 50)
            offset_y += int(bbox[3] - bbox[1] + 15) if bbox else 65

        # 5. Render author near the bottom of the image
        if author:
            author_y = height - 120
            draw.text((margin + 2, author_y + 2), author, font=font_author, fill="black")
            draw.text((margin, author_y), author, font=font_author, fill="#E2E8F0")

        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format="JPEG", quality=85)
        optimize_and_save_image(img_byte_arr.getvalue(), filepath)
        return f"{Config.COVERS_BASE_URL}/{filename}", "fallback_pil"
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"Fallback generation failed: {e}")
        return None


def download_direct_url(identifier: str, url: str, source_name: str, suffix: str = "ext") -> tuple[str, str] | None:
    """Securely downloads a direct image URL to the local filesystem."""
    res = None
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        with requests.get(url, stream=True, timeout=10, headers=headers) as response:
            if response.status_code == 200:
                # Fast fail on known bad sizes if header is present
                try:
                    header_len_raw = response.headers.get("content-length")
                    if header_len_raw is not None:
                        header_len = int(header_len_raw)
                        if 0 < header_len < MIN_COVER_FILE_SIZE:
                            return None
                except (TypeError, ValueError):
                    pass

                logger.debug(f"Downloading cover for {identifier} from URL {url}.")

                downloaded = bytearray()
                for chunk in response.iter_content(chunk_size=8192):
                    if not chunk:
                        continue
                    downloaded.extend(chunk)
                    if len(downloaded) > MAX_COVER_FILE_SIZE:
                        logger.warning(f"Direct URL {url} exceeded limits. Aborting.")
                        return None

                if len(downloaded) >= MIN_COVER_FILE_SIZE:
                    content = bytes(downloaded)
                    if is_valid_cover(content):
                        logger.info(f"Cover for {identifier} downloaded successfully from URL {url}.")

                        filename = f"{identifier}_{suffix}.jpg"
                        filepath = os.path.join(COVERS_DIR, filename)
                        optimize_and_save_image(content, filepath)
                        res = f"{Config.COVERS_BASE_URL}/{filename}", source_name
    except (requests.RequestException, OSError, ValueError, TypeError) as e:
        logger.error(f"Error fetching direct URL {url}: {e}")
    return res


def fetch_external_api_cover(identifier: str, isbn: str | None = None) -> tuple[str, str] | None:
    """Tier 2 fallback: Try OpenLibrary, Google Books, then Allegro. Returns (path, source) tuple on success."""
    isbn_for_lookup = canonicalize_isbn(isbn or identifier)
    res = None

    if isbn_for_lookup:
        # 1. Open Library - try original (full resolution) first, then fall back to L
        ol_url_original = f"https://covers.openlibrary.org/b/isbn/{isbn_for_lookup}.jpg"
        res = download_direct_url(identifier, ol_url_original, "api_openlibrary", suffix="ol_orig")

        if not res:
            ol_url = f"https://covers.openlibrary.org/b/isbn/{isbn_for_lookup}-L.jpg"
            res = download_direct_url(identifier, ol_url, "api_openlibrary", suffix="ol")

        if not res:
            # 2. Google Books (Search -> Thumbnail)
            gb_search = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn_for_lookup}"
            try:
                with requests.get(gb_search, timeout=5) as gb_res:
                    if gb_res.status_code == 200:
                        gb_data = gb_res.json()
                        if "items" in gb_data:
                            thumb = gb_data["items"][0]["volumeInfo"].get("imageLinks", {}).get("thumbnail")
                            if thumb:
                                thumb = thumb.replace("http:", "https:")

                                # Try high-res first (zoom=0)
                                thumb_high_res = thumb.replace("zoom=1", "zoom=0")
                                res = download_direct_url(identifier, thumb_high_res, "api_google_books", suffix="gb")

                                # Fallback to original (zoom=1) if high-res failed validation
                                if not res and thumb_high_res != thumb:
                                    res = download_direct_url(identifier, thumb, "api_google_books", suffix="gb")
            except (requests.RequestException, OSError, ValueError, TypeError, KeyError, IndexError):
                pass
    else:
        logger.debug("Skipping External Bibliographic APIs (OpenLibrary/GoogleBooks) for non-ISBN identifier: %s", identifier)

    if not res:
        # 3. Allegro API
        from app.utils.allegro import fetch_allegro_metadata

        barcode_to_query = isbn_for_lookup or identifier
        if barcode_to_query:
            try:
                allegro_meta = fetch_allegro_metadata(barcode_to_query)
                if allegro_meta and allegro_meta.get("cover_url"):
                    res = download_direct_url(identifier, allegro_meta["cover_url"], "api_allegro", suffix="allegro")
            except (requests.RequestException, ValueError, KeyError, OSError, TypeError) as e:
                logger.warning("Failed to fetch cover from Allegro: %s", e)

    return res


def process_fast_cover(manifestation: Manifestation, identifier: str) -> bool:
    """Runs real-time (fast) lookups. Returns True if a cover was found."""
    result = fetch_external_api_cover(identifier)
    if not result:
        # Tier 2.5: Non-ISBN cover providers (MusicBrainz, TMDb)
        content_type = manifestation.expression.content_type if manifestation.expression else None
        result = fetch_upc_cover(identifier, content_type=content_type)
    if result:
        local_path, source = result
        manifestation.cover_url = local_path
        manifestation.update_meta(cover_source=source, cover_status="ready")
        return True
    return False


def fetch_upc_cover(identifier: str, content_type: str | None = None) -> tuple[str, str] | None:
    """Attempt cover resolution for non-ISBN identifiers (UPC/EAN barcodes).

    Routes to appropriate provider based on content_type:
    - music → MusicBrainz Cover Art Archive
    - movie/video → TMDb poster
    - board_game/game/puzzle → IGDB game artwork
    """
    if content_type == "music":
        return _fetch_musicbrainz_cover(identifier)
    if content_type in ("movie", "video"):
        return _fetch_tmdb_cover(identifier)
    if content_type in ("board_game", "game", "puzzle"):
        return _fetch_igdb_cover(identifier)
    return None


def _fetch_musicbrainz_cover(barcode: str) -> tuple[str, str] | None:
    """Query MusicBrainz by barcode, download front cover from Cover Art Archive."""
    url = f"https://musicbrainz.org/ws/2/release/?query=barcode:{barcode}&fmt=json"
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "iqoqo/0.7.1 ( dev@kruk.me )"})
        if resp.status_code != 200:
            return None
        releases = resp.json().get("releases", [])
        if not releases:
            return None
        release_id = releases[0].get("id")
        if not release_id:
            return None
        cover_url = f"https://coverartarchive.org/release/{release_id}/front"
        return download_direct_url(barcode, cover_url, "api_musicbrainz", suffix="mb")
    except (requests.RequestException, ValueError, KeyError) as e:
        logger.error("MusicBrainz cover lookup failed for %s: %s", barcode, e)
        return None


def _fetch_tmdb_cover(barcode: str) -> tuple[str, str] | None:
    """Resolve UPC to video title via external lookup, then fetch TMDb poster."""
    try:
        from app.utils.tmdb import clean_video_title, fetch_video_metadata
        from app.utils.upc import resolve_physical_media
    except ImportError:
        return None

    title = None
    upc_meta = resolve_physical_media(barcode)
    if upc_meta and upc_meta.get("title"):
        title = clean_video_title(upc_meta["title"])

    meta = fetch_video_metadata(title or barcode)
    if not meta or not meta.get("cover_url"):
        return None
    return download_direct_url(barcode, meta["cover_url"], "api_tmdb", suffix="tmdb")


def _fetch_igdb_cover(barcode: str) -> tuple[str, str] | None:
    """Resolve UPC to game title via external lookup, then fetch IGDB game artwork."""
    try:
        from app.utils.igdb import fetch_game_metadata
        from app.utils.upc import resolve_physical_media
    except ImportError:
        return None

    title = None
    upc_meta = resolve_physical_media(barcode)
    if upc_meta and upc_meta.get("title"):
        title = upc_meta["title"]

    meta = fetch_game_metadata(title or barcode)
    if not meta or not meta.get("cover_url"):
        return None
    return download_direct_url(barcode, meta["cover_url"], "api_igdb", suffix="igdb")


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

                local_cover_url = f"{Config.COVERS_BASE_URL}/{filename}"
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

            # Tier 2.5: Non-ISBN cover providers (MusicBrainz, TMDb)
            if not local_cover_url:
                content_type = manifestation.expression.content_type if manifestation.expression else None
                result = fetch_upc_cover(identifier, content_type=content_type)
                if result:
                    local_cover_url, source = result

        # Tier 3/4: LLM Generation
        allow_generate_cover = Config.ALLOW_LLM and llm_permissions.get("allow_generate_cover", False)
        if not local_cover_url and allow_generate_cover:
            # Extract format for media-aware prompts
            format_type = manifestation.meta.get("format") if manifestation.meta else None

            result = fetch_llm_cover(
                identifier,
                title,
                author,
                user_id,
                description,
                genre,
                format_type=format_type,
                allow_cloud_llm=llm_permissions.get("allow_cloud_llm", False),
            )
            if result:
                local_cover_url, source = result

        # Tier 5: PIL Fallback
        if not local_cover_url:
            result = generate_fallback_cover(identifier, title, author)
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
) -> str | None:
    """Fires off the background executor using the centralized task pool.

    Returns:
        str | None: Task ID, or None if the background queue is unavailable.
            Callers should treat None as a deferred/unavailable state and still
            return a success response — the data has been saved even without the task.
    """
    return submit_task(
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

            # Update DB
            book.cover_url = f"{Config.COVERS_BASE_URL}/{best_match}"

            updates = {"cover_status": "ready"}
            if not (book.meta and "cover_source" in book.meta):
                updates["cover_source"] = "rebind"
            book.update_meta(**updates)

            orphans_rebound += 1

    if orphans_rebound > 0:
        db.session.commit()

    return orphans_rebound


def cleanup_stuck_pending_covers(timeout_minutes: int = 30) -> int:
    """Finds manifestations stuck in 'pending' or 'processing' for more than timeout_minutes and resets them to 'failed'."""

    now = datetime.now(UTC)
    cutoff = now - timedelta(minutes=timeout_minutes)

    stuck_count = 0
    try:
        # Fetch all manifestations with pending/processing cover_status.
        stmt = (
            db.select(Manifestation)
            .where(
                db.or_(
                    Manifestation.meta["cover_status"].as_string() == "pending",
                    Manifestation.meta["cover_status"].as_string() == "processing",
                )
            )
            .execution_options(yield_per=100)
        )

        for manifestation in db.session.scalars(stmt):
            # Check updated_at timestamp
            updated_at_str = manifestation.meta.get("cover_status_updated_at")
            should_reset = False
            if updated_at_str:
                try:
                    # Parse isoformat
                    dt_str = updated_at_str
                    if dt_str.endswith("Z"):
                        dt_str = dt_str[:-1] + "+00:00"
                    updated_at = datetime.fromisoformat(dt_str)
                    if updated_at.tzinfo is None:
                        updated_at = updated_at.replace(tzinfo=UTC)

                    if updated_at < cutoff:
                        should_reset = True
                except ValueError:
                    # If timestamp is invalid/unparseable, reset it anyway to be safe
                    should_reset = True
            else:
                # If there's no updated_at timestamp but status is pending/processing,
                # we also consider it stuck.
                should_reset = True

            if should_reset:
                manifestation.update_meta(
                    cover_status="failed",
                    cover_error="Stuck task cleared at startup",
                )
                stuck_count += 1

        if stuck_count > 0:
            db.session.commit()
            logger.info("Cleared %d stuck cover tasks at startup", stuck_count)
    except Exception as e:  # pylint: disable=broad-exception-caught
        # Don't block app startup if tables aren't created yet or other DB issues
        logger.warning("Failed to check or clear stuck cover tasks at startup: %s", e)
        db.session.rollback()

    return stuck_count

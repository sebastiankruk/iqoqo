import hashlib
import io
import logging
import os
import threading

import requests
from PIL import Image, ImageDraw, ImageFont

from app.config import Config
from app.db import db
from app.db.models import Manifestation
from app.utils.images import optimize_and_save_image
from app.utils.llm_covers import fetch_llm_cover

logger = logging.getLogger(__name__)

COVERS_DIR = os.path.join(Config.BASE_DIR, "app", "static", "covers")
RAW_DIR = os.path.join(Config.BASE_DIR, "app", "static", "uploads", "raw_covers")

os.makedirs(COVERS_DIR, exist_ok=True)
os.makedirs(RAW_DIR, exist_ok=True)


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
        return f"/static/covers/{filename}"
    except (OSError, ValueError) as e:
        logger.error(f"Fallback generation failed: {e}")
        return None


def fetch_external_api_cover(isbn: str) -> tuple[str, str] | None:
    """Tier 2: Try OpenLibrary then Google Books. Returns (path, source) tuple on success."""

    # 1. Open Library (Direct)
    ol_url = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"
    try:
        response = requests.get(ol_url, stream=True, timeout=5)
        if response.status_code == 200:
            # content-length may be absent; consume the stream and measure actual bytes
            content = b"".join(response.iter_content(1024))
            # Reject 1×1 tracking pixels (always < 1 KB)
            if len(content) > 1000:
                filename = f"{isbn}_ol.jpg"
                filepath = os.path.join(COVERS_DIR, filename)
                with open(filepath, "wb") as f:
                    f.write(content)
                return f"/static/covers/{filename}", "api_openlibrary"
    except (requests.RequestException, OSError, ValueError, TypeError):
        pass

    # 2. Google Books (Search -> Thumbnail)
    gb_search = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
    try:
        res = requests.get(gb_search, timeout=5).json()
        if "items" in res:
            thumb = res["items"][0]["volumeInfo"].get("imageLinks", {}).get("thumbnail")
            if thumb:
                # Get higher res
                thumb = thumb.replace("zoom=1", "zoom=0").replace("http:", "https:")
                img_res = requests.get(thumb, timeout=10)
                if img_res.status_code == 200:
                    filename = f"{isbn}_gb.jpg"
                    filepath = os.path.join(COVERS_DIR, filename)
                    with open(filepath, "wb") as f:
                        f.write(img_res.content)
                    return f"/static/covers/{filename}", "api_google_books"
    except (requests.RequestException, OSError, ValueError, TypeError, KeyError, IndexError):
        pass

    return None


def process_fast_cover(manifestation: Manifestation, isbn: str) -> bool:
    """Runs real-time (fast) lookups. Returns True if a cover was found."""
    result = fetch_external_api_cover(isbn)
    if result:
        local_path, source = result
        manifestation.cover_path = local_path
        # Force SQLAlchemy to detect change in JSON field
        meta = dict(manifestation.meta) if manifestation.meta else {}
        meta["cover_source"] = source
        meta["cover_status"] = "ready"
        manifestation.meta = meta
        return True
    return False


def process_cover_pipeline(
    manifestation_id: int,
    isbn: str,
    title: str,
    author: str,
    user_image_path: str | None = None,
):
    """
    The single cover-generation pipeline (Chain of Responsibility).

    Tiers:
      1. User photo (if provided)
      2. External APIs (OpenLibrary, Google Books)
      3/4. LLM generation (local SD → Gemini → OpenAI)

    If all tiers fail the existing cover_path is left unchanged so the
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

        local_cover_path: str | None = None
        source: str | None = None

        # Tier 1: User Photo
        if user_image_path and os.path.exists(user_image_path):
            filename = f"{isbn}_user.jpg"
            dest_path = os.path.join(COVERS_DIR, filename)
            os.rename(user_image_path, dest_path)
            local_cover_path = f"/static/covers/{filename}"
            source = "user_photo"

        # Tier 2: External APIs
        if not local_cover_path:
            result = fetch_external_api_cover(isbn)
            if result:
                local_cover_path, source = result

        # Tier 3/4: LLM Generation
        if not local_cover_path:
            result = fetch_llm_cover(isbn, title, author)
            if result:
                local_cover_path, source = result

        # Update DB
        # Force SQLAlchemy to detect change in JSON field
        meta = dict(manifestation.meta) if manifestation.meta else {}

        if local_cover_path:
            abs_path = os.path.join(COVERS_DIR, os.path.basename(local_cover_path))
            add_source_badge(abs_path, source or "")
            manifestation.cover_path = local_cover_path
            meta["cover_source"] = source
            meta["cover_status"] = "ready"
            logger.info("Cover processed for %s: %s", isbn, source)
        else:
            # All tiers failed — leave cover_path as-is so the frontend shows
            # a book-icon placeholder rather than an empty or text-only image.
            meta["cover_status"] = "failed"
            logger.warning("Cover generation failed for %s: no cover produced, leaving existing", isbn)

        manifestation.meta = meta
        db.session.commit()


def start_cover_processing(manifestation_id: int, isbn: str, title: str, author: str, user_image_path: str | None = None):
    """Fires off the background thread."""
    thread = threading.Thread(target=process_cover_pipeline, args=(manifestation_id, isbn, title, author, user_image_path))
    thread.start()

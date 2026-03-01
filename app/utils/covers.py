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
            if img.mode != "RGB":
                img = img.convert("RGB")

            d = ImageDraw.Draw(img)
            w, h = img.size

            # Draw a 30x30 rectangle in bottom right
            box_size = 30
            d.rectangle([w - box_size, h - box_size, w, h], fill=color)

            # Draw the letter inside the box
            font = ImageFont.load_default()
            # Adjust position for default font
            d.text((w - 20, h - 22), text, fill="white", font=font)

            img.save(filepath)
    except Exception as e:
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


def fetch_external_api_cover(isbn: str) -> str | None:
    """Tier 2: Try OpenLibrary then Google Books."""

    # 1. Open Library (Direct)
    ol_url = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"
    try:
        response = requests.get(ol_url, stream=True, timeout=5)
        # Check for 1x1 pixel tracking image
        if response.status_code == 200 and int(response.headers.get("content-length", 0)) > 1000:
            filename = f"{isbn}_ol.jpg"
            filepath = os.path.join(COVERS_DIR, filename)
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return f"/static/covers/{filename}"
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
                    return f"/static/covers/{filename}"
    except (requests.RequestException, OSError, ValueError, TypeError, KeyError, IndexError):
        pass

    return None


def process_fast_cover(manifestation: Manifestation, isbn: str) -> bool:
    """Runs real-time (fast) lookups. Returns True if a cover was found."""
    # Try External APIs (OpenLibrary, Google Books)
    local_path = fetch_external_api_cover(isbn)
    if local_path:
        manifestation.cover_path = local_path
        if manifestation.meta is None:
            manifestation.meta = {}

        # Determine source based on filename suffix
        source = "external_api"
        if "_ol.jpg" in local_path:
            source = "api_openlibrary"
        elif "_gb.jpg" in local_path:
            source = "api_google_books"

        manifestation.meta["cover_source"] = source
        manifestation.meta["cover_status"] = "ready"
        return True
    return False


def generate_cover_async(app, manifestation_id: int, isbn: str, title: str, author: str):
    """Background thread for heavy LLM generation."""
    with app.app_context():
        manif = db.session.get(Manifestation, manifestation_id)
        if not manif:
            return

        local_path = fetch_llm_cover(isbn, title, author)

        # Fallback to basic pillow text cover if LLM fails
        if not local_path:
            local_path = generate_fallback_cover(isbn, title, author)

        if local_path:
            # Determine source
            source = "llm_generated"
            if "_gemini.jpg" in local_path:
                source = "llm_gemini"
            elif "_dalle.jpg" in local_path:
                source = "llm_openai"
            elif "_localsd.jpg" in local_path:
                source = "llm_local_stable_diffusion"
            elif "_generated.jpg" in local_path:
                source = "fallback_pil"

            abs_path = os.path.join(COVERS_DIR, os.path.basename(local_path))
            add_source_badge(abs_path, source)

            manif.cover_path = local_path
            if manif.meta is None:
                manif.meta = {}
            manif.meta["cover_source"] = source
            manif.meta["cover_status"] = "ready"
            db.session.commit()


def process_cover_pipeline(manifestation_id: int, isbn: str, title: str, author: str, user_image_path: str | None = None):
    """
    The Chain of Responsibility pipeline.
    Can be run in background thread or via CLI script.
    """
    from flask import current_app, has_app_context

    if has_app_context():
        app = current_app
    else:
        from app import create_app

        app = create_app()

    with app.app_context():
        manifestation = Manifestation.query.get(manifestation_id)
        if not manifestation:
            return

        local_cover_path = None
        source = None

        # Tier 1: User Photo
        if user_image_path and os.path.exists(user_image_path):
            filename = f"{isbn}_user.jpg"
            dest_path = os.path.join(COVERS_DIR, filename)
            os.rename(user_image_path, dest_path)
            local_cover_path = f"/static/covers/{filename}"
            source = "user_photo"

        # Tier 2: External APIs
        if not local_cover_path:
            local_cover_path = fetch_external_api_cover(isbn)
            source = "external_api" if local_cover_path else None

        # Tier 3/4: LLM Gen
        if not local_cover_path:
            local_cover_path = fetch_llm_cover(isbn, title, author)
            source = "llm_generated" if local_cover_path else None

        # Tier 5: Fallback
        if not local_cover_path:
            local_cover_path = generate_fallback_cover(isbn, title, author)
            source = "fallback_pil"

        # Update DB
        if manifestation.meta is None:
            manifestation.meta = {}

        manifestation.cover_path = local_cover_path
        manifestation.meta["cover_source"] = source
        manifestation.meta["cover_status"] = "ready"

        db.session.commit()
        logger.info(f"Cover processed for {isbn}: {source}")


def start_cover_processing(manifestation_id: int, isbn: str, title: str, author: str, user_image_path: str | None = None):
    """Fires off the background thread."""
    thread = threading.Thread(target=process_cover_pipeline, args=(manifestation_id, isbn, title, author, user_image_path))
    thread.start()

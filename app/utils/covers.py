import hashlib
import logging
import os
import threading

import requests
from PIL import Image, ImageDraw, ImageFont

from app.config import Config
from app.db import db
from app.db.models import Manifestation
from app.utils.llm_covers import fetch_llm_cover

logger = logging.getLogger(__name__)

COVERS_DIR = os.path.join(Config.BASE_DIR, "app", "static", "covers")
RAW_DIR = os.path.join(Config.BASE_DIR, "app", "static", "uploads", "raw_covers")

os.makedirs(COVERS_DIR, exist_ok=True)
os.makedirs(RAW_DIR, exist_ok=True)


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

        img.save(filepath)
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

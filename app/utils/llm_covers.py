import base64
import binascii
import logging
import os

import requests
from openai import OpenAI

from app.config import Config
from app.db import db
from app.db.models import LLMTelemetry
from app.utils.images import add_text_overlay, optimize_and_save_image

logger = logging.getLogger(__name__)

COVERS_DIR = os.path.join(Config.BASE_DIR, "app", "static", "covers")

# Approximate costs per image (USD)
PRICING = {
    # DALL-E 3 Standard
    "openai": 0.040,
    # Imagen 3
    "gemini": 0.030,
    # Local Stable Diffusion
    "local": 0.000,
}


def record_telemetry(provider: str):
    """Updates telemetry after a successful generation."""
    try:
        stat = LLMTelemetry.query.filter_by(provider=provider).first()
        if not stat:
            stat = LLMTelemetry(provider=provider)
            stat.images_generated = 0
            stat.estimated_cost_usd = 0.0
            db.session.add(stat)

        if stat.images_generated is None:
            stat.images_generated = 0
        stat.images_generated += 1
        if stat.estimated_cost_usd is None:
            stat.estimated_cost_usd = 0.0
        stat.estimated_cost_usd += PRICING.get(provider, 0.0)
        db.session.commit()
    except (RuntimeError, ValueError, TypeError) as e:
        logger.error(f"Failed to record telemetry: {e}")
        db.session.rollback()


def save_image(image_data: bytes, isbn: str, suffix: str) -> str:
    """Helper to save binary image data to disk."""
    filename = f"{isbn}_{suffix}.jpg"
    filepath = os.path.join(COVERS_DIR, filename)
    optimize_and_save_image(image_data, filepath)
    return f"/static/covers/{filename}"


def build_context(description: str, genre: str) -> str:
    ctx = ""
    if genre:
        ctx += f" Genre: {genre}."
    if description:
        ctx += f" Theme/Description: {description[:300]}."
    return ctx


def generate_cover_cloud(isbn: str, title: str, author: str, description: str = "", genre: str = "") -> tuple[str, str] | None:
    """Tier 3: OpenAI DALL-E 3. Returns (path, source) tuple on success."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        client = OpenAI(api_key=api_key)
        context = build_context(description, genre)
        prompt = f"A high-quality, minimalist book cover design for '{title}' by {author}.{context} No text other than the title and author. Clean typography, modern aesthetic."

        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )

        if not response.data:
            return None

        image_url = response.data[0].url
        if not isinstance(image_url, str):
            return None

        img_response = requests.get(image_url, timeout=30)

        if img_response.status_code == 200:
            path = save_image(img_response.content, isbn, "dalle")
            record_telemetry("openai")
            return path, "llm_openai"
    except (requests.RequestException, OSError, ValueError, TypeError, KeyError, IndexError, AttributeError) as e:
        logger.error(f"Cloud LLM Gen failed: {e}")

    return None


def generate_cover_gemini(isbn: str, title: str, author: str, description: str = "", genre: str = "") -> tuple[str, str] | None:
    """Tier 3: Google Imagen via Gemini API. Returns (path, source) tuple on success."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    # {
    #     "prompt": f"Minimalist book cover, highly detailed, title '{title}', author '{author}'",
    #     "number_of_images": 1,
    #     "height": 1024,
    #     "width": 1024,
    # }

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        context = build_context(description, genre)
        prompt = f"Minimalist book cover, highly detailed, title '{title}', author '{author}'.{context}"

        # The SDK automatically resolves the correct endpoint and API version
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=prompt,
            config=types.GenerateContentConfig(response_modalities=["IMAGE"], image_config=types.ImageConfig(aspect_ratio="1:1")),
        )

        # The new API returns the raw bytes inside inline_data
        if response.candidates:
            candidate = response.candidates[0]
            if candidate.content and candidate.content.parts:
                inline_data = candidate.content.parts[0].inline_data
                if inline_data and inline_data.data:
                    path = save_image(inline_data.data, isbn, "gemini")
                    record_telemetry("gemini")
                    return path, "llm_gemini"

    except (requests.RequestException, ValueError, TypeError, KeyError, IndexError, OSError, binascii.Error) as e:
        logger.error(f"Gemini Gen failed: {e}")

    return None


def generate_cover_local(isbn: str, title: str, author: str, description: str = "", genre: str = "") -> tuple[str, str] | None:
    """Tier 4: Local Stable Diffusion (Automatic1111 API). Returns (path, source) tuple on success."""
    sd_url = os.environ.get("LOCAL_SD_URL")
    if not sd_url:
        return None

    context = build_context(description, genre)
    payload = {
        "prompt": f"masterpiece, best quality, book cover art, minimalist, aesthetic, representing '{title}' by {author}, clean background, no text.{context}",
        "negative_prompt": "text, title, author, writing, letters, watermark, signature, blurry, low quality, cropped, ugly",
        "steps": 20,
        "width": 512,
        "height": 768,
    }

    try:
        response = requests.post(f"{sd_url}/sdapi/v1/txt2img", json=payload, timeout=300)
        if response.status_code == 200:
            r = response.json()
            image_data = base64.b64decode(r["images"][0])
            path = save_image(image_data, isbn, "localsd")

            # Overlay typography
            full_path = os.path.join(COVERS_DIR, os.path.basename(path))
            add_text_overlay(full_path, title, author)

            record_telemetry("local")
            return path, "llm_local_stable_diffusion"
    except (requests.RequestException, ValueError, TypeError, KeyError, IndexError, OSError, binascii.Error) as e:
        logger.error(f"Local SD Gen failed: {e}")

    return None


def fetch_llm_cover(isbn: str, title: str, author: str, description: str = "", genre: str = "") -> tuple[str, str] | None:
    """Orchestrates LLM generation tiers. Returns (path, source) tuple on success."""
    # 1. Local (Free)
    result = generate_cover_local(isbn, title, author, description, genre)
    if result:
        return result

    # 2. Cloud (Paid) - check env vars for which provider is available
    if os.environ.get("GEMINI_API_KEY"):
        result = generate_cover_gemini(isbn, title, author, description, genre)
        if result:
            return result

    if os.environ.get("OPENAI_API_KEY"):
        return generate_cover_cloud(isbn, title, author, description, genre)

    return None

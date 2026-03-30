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
import base64
import binascii
import logging
import os
import time

import requests
from openai import OpenAI

from app.config import Config
from app.core.permissions import ItemPermissions
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


def record_telemetry(provider: str, user_id: str, duration: float, operation_type: str = "cover_generation"):
    """Updates telemetry after a successful generation.

    Records per-user telemetry and accumulates total processing duration.
    """
    from sqlalchemy.exc import IntegrityError

    for attempt in range(2):
        try:
            stat = LLMTelemetry.query.filter_by(provider=provider, user_id=user_id, operation_type=operation_type).first()
            if not stat:
                stat = LLMTelemetry(provider=provider, user_id=user_id, operation_type=operation_type)
                stat.images_generated = 0
                stat.estimated_cost_usd = 0.0
                stat.total_duration_seconds = 0.0
                db.session.add(stat)

            if stat.images_generated is None:
                stat.images_generated = 0
            stat.images_generated += 1

            if stat.estimated_cost_usd is None:
                stat.estimated_cost_usd = 0.0
            stat.estimated_cost_usd += PRICING.get(provider, 0.0)

            if stat.total_duration_seconds is None:
                stat.total_duration_seconds = 0.0
            stat.total_duration_seconds += duration

            db.session.commit()
            break
        except IntegrityError:
            db.session.rollback()
            if attempt == 1:
                logger.error("Failed to record telemetry after 2 attempts due to concurrent inserts.")
        except (RuntimeError, ValueError, TypeError) as e:
            logger.error("Failed to record telemetry: %s", e)
            db.session.rollback()
            break


def save_image(image_data: bytes, identifier: str, suffix: str) -> str:
    """Helper to save binary image data to disk."""
    filename = f"{identifier}_{suffix}.jpg"
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


def generate_cover_cloud(
    identifier: str, title: str, author: str, user_id: str, description: str = "", genre: str = ""
) -> tuple[str, str] | None:
    """Tier 3: OpenAI DALL-E 3. Returns (path, source) tuple on success."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        start_time = time.time()
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
            path = save_image(img_response.content, identifier, "dalle")
            duration = time.time() - start_time
            record_telemetry("openai", user_id, duration, "cover_generation")
            return path, "llm_openai"
    except (requests.RequestException, OSError, ValueError, TypeError, KeyError, IndexError, AttributeError) as e:
        logger.error(f"Cloud LLM Gen failed: {e}")

    return None


def generate_cover_gemini(
    identifier: str, title: str, author: str, user_id: str, description: str = "", genre: str = ""
) -> tuple[str, str] | None:
    """Tier 3: Google Imagen via Gemini API. Returns (path, source) tuple on success."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    try:
        start_time = time.time()
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        context = build_context(description, genre)
        prompt = f"Minimalist book cover, highly detailed, title '{title}', author '{author}'.{context}"

        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=prompt,
            config=types.GenerateContentConfig(response_modalities=["IMAGE"], image_config=types.ImageConfig(aspect_ratio="1:1")),
        )

        if response.candidates:
            candidate = response.candidates[0]
            if candidate.content and candidate.content.parts:
                inline_data = candidate.content.parts[0].inline_data
                if inline_data and inline_data.data:
                    path = save_image(inline_data.data, identifier, "gemini")
                    duration = time.time() - start_time
                    record_telemetry("gemini", user_id, duration, "cover_generation")
                    return path, "llm_gemini"

    except (requests.RequestException, ValueError, TypeError, KeyError, IndexError, OSError, binascii.Error) as e:
        logger.error(f"Gemini Gen failed: {e}")

    return None


def generate_cover_local(
    identifier: str, title: str, author: str, user_id: str, description: str = "", genre: str = ""
) -> tuple[str, str] | None:
    """Tier 4: Local Stable Diffusion (Automatic1111 API). Returns (path, source) tuple on success."""
    sd_url = os.environ.get("LOCAL_SD_URL")
    if not sd_url:
        return None

    # Truncate title to first 4 words for local SD prompt
    words = title.split()
    trimmed_title = " ".join(words[:4]) if len(words) > 4 else title

    context = build_context(description, genre)
    payload = {
        "prompt": f"masterpiece, best quality, book cover art, minimalist, aesthetic, representing '{trimmed_title}' by {author}, clean background, no text.{context}",
        "negative_prompt": "text, title, author, writing, letters, watermark, signature, blurry, low quality, cropped, ugly",
        "steps": 20,
        "width": 512,
        "height": 768,
    }

    try:
        start_time = time.time()
        response = requests.post(f"{sd_url}/sdapi/v1/txt2img", json=payload, timeout=300)
        if response.status_code == 200:
            r = response.json()
            image_data = base64.b64decode(r["images"][0])
            path = save_image(image_data, identifier, "localsd")

            # Overlay typography
            full_path = os.path.join(COVERS_DIR, os.path.basename(path))
            add_text_overlay(full_path, title, author)

            duration = time.time() - start_time
            record_telemetry("local", user_id, duration, "cover_generation")
            return path, "llm_local_stable_diffusion"
    except (requests.RequestException, ValueError, TypeError, KeyError, IndexError, OSError, binascii.Error) as e:
        logger.error(f"Local SD Gen failed: {e}")

    return None


def fetch_llm_cover(
    identifier: str, title: str, author: str, user_id: str, description: str = "", genre: str = "", allow_cloud_llm: bool = False
) -> tuple[str, str] | None:
    """Orchestrates LLM generation tiers. Returns (path, source) tuple on success."""
    # 1. Local (Free)
    result = generate_cover_local(identifier, title, author, user_id, description, genre)
    if result:
        return result

    # 2. Cloud (Paid) - restricted by cloud permission
    if not allow_cloud_llm:
        logger.debug(f"Cloud LLM generation skipped: user lacks {ItemPermissions.LLM_GENERATE_CLOUD.value} permission.")
        return None

    if os.environ.get("GEMINI_API_KEY"):
        result = generate_cover_gemini(identifier, title, author, user_id, description, genre)
        if result:
            return result

    if os.environ.get("OPENAI_API_KEY"):
        return generate_cover_cloud(identifier, title, author, user_id, description, genre)

    return None

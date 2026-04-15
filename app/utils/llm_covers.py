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

import base64
import binascii
import logging
import os
import time

import requests
from openai import OpenAI
from sqlalchemy.exc import SQLAlchemyError

from app.config import Config
from app.core.permissions import PermissionName
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


def record_telemetry(
    provider: str,
    user_id: str,
    duration: float,
    operation_type: str = "cover_generation",
    status: str = "success",
    error_message: str | None = None,
):
    """Records a new telemetry entry after an LLM operation.

    Each execution is recorded as a separate row to provide a full audit trail.
    """
    try:
        stat = LLMTelemetry(
            provider=provider,
            user_id=user_id,
            operation_type=operation_type,
            images_generated=1 if status == "success" else 0,
            estimated_cost_usd=PRICING.get(provider, 0.0) if status == "success" else 0.0,
            total_duration_seconds=duration,
            status=status,
            error_message=error_message,
        )
        db.session.add(stat)
        db.session.commit()
    except SQLAlchemyError as e:
        logger.error("Failed to record telemetry: %s", e)
        db.session.rollback()


def save_image(image_data: bytes, identifier: str, suffix: str) -> str:
    """Helper to save binary image data to disk."""
    filename = f"{identifier}_{suffix}.jpg"
    filepath = os.path.join(COVERS_DIR, filename)
    optimize_and_save_image(image_data, filepath)
    return f"{Config.COVERS_BASE_URL}/{filename}"


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

    start_time = time.time()
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
            record_telemetry("openai", user_id, time.time() - start_time, status="failed", error_message="Empty response data")
            return None

        image_url = response.data[0].url
        if not isinstance(image_url, str):
            record_telemetry("openai", user_id, time.time() - start_time, status="failed", error_message="Invalid image URL in response")
            return None

        img_response = requests.get(image_url, timeout=30)

        if img_response.status_code == 200:
            path = save_image(img_response.content, identifier, "dalle")
            duration = time.time() - start_time
            record_telemetry("openai", user_id, duration, "cover_generation")
            return path, "llm_openai"

        record_telemetry("openai", user_id, time.time() - start_time, status="failed", error_message=f"HTTP {img_response.status_code}")
    except (requests.RequestException, OSError, ValueError, TypeError, KeyError, IndexError, AttributeError) as e:
        logger.error(f"Cloud LLM Gen failed: {e}")
        record_telemetry("openai", user_id, time.time() - start_time, status="failed", error_message=str(e))

    return None


def generate_cover_gemini(
    identifier: str, title: str, author: str, user_id: str, description: str = "", genre: str = ""
) -> tuple[str, str] | None:
    """Tier 3: Google Imagen via Gemini API. Returns (path, source) tuple on success."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    start_time = time.time()
    try:
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

        record_telemetry("gemini", user_id, time.time() - start_time, status="failed", error_message="No valid candidates in response")

    except (requests.RequestException, ValueError, TypeError, KeyError, IndexError, OSError, binascii.Error) as e:
        logger.error(f"Gemini Gen failed: {e}")
        record_telemetry("gemini", user_id, time.time() - start_time, status="failed", error_message=str(e))

    return None


def generate_cover_local(
    identifier: str, title: str, author: str, user_id: str, description: str = "", genre: str = ""
) -> tuple[str, str] | None:
    """Tier 4: Local Stable Diffusion (Automatic1111 API). Returns (path, source) tuple on success."""
    sd_url = os.environ.get("LOCAL_SD_URL")
    if not sd_url:
        return None

    # Trimming for prompt is now removed to give full context to LLM.
    # Trimming for overlay is applied further below.
    context = build_context(description, genre)
    payload = {
        "prompt": f"masterpiece, best quality, book cover art, minimalist, aesthetic, representing '{title}' by {author}, clean background, no text.{context}",
        "negative_prompt": "text, title, author, writing, letters, watermark, signature, blurry, low quality, cropped, ugly",
        "steps": 20,
        "width": 512,
        "height": 768,
    }

    logger.debug("Generating local SD cover with prompt: %s", payload["prompt"])
    start_time = time.time()
    try:
        response = requests.post(f"{sd_url}/sdapi/v1/txt2img", json=payload, timeout=300)
        if response.status_code == 200:
            r = response.json()
            image_data = base64.b64decode(r["images"][0])
            path = save_image(image_data, identifier, "localsd")

            # Overlay typography - potentially trimmed for visual clarity
            full_path = os.path.join(COVERS_DIR, os.path.basename(path))

            overlay_title = title
            if Config.LLM_TITLE_MAX_WORDS > 0:
                words = title.split()
                if len(words) > Config.LLM_TITLE_MAX_WORDS:
                    overlay_title = " ".join(words[: Config.LLM_TITLE_MAX_WORDS]) + "..."

            add_text_overlay(full_path, overlay_title, author)

            duration = time.time() - start_time
            record_telemetry("local", user_id, duration, "cover_generation")
            return path, "llm_local_stable_diffusion"

        record_telemetry("local", user_id, time.time() - start_time, status="failed", error_message=f"HTTP {response.status_code}")
    except (requests.RequestException, ValueError, TypeError, KeyError, IndexError, OSError, binascii.Error) as e:
        logger.error(f"Local SD Gen failed: {e}")
        record_telemetry("local", user_id, time.time() - start_time, status="failed", error_message=str(e))

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
        logger.debug(f"Cloud LLM generation skipped: user lacks {PermissionName.LLM_GENERATE_CLOUD.value} permission.")
        record_telemetry(
            "cloud", user_id, 0.0, status="not_allowed", error_message=f"User lacks {PermissionName.LLM_GENERATE_CLOUD.value} permission"
        )
        return None

    if os.environ.get("GEMINI_API_KEY"):
        result = generate_cover_gemini(identifier, title, author, user_id, description, genre)
        if result:
            return result

    if os.environ.get("OPENAI_API_KEY"):
        return generate_cover_cloud(identifier, title, author, user_id, description, genre)

    return None

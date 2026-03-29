"""Utilities for extracting book metadata from cover images using a Vision LLM or OCR."""

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
import io
import json
import logging
import os
import re
import time
import uuid

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import Config
from app.core.permissions import ItemPermissions
from app.db.models import User, db

logger = logging.getLogger(__name__)

PROMPT = (
    "You are a book cataloguing assistant. "
    "Look at the book cover image and extract the book metadata. "
    "Respond ONLY with a JSON object in this exact format, with no markdown fences or extra text:\n"
    '{"Title": "<title>", "Subtitle": "<subtitle>", "Authors": ["<author1>", "<author2>"], '
    '"Publisher": "<publisher>", "Year": "<year>", "ISBN": "<isbn>", '
    '"Edition": "<edition>", "Language": "<language>", "Genre": "<genre>"}\n'
    "If you cannot determine a field, use an empty string or empty list as appropriate."
)


def extract_metadata_from_cover(image_bytes: bytes, mime_type: str = "image/jpeg", user_id: str | None = None) -> dict | None:
    # 1. Try Gemini
    try:
        result = _extract_via_gemini(image_bytes, mime_type, user_id)
        if result:
            return result
    except (ValueError, TypeError, ConnectionError, TimeoutError, RuntimeError) as e:
        logger.error("Waterfall step 1 (Gemini) raised an exception: %s", e)

    # 2. Try Ollama Fallback
    try:
        result = _extract_via_ollama(image_bytes)
        if result:
            return result
    except requests.exceptions.RequestException as e:
        logger.error("Waterfall step 2 (Ollama) raised an exception: %s", e)

    # 3. Try Tesseract OCR Fallback
    try:
        return _extract_via_tesseract(image_bytes)
    except (OSError, ValueError, RuntimeError) as e:
        logger.error("Waterfall step 3 (Tesseract) raised an exception: %s", e)

    return None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((ConnectionError, TimeoutError, RuntimeError)),
    reraise=True,
)
def _call_gemini_api(client, model, contents):
    """Helper to wrap API calls with Tenacity backoff"""
    return client.models.generate_content(model=model, contents=contents)


def _extract_via_gemini(image_bytes: bytes, mime_type: str, user_id: str | None = None) -> dict | None:
    can_use_cloud_llm = False
    if user_id:
        user = None
        try:
            user = db.session.get(User, uuid.UUID(user_id))
        except ValueError:
            logger.debug("vision._extract_via_gemini: invalid user_id format %r, skipping permission check.", user_id)

        if user:
            can_use_cloud_llm = user.has_permission(ItemPermissions.LLM_GENERATE_CLOUD.value)

    if not Config.ALLOW_LLM or not can_use_cloud_llm:
        logger.debug("Gemini execution skipped: ALLOW_LLM=%s, cloud status=%s", Config.ALLOW_LLM, can_use_cloud_llm)
        return None

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY not set – skipping Gemini vision extraction.")
        return None

    from app.utils.llm_covers import record_telemetry

    try:
        from google import genai  # type: ignore[import-untyped]
        from google.genai import types  # type: ignore[import-untyped]

        client = genai.Client(api_key=api_key)
        start_time = time.time()

        response = _call_gemini_api(client, "gemini-flash-latest", [types.Part.from_bytes(data=image_bytes, mime_type=mime_type), PROMPT])

        raw = response.text.strip() if response.text else ""
        result = _parse_json_response(raw)

        if result and user_id:
            duration = time.time() - start_time
            record_telemetry("gemini", user_id, duration)

        return result

    except (ImportError, AttributeError) as e:
        logger.error("google-genai package is not installed or API surface changed: %s", e)
    except (ValueError, TypeError, ConnectionError, TimeoutError, RuntimeError) as e:
        logger.error("Gemini vision extraction failed: %s", e)

    return None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(requests.exceptions.RequestException),
    reraise=True,
)
def _call_ollama_api(url, payload):
    response = requests.post(f"{url}/api/generate", json=payload, timeout=30)
    response.raise_for_status()
    return response


def _extract_via_ollama(image_bytes: bytes) -> dict | None:
    if not Config.ALLOW_LLM:
        logger.debug("Ollama vision extraction skipped: ALLOW_LLM is false.")
        return None

    url = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
    model = os.environ.get("OLLAMA_VISION_MODEL", "llava")

    try:
        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        payload = {"model": model, "prompt": PROMPT, "images": [b64_image], "stream": False, "format": "json"}

        response = _call_ollama_api(url, payload)

        data = response.json()
        raw = data.get("response", "").strip()
        return _parse_json_response(raw)

    except ImportError:
        logger.error("requests library is missing for Ollama extraction.")
    except requests.exceptions.RequestException as e:
        msg = str(e)
        err_resp = getattr(e, "response", None)
        if err_resp is not None and getattr(err_resp, "status_code", None) == 404:
            msg = f"Model '{model}' not found on Ollama. Run 'ollama pull {model}' to fix."
        logger.error("Ollama HTTP extraction failed: %s", msg)

    return None


def _extract_via_tesseract(image_bytes: bytes) -> dict | None:
    try:
        import pytesseract
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(img).strip()

        if not text:
            return None

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return None

        title = lines[0]
        authors = lines[1:] if len(lines) > 1 else []

        return {"Title": title, "Authors": authors}

    except ImportError:
        logger.error("pytesseract or Pillow is not installed.")
    except (OSError, ValueError, RuntimeError) as e:
        msg = str(e)
        if "tesseract is not installed" in msg:
            msg = "tesseract-ocr not found on host. On macOS, run 'brew install tesseract'."
        logger.error("Tesseract extraction failed: %s", msg)

    return None


def _parse_json_response(raw: str) -> dict | None:
    if not raw:
        return None
    try:
        # String concatenation used here to prevent markdown UI renderer bugs
        ticks = "`" * 3
        raw = re.sub(r"^" + ticks + r"(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*" + ticks + r"$", "", raw)

        data = json.loads(raw)

        title = data.get("Title", "")
        authors = data.get("Authors", [])

        # Extract new requested fields
        subtitle = data.get("Subtitle", "")
        publisher = data.get("Publisher", "")
        year = data.get("Year", "")
        isbn = data.get("ISBN", "")
        edition = data.get("Edition", "")
        language = data.get("Language", "")
        genre = data.get("Genre", "")

        if not isinstance(title, str):
            title = str(title)
        if not isinstance(authors, list):
            authors = [a.strip() for a in str(authors).split(",") if a.strip()] if authors else []

        return {
            "Title": title.strip(),
            "Subtitle": str(subtitle).strip(),
            "Authors": [a.strip() for a in authors if a],
            "Publisher": str(publisher).strip(),
            "Year": str(year).strip(),
            "ISBN": str(isbn).strip(),
            "Edition": str(edition).strip(),
            "Language": str(language).strip(),
            "Genre": str(genre).strip(),
        }
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        logger.error("Failed to parse JSON response: %s", e)
        return None

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

logger = logging.getLogger(__name__)

PROMPT = (
    "You are a book cataloguing assistant. "
    "Look at the book cover image and extract the book title and the author(s). "
    "Respond ONLY with a JSON object in this exact format, with no markdown fences or extra text:\n"
    '{"Title": "<title>", "Authors": ["<author1>", "<author2>"]}\n'
    "If you cannot determine the title or authors, use an empty string or empty list."
)


def extract_metadata_from_cover(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict | None:
    """Extract book Title and Authors from a cover image using a fallback waterfall.

    The function attempts to extract metadata in the following order:
    1. Gemini Vision API (Primary, high quality)
    2. Local Ollama Vision API e.g., llava (Free, local fallback)
    3. Tesseract OCR (Basic, offline text extraction)

    Returns a dictionary with ``Title`` (str) and ``Authors`` (list[str]) when successful.
    Returns ``None`` when all methods fail.

    Args:
        image_bytes: Raw bytes of the cover image (JPEG, PNG, WebP supported).
        mime_type:   MIME type of the image, defaults to ``image/jpeg``.

    Returns:
        A dict ``{"Title": str, "Authors": [str, ...]}`` on success, or ``None``.
    """
    # 1. Try Gemini
    result = _extract_via_gemini(image_bytes, mime_type)
    if result:
        return result

    # 2. Try Ollama Fallback
    result = _extract_via_ollama(image_bytes)
    if result:
        return result

    # 3. Try Tesseract OCR Fallback
    return _extract_via_tesseract(image_bytes)


def _extract_via_gemini(image_bytes: bytes, mime_type: str) -> dict | None:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY not set – skipping Gemini vision extraction.")
        return None

    try:
        from google import genai  # type: ignore[import-untyped]
        from google.genai import types  # type: ignore[import-untyped]

        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                PROMPT,
            ],  # type: ignore[arg-type]
        )

        raw = response.text.strip() if response.text else ""
        return _parse_json_response(raw)

    except (ImportError, AttributeError) as e:
        logger.error("google-genai package is not installed or API surface changed: %s", e)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("Gemini vision extraction failed: %s", e)

    return None


def _extract_via_ollama(image_bytes: bytes) -> dict | None:
    url = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
    model = os.environ.get("OLLAMA_VISION_MODEL", "llava")

    try:
        import requests

        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        payload = {"model": model, "prompt": PROMPT, "images": [b64_image], "stream": False, "format": "json"}

        response = requests.post(f"{url}/api/generate", json=payload, timeout=30)
        response.raise_for_status()

        data = response.json()
        raw = data.get("response", "").strip()
        return _parse_json_response(raw)

    except ImportError:
        logger.error("requests library is missing for Ollama extraction.")
    except Exception as e:  # pylint: disable=broad-exception-caught
        import requests

        msg = str(e)
        if isinstance(e, requests.exceptions.RequestException):
            err_resp = getattr(e, "response", None)
            if err_resp is not None and getattr(err_resp, "status_code", None) == 404:
                msg = f"Model '{model}' not found on Ollama. Run 'ollama pull {model}' to fix."
        logger.error("Ollama vision extraction failed: %s", msg)

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
    except Exception as e:  # pylint: disable=broad-exception-caught
        msg = str(e)
        if "tesseract is not installed" in msg:
            msg = "tesseract-ocr not found on host. On macOS, run 'brew install tesseract'."
        logger.error("Tesseract extraction failed: %s", msg)

    return None


def _parse_json_response(raw: str) -> dict | None:
    if not raw:
        return None
    try:
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        data = json.loads(raw)

        title = data.get("Title", "")
        authors = data.get("Authors", [])

        if not isinstance(title, str):
            title = str(title)
        if not isinstance(authors, list):
            authors = [str(authors)] if authors else []

        return {"Title": title.strip(), "Authors": [a.strip() for a in authors if a]}
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        logger.error("Failed to parse JSON response: %s", e)
        return None

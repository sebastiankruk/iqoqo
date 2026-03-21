"""Utilities for extracting book metadata from cover images using a Vision LLM."""

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
import json
import logging
import os
import re

logger = logging.getLogger(__name__)


def extract_metadata_from_cover(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict | None:
    """Extract book Title and Authors from a cover image using the Gemini Vision API.

    The function calls the Gemini multimodal model with the supplied image and returns
    a dictionary with ``Title`` (str) and ``Authors`` (list[str]) when successful.
    Returns ``None`` when the API key is missing, the API call fails, or the model
    response cannot be parsed.

    Setup
    -----
    Set the ``GEMINI_API_KEY`` environment variable to a valid
    `Google AI Studio <https://aistudio.google.com/api-keys>`_ key.
    The key requires access to the ``gemini-2.0-flash`` (or later) model.

    Args:
        image_bytes: Raw bytes of the cover image (JPEG, PNG, WebP supported).
        mime_type:   MIME type of the image, defaults to ``image/jpeg``.

    Returns:
        A dict ``{"Title": str, "Authors": [str, ...]}`` on success, or ``None``.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY not set – vision extraction is disabled.")
        return None

    try:
        from google import genai  # type: ignore[import-untyped]
        from google.genai import types  # type: ignore[import-untyped]

        client = genai.Client(api_key=api_key)

        prompt = (
            "You are a book cataloguing assistant. "
            "Look at the book cover image and extract the book title and the author(s). "
            "Respond ONLY with a JSON object in this exact format, with no markdown fences or extra text:\n"
            '{"Title": "<title>", "Authors": ["<author1>", "<author2>"]}\n'
            "If you cannot determine the title or authors, use an empty string or empty list."
        )

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                prompt,
            ],  # type: ignore[arg-type]
        )

        raw = response.text.strip() if response.text else ""

        # Strip optional markdown code-fence wrappers the model might add
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

    except (ImportError, AttributeError) as e:
        logger.error("google-genai package is not installed or API surface changed: %s", e)
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        logger.error("Failed to parse Gemini vision response: %s", e)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("Gemini vision extraction failed: %s", e)

    return None

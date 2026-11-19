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
import shutil
import time
import uuid
from typing import Any

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import Config
from app.core.config_service import ConfigService
from app.core.permissions import PermissionName
from app.db.models import User, db

logger = logging.getLogger(__name__)

_MAX_COVER_PIXELS = 100_000_000
_OCR_MAX_DIMENSION = 2200
_LLM_MAX_DIMENSION = 2000


def _is_llm_enabled() -> bool:
    """Resolve ALLOW_LLM via Config.ALLOW_LLM or ConfigService (DB / env)."""
    if Config.ALLOW_LLM:
        return True
    return ConfigService.get_bool("ALLOW_LLM", False)


def _resolve_ollama_base_url() -> str:
    """Return configured Ollama URL, falling back to host.docker.internal inside containers."""
    configured = ConfigService.get("OLLAMA_URL")
    if isinstance(configured, str) and configured.strip():
        return configured.strip().rstrip("/")
    default_url = "http://localhost:11434"
    if os.path.exists("/.dockerenv"):
        try:
            requests.get(f"{default_url}/api/tags", timeout=1)
            return default_url
        except requests.exceptions.RequestException:
            return "http://host.docker.internal:11434"
    return default_url


def _normalize_cover_image_bytes(image_bytes: bytes, max_dim: int = _LLM_MAX_DIMENSION) -> tuple[bytes, str]:
    """EXIF-transpose and downscale large camera images; return original bytes if unparseable."""
    try:
        from PIL import Image, ImageOps

        prev_max = Image.MAX_IMAGE_PIXELS
        if isinstance(prev_max, int) and prev_max < _MAX_COVER_PIXELS:
            Image.MAX_IMAGE_PIXELS = _MAX_COVER_PIXELS
        try:
            with Image.open(io.BytesIO(image_bytes)) as opened:
                img = ImageOps.exif_transpose(opened)
                if max(img.size) <= max_dim and img.mode in ("RGB", "L"):
                    return image_bytes, "image/jpeg"
                rgb = img.convert("RGB")
                rgb.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
                buf = io.BytesIO()
                rgb.save(buf, format="JPEG", quality=88)
                return buf.getvalue(), "image/jpeg"
        finally:
            Image.MAX_IMAGE_PIXELS = prev_max
    except (ImportError, OSError, ValueError):
        return image_bytes, "image/jpeg"


PROMPT = (
    "You are a book and periodical cataloguing assistant. "
    "Look at the book or magazine cover image and extract its bibliographic metadata. "
    "Respond ONLY with a JSON object in this exact format, with no markdown fences or extra text:\n"
    '{"Title": "<title>", "Subtitle": "<subtitle>", "Authors": ["<author1>", "<author2>"], '
    '"Publisher": "<publisher>", "Year": "<year>", "ISBN": "<isbn>", '
    '"ISSN": "<issn>", "Indeks": "<indeks>", "IssueNumber": "<issue_number>", '
    '"CumulativeIssueNumber": "<cumulative_issue_number>", "Volume": "<volume>", '
    '"PublicationMonth": "<month_1_to_12>", "PublicationYear": "<4_digit_year>", '
    '"CoverHeadline": "<cover_headline>", '
    '"Edition": "<edition>", "Language": "<language>", "Genre": "<genre>"}\n'
    "If you cannot determine a field, use an empty string or empty list as appropriate."
)


def extract_metadata_from_cover(image_bytes: bytes, mime_type: str = "image/jpeg", user_id: str | None = None) -> dict | None:
    """Extract book metadata from a cover image using a waterfall of vision backends.

    This is the public entry point used by API handlers to obtain structured metadata from
    a single cover image. The function tries multiple backends in sequence and returns
    the first successful result:

    1. Gemini Vision (cloud LLM) -- used only when Config.ALLOW_LLM is true, a valid
       ``user_id`` is provided, and the associated user has the
       ``PermissionName.LLM_GENERATE_CLOUD`` permission. If Gemini is unavailable, fails,
       or returns no usable data, the function falls through to the next step.
    2. Ollama Vision -- used when Config.ALLOW_LLM is true and a local Ollama instance is
       reachable. Network errors or invalid responses cause the function to fall through
       to the next step.
    3. Tesseract OCR -- used as a final, local-only fallback that performs OCR on the
       image and heuristically derives a title and list of authors from the text.

    Parameters
    ----------
    image_bytes:
        Raw bytes of the cover image.
    mime_type:
        MIME type of the image (for example ``"image/jpeg"`` or ``"image/png"``). This is
        passed through to backends that require it (such as Gemini Vision).
    user_id:
        Optional string UUID of the requesting user. When provided, it is used to check
        whether the caller is allowed to use cloud LLM backends; if omitted or invalid,
        cloud-only steps are skipped and local fallbacks are used instead.

    Returns
    -------
    dict | None
        A dictionary containing the extracted metadata, or ``None`` if no backend could
        produce a result. When successful, the dictionary will typically contain some or
        all of the following keys (depending on the backend and what could be inferred):

        - ``"Title"`` (str)
        - ``"Subtitle"`` (str)
        - ``"Authors"`` (list[str])
        - ``"Publisher"`` (str)
        - ``"Year"`` (str)
        - ``"ISBN"`` (str)
        - ``"Edition"`` (str)
        - ``"Language"`` (str)
        - ``"Genre"`` (str)

    Notes
    -----
    Backend-specific exceptions are logged and swallowed; this function itself does not
    raise on backend failure and instead returns ``None`` when all steps are exhausted.
    """

    # 1. Try Gemini
    try:
        result = _extract_via_gemini(image_bytes, mime_type, user_id)
        if result:
            return result
    except (ValueError, KeyError, IndexError, AttributeError, TypeError, OSError, RuntimeError) as e:
        logger.warning("Waterfall: Gemini failed, trying Ollama... (%s)", e)

    # 2. Try Ollama Fallback
    try:
        result = _extract_via_ollama(image_bytes, user_id=user_id)
        if result:
            return result
    except (ValueError, KeyError, IndexError, AttributeError, TypeError, OSError, RuntimeError, requests.exceptions.RequestException) as e:
        logger.warning("Waterfall: Ollama failed, trying Tesseract... (%s)", e)

    # 3. Try Tesseract OCR Fallback
    try:
        return _extract_via_tesseract(image_bytes, user_id=user_id)
    except (OSError, ValueError, RuntimeError) as e:
        logger.error("Waterfall: Tesseract failed: %s", e)

    return None


def _record_vision_telemetry(
    provider: str,
    user_id: str | uuid.UUID | None,
    duration: float,
    status: str = "success",
    error_message: str | None = None,
) -> None:
    """Persist metadata extraction telemetry to LLMTelemetry when app context or mock is present."""
    from flask import has_app_context

    from app.utils.llm_covers import record_telemetry

    session_is_mocked = bool(getattr(getattr(db, "session", None), "_mock_name", None))
    if not has_app_context() and not session_is_mocked:
        return
    effective_user_id = str(user_id) if user_id else "system"
    record_telemetry(
        provider,
        effective_user_id,
        duration,
        operation_type="metadata_extraction",
        status=status,
        error_message=error_message[:500] if error_message else None,
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((ConnectionError, TimeoutError, RuntimeError)),
    reraise=True,
)
def _call_gemini_api(client, model, contents):
    """Helper to wrap API calls with Tenacity backoff"""
    return client.models.generate_content(model=model, contents=contents)


def _extract_via_gemini(image_bytes: bytes, mime_type: str, user_id: str | uuid.UUID | None = None) -> dict | None:
    can_use_cloud_llm = False
    user_id_str = str(user_id) if user_id else None
    if user_id:
        user = None
        try:
            user_uuid = user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))
            user = db.session.get(User, user_uuid)
        except (ValueError, TypeError, AttributeError):
            logger.debug("vision._extract_via_gemini: invalid user_id format %r, skipping permission check.", user_id)

        if user:
            can_use_cloud_llm = user.has_permission(PermissionName.LLM_GENERATE_CLOUD.value)

    if not _is_llm_enabled() or not can_use_cloud_llm:
        logger.debug("Gemini execution skipped: ALLOW_LLM=%s, cloud status=%s", _is_llm_enabled(), can_use_cloud_llm)
        return None

    api_key = ConfigService.get("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY not set – skipping Gemini vision extraction.")
        return None

    from flask import has_app_context

    from app.utils.llm_covers import record_telemetry

    api_error_cls: type[BaseException] = RuntimeError
    start_time = time.time()
    try:
        from google import genai  # type: ignore[import-untyped]
        from google.genai import types  # type: ignore[import-untyped]

        maybe_api_err = getattr(getattr(genai, "errors", None), "APIError", None)
        if isinstance(maybe_api_err, type) and issubclass(maybe_api_err, BaseException):
            api_error_cls = maybe_api_err

        normalized_bytes, normalized_mime = _normalize_cover_image_bytes(image_bytes)
        effective_mime = normalized_mime if normalized_bytes is not image_bytes else mime_type

        client = genai.Client(api_key=api_key)
        start_time = time.time()

        response = _call_gemini_api(
            client,
            "gemini-flash-latest",
            [types.Part.from_bytes(data=normalized_bytes, mime_type=effective_mime), PROMPT],
        )

        raw = response.text.strip() if response.text else ""
        result = _parse_json_response(raw)

        if result:
            result = _enrich_llm_serial_result(result, image_bytes)
        duration = time.time() - start_time
        if result:
            if user_id_str and (has_app_context() or getattr(getattr(db, "session", None), "_mock_name", None)):
                record_telemetry("gemini", user_id_str, duration, operation_type="metadata_extraction")
            elif has_app_context():
                _record_vision_telemetry("gemini", user_id_str, duration, status="success")
        else:
            _record_vision_telemetry("gemini", user_id_str, duration, status="failed", error_message="Empty or unparseable JSON response")

        return result

    except (ImportError, AttributeError) as e:
        logger.error("google-genai package is not installed or API surface changed: %s", e)
        _record_vision_telemetry("gemini", user_id_str, time.time() - start_time, status="failed", error_message=str(e))
    except api_error_cls as e:
        logger.warning("Gemini API rejected cover extraction request (%s); falling back.", e)
        _record_vision_telemetry("gemini", user_id_str, time.time() - start_time, status="failed", error_message=str(e))
    except (ValueError, KeyError, TypeError, OSError, RuntimeError, ConnectionError) as e:
        logger.error("Gemini vision extraction failed: %s", e)
        _record_vision_telemetry("gemini", user_id_str, time.time() - start_time, status="failed", error_message=str(e))

    return None


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=3),
    retry=retry_if_exception_type(requests.exceptions.ConnectionError),
    reraise=True,
)
def _call_ollama_api(url, payload, timeout: int | None = None):
    # Vision inference on a local model is slower than its text counterpart: the
    # same model needed 45.7s cold and 9.1s warm on a real pairing run, so a 30s
    # ceiling cuts off a cold start that would otherwise succeed. Overridable
    # because the right value depends on the host, and an OCI Free Tier ARM box
    # is slower still -- a hardcoded number here is wrong for somebody.
    effective_timeout = timeout if timeout is not None else int(os.environ.get("OLLAMA_VISION_TIMEOUT", "90"))
    response = requests.post(f"{url}/api/generate", json=payload, timeout=effective_timeout)
    response.raise_for_status()
    return response


def _extract_via_ollama(image_bytes: bytes, user_id: str | uuid.UUID | None = None) -> dict | None:
    if not _is_llm_enabled():
        logger.debug("Ollama vision extraction skipped: ALLOW_LLM is false.")
        return None

    url = _resolve_ollama_base_url()
    model = str(ConfigService.get("OLLAMA_VISION_MODEL") or "llava").strip()
    raw_timeout = ConfigService.get("OLLAMA_VISION_TIMEOUT") or os.environ.get("OLLAMA_VISION_TIMEOUT")
    try:
        fast_timeout = int(raw_timeout) if raw_timeout not in (None, "") else 25
    except (ValueError, TypeError):
        fast_timeout = 25

    start_time = time.time()
    try:
        normalized_bytes, _ = _normalize_cover_image_bytes(image_bytes, max_dim=768)
        b64_image = base64.b64encode(normalized_bytes).decode("utf-8")
        payload = {
            "model": model,
            "prompt": PROMPT,
            "images": [b64_image],
            "stream": False,
            "format": "json",
            "options": {"num_predict": 220, "temperature": 0.1},
        }

        response = _call_ollama_api(url, payload, timeout=fast_timeout)

        data = response.json()
        raw = data.get("response", "").strip()
        result = _parse_json_response(raw)
        if result:
            result = _enrich_llm_serial_result(result, image_bytes)
        duration = time.time() - start_time
        _record_vision_telemetry(
            "ollama",
            user_id,
            duration,
            status="success" if result else "failed",
            error_message=None if result else f"Empty or unparseable JSON from model {model}",
        )
        return result

    except requests.exceptions.RequestException as e:
        msg = str(e)
        err_resp = getattr(e, "response", None)
        if err_resp is not None and getattr(err_resp, "status_code", None) == 404:
            msg = f"Model '{model}' not found on Ollama. Run 'ollama pull {model}' to fix."
        logger.error("Ollama HTTP extraction failed: %s", msg)
        _record_vision_telemetry(
            "ollama",
            user_id,
            time.time() - start_time,
            status="failed",
            error_message=f"{type(e).__name__}: {msg}",
        )

    return None


def _pick_serial_headline(lines: list[str]) -> str | None:
    """Pick the cleanest prominent headline from magazine cover OCR lines."""
    noise_re = re.compile(r"^(?:cena|www\.|http|issn|indeks|nr\b|no\.?\b|9\s*77|\d+[\d\s.,/>-]*$)", re.IGNORECASE)
    garbage_re = re.compile(r"[-_=~|]{2,}")
    candidates: list[tuple[int, str]] = []
    for line in lines:
        cleaned = line.strip()
        if len(cleaned) < 5 or noise_re.search(cleaned) or garbage_re.search(cleaned):
            continue
        if "national geographic" in cleaned.lower():
            continue
        words = [w for w in re.findall(r"[A-Za-zÀ-ÿ]+", cleaned) if len(w) >= 3]
        alpha_chars = sum(1 for ch in cleaned if ch.isalpha())
        if words and alpha_chars >= 5:
            candidates.append((alpha_chars, cleaned))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def _upscale_crop_for_ocr(crop: Any, min_width: int = 1200) -> Any:
    """Upscale small regional crops so thin masthead and barcode glyphs stay legible."""
    from PIL import Image

    cw, ch = crop.size
    if cw <= 0 or ch <= 0:
        return crop
    if cw < min_width:
        scale = min(3.0, float(min_width) / float(cw))
        return crop.resize((max(1, int(cw * scale)), max(1, int(ch * scale))), Image.Resampling.BICUBIC)
    return crop


def _run_multizone_serial_ocr(img: Any, pytesseract_mod: Any, lang: str | None) -> str:
    """Run targeted OCR on inner top masthead (normal + inverted) and bottom barcode corners."""
    from PIL import ImageOps

    w, h = img.size
    gray = img.convert("L")
    ocr_kwargs = {"lang": lang, "config": "--psm 6"} if lang else {"config": "--psm 6"}
    zone_texts: list[str] = []

    top_bands = (
        gray.crop((int(w * 0.28), int(h * 0.03), int(w * 0.92), max(int(h * 0.105), 1))),
        gray.crop((0, 0, w, max(1, int(h * 0.14)))),
    )
    for top_strip in top_bands:
        scaled = _upscale_crop_for_ocr(top_strip, min_width=1400)
        for variant in (ImageOps.autocontrast(scaled), ImageOps.autocontrast(ImageOps.invert(scaled))):
            t = pytesseract_mod.image_to_string(variant, **ocr_kwargs).strip()
            if t:
                zone_texts.append(t)

    bot_right = _upscale_crop_for_ocr(gray.crop((int(w * 0.58), int(h * 0.74), int(w * 0.96), int(h * 0.94))), min_width=1200)
    bot_left = _upscale_crop_for_ocr(gray.crop((int(w * 0.06), int(h * 0.74), int(w * 0.44), int(h * 0.94))), min_width=1200)
    for raw_crop in (bot_right, bot_left, bot_right.rotate(90, expand=True), bot_left.rotate(270, expand=True)):
        crop = ImageOps.autocontrast(raw_crop)
        t = pytesseract_mod.image_to_string(crop, **ocr_kwargs).strip()
        if t:
            zone_texts.append(t)

    return "\n".join(zone_texts)


def _enrich_llm_serial_result(result: dict[str, Any], image_bytes: bytes) -> dict[str, Any]:
    """Overlay deterministic barcode/masthead OCR and Biblioteka Narodowa lookup onto LLM output."""
    try:
        import pytesseract
        from PIL import Image, ImageOps

        prev_max = Image.MAX_IMAGE_PIXELS
        if isinstance(prev_max, int) and prev_max < _MAX_COVER_PIXELS:
            Image.MAX_IMAGE_PIXELS = _MAX_COVER_PIXELS
        try:
            img = Image.open(io.BytesIO(image_bytes))
        finally:
            Image.MAX_IMAGE_PIXELS = prev_max

        if not (hasattr(img, "size") and isinstance(getattr(img, "size", None), tuple) and len(img.size) == 2):
            return result

        img = ImageOps.exif_transpose(img)
        lang: str | None = None
        try:
            if "pol" in pytesseract.get_languages():
                lang = "pol+eng"
        except (OSError, RuntimeError, TypeError):
            lang = None

        zone_text = _run_multizone_serial_ocr(img, pytesseract, lang)
        from app.utils.issn import parse_cover_issue_label

        ocr_hints = parse_cover_issue_label(zone_text)
        enriched = dict(result)
        for key in (
            "issn",
            "ean",
            "ean_addon",
            "indeks",
            "issue_number",
            "cumulative_issue_number",
            "publication_month",
            "publication_year",
        ):
            if key in ocr_hints and ocr_hints[key] not in (None, ""):
                enriched[key] = ocr_hints[key]

        issn_val = enriched.get("issn")
        if issn_val:
            try:
                from app.strategies.serials import SerialLookupStrategy

                serial_meta, _ = SerialLookupStrategy().lookup(str(issn_val))
                if isinstance(serial_meta, dict):
                    if serial_meta.get("Title") or serial_meta.get("title"):
                        enriched["Title"] = str(serial_meta.get("Title") or serial_meta.get("title"))
                    if serial_meta.get("publisher"):
                        enriched["Publisher"] = str(serial_meta["publisher"])
            except (OSError, ValueError, RuntimeError):
                pass
            if str(enriched.get("ISBN") or "").strip() in ("000000", "0"):
                enriched["ISBN"] = ""
            enriched["Authors"] = []

        return enriched
    except (ImportError, OSError, ValueError, RuntimeError):
        return result


def _extract_via_tesseract(image_bytes: bytes, user_id: str | uuid.UUID | None = None) -> dict | None:
    start_time = time.time()
    try:
        import pytesseract
        from PIL import Image, ImageOps

        prev_max = Image.MAX_IMAGE_PIXELS
        if isinstance(prev_max, int) and prev_max < _MAX_COVER_PIXELS:
            Image.MAX_IMAGE_PIXELS = _MAX_COVER_PIXELS
        try:
            img = Image.open(io.BytesIO(image_bytes))
        finally:
            Image.MAX_IMAGE_PIXELS = prev_max

        is_real_pil_image = hasattr(img, "size") and isinstance(getattr(img, "size", None), tuple) and len(img.size) == 2
        lang: str | None = None
        if is_real_pil_image:
            img = ImageOps.exif_transpose(img)
            try:
                avail_langs = pytesseract.get_languages()
                if "pol" in avail_langs:
                    lang = "pol+eng"
            except (OSError, RuntimeError, TypeError):
                lang = None

            work_img = img.copy()
            if max(work_img.size) > _OCR_MAX_DIMENSION:
                work_img.thumbnail((_OCR_MAX_DIMENSION, _OCR_MAX_DIMENSION), Image.Resampling.LANCZOS)
            text = pytesseract.image_to_string(work_img, **({"lang": lang} if lang else {})).strip()
            zone_text = _run_multizone_serial_ocr(img, pytesseract, lang)
            combined_text = "\n".join(part for part in (text, zone_text) if part)
        else:
            text = pytesseract.image_to_string(img).strip()
            combined_text = text

        if not combined_text.strip():
            _record_vision_telemetry("tesseract", user_id, time.time() - start_time, status="failed", error_message="No OCR text detected")
            return None

        lines = [line.strip() for line in (text or combined_text).splitlines() if line.strip()]
        if not lines:
            _record_vision_telemetry("tesseract", user_id, time.time() - start_time, status="failed", error_message="No OCR lines detected")
            return None

        from app.utils.issn import parse_cover_issue_label

        serial_hints = parse_cover_issue_label(combined_text)
        if serial_hints.get("issn"):
            title = lines[0]
            publisher = ""
            try:
                from app.strategies.serials import SerialLookupStrategy

                serial_meta, _ = SerialLookupStrategy().lookup(serial_hints["issn"])
                if isinstance(serial_meta, dict):
                    title = str(serial_meta.get("Title") or serial_meta.get("title") or title)
                    publisher = str(serial_meta.get("publisher") or "")
            except (OSError, ValueError, RuntimeError):
                pass

            payload: dict[str, object] = {"Title": title, "Authors": []}
            if publisher:
                payload["Publisher"] = publisher
            payload.update(serial_hints)
            headline = _pick_serial_headline(lines)
            if headline and "cover_headline" not in payload:
                payload["cover_headline"] = headline
            _record_vision_telemetry("tesseract", user_id, time.time() - start_time, status="success")
            return payload

        title = lines[0]
        authors = lines[1:] if len(lines) > 1 else []
        payload = {"Title": title, "Authors": authors}
        if serial_hints:
            payload.update(serial_hints)
        _record_vision_telemetry("tesseract", user_id, time.time() - start_time, status="success")
        return payload

    except ImportError as e:
        logger.error("pytesseract or Pillow is not installed.")
        _record_vision_telemetry("tesseract", user_id, time.time() - start_time, status="failed", error_message=str(e))
    except (OSError, ValueError, RuntimeError) as e:
        msg = str(e)
        if "tesseract is not installed" in msg:
            msg = "tesseract-ocr not found on host. On macOS, run 'brew install tesseract'."
        logger.error("Tesseract extraction failed: %s", msg)
        _record_vision_telemetry("tesseract", user_id, time.time() - start_time, status="failed", error_message=msg)

    return None


def get_llm_vision_status(probe_ollama: bool = False) -> dict[str, Any]:
    """Return health & readiness summary for Gemini, OpenAI, Ollama Vision/Dedupe, and Tesseract."""
    from app.db.models import InstanceSettings

    configured_keys = set(InstanceSettings.get_configured_keys())
    allow_llm = _is_llm_enabled()

    gemini_db = "GEMINI_API_KEY" in configured_keys
    gemini_env = bool(os.getenv("GEMINI_API_KEY"))
    gemini_configured = gemini_db or gemini_env
    gemini_source = "db" if gemini_db else ("env" if gemini_env else "missing")

    openai_db = "OPENAI_API_KEY" in configured_keys
    openai_env = bool(os.getenv("OPENAI_API_KEY"))
    openai_configured = openai_db or openai_env
    openai_source = "db" if openai_db else ("env" if openai_env else "missing")

    ollama_url = _resolve_ollama_base_url()
    ollama_vision_model = str(ConfigService.get("OLLAMA_VISION_MODEL") or "llava").strip()
    ollama_dedupe_model = str(ConfigService.get("OLLAMA_DEDUPE_MODEL") or "llama3:latest").strip()

    ollama_reachable = False
    installed_models: list[str] = []
    if probe_ollama:
        try:
            resp = requests.get(f"{ollama_url}/api/tags", timeout=2)
            resp.raise_for_status()
            payload = resp.json()
            installed_models = [
                str(entry.get("name", "")) for entry in (payload.get("models") or []) if isinstance(entry, dict) and entry.get("name")
            ]
            ollama_reachable = True
        except (requests.exceptions.RequestException, ValueError):
            ollama_reachable = False

    def _has_model(target: str) -> bool:
        return any(m == target or m.startswith(f"{target}:") for m in installed_models)

    vision_model_installed = _has_model(ollama_vision_model) if ollama_reachable else False
    dedupe_model_installed = _has_model(ollama_dedupe_model) if ollama_reachable else False

    tesseract_bin = bool(shutil.which("tesseract"))
    tesseract_langs: list[str] = []
    if tesseract_bin:
        try:
            import pytesseract

            tesseract_langs = list(pytesseract.get_languages())
        except (ImportError, OSError, RuntimeError):
            tesseract_langs = []

    vision_ready = allow_llm and (gemini_configured or (ollama_reachable and vision_model_installed))
    return {
        "allow_llm": allow_llm,
        "gemini": {"configured": gemini_configured, "source": gemini_source},
        "openai": {"configured": openai_configured, "source": openai_source},
        "ollama": {
            "url": ollama_url,
            "vision_model": ollama_vision_model,
            "dedupe_model": ollama_dedupe_model,
            "reachable": ollama_reachable,
            "vision_model_installed": vision_model_installed,
            "dedupe_model_installed": dedupe_model_installed,
            "installed_models": installed_models,
        },
        "vision_ready": vision_ready,
        "tesseract": {"installed": tesseract_bin, "languages": tesseract_langs},
    }


def _extract_json_object(raw: str) -> dict | None:
    """Pull the first complete JSON object out of a model response.

    Local vision models do not reliably emit bare JSON. They wrap it in prose
    ("Here is the result: {...} hope that helps"), fence it, or emit more than
    one object. A greedy ``\\{.*\\}`` substring is the obvious fix and is wrong
    twice over: on ``{"Title": "A"} {"Title": "B"}`` it spans both objects and
    fails to parse, and on a response with trailing prose containing a brace it
    captures past the object and fails again.

    ``raw_decode`` returns the first valid JSON value and the index it stopped
    at, so trailing prose and sibling objects are simply left unconsumed.
    """
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", raw):
        try:
            value, _ = decoder.raw_decode(raw[match.start() :])
        except ValueError:
            # Not the start of a valid object -- keep scanning for the next "{".
            continue
        if isinstance(value, dict):
            return value
    return None


def _parse_json_response(raw: str) -> dict | None:
    if not raw:
        return None
    try:
        # String concatenation used here to prevent markdown UI renderer bugs
        ticks = "`" * 3
        raw = re.sub(r"^" + ticks + r"(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*" + ticks + r"$", "", raw)

        data = _extract_json_object(raw)
        if data is None:
            raise ValueError("no complete JSON object found in response")

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

        parsed_payload: dict[str, object] = {
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

        from app.utils.issn import normalize_issn, parse_cover_issue_label

        raw_issn = normalize_issn(str(data.get("ISSN") or data.get("issn") or ""))
        if raw_issn:
            parsed_payload["issn"] = raw_issn
        for src_key, dst_key in (
            ("Indeks", "indeks"),
            ("IssueNumber", "issue_number"),
            ("Volume", "volume"),
            ("CoverHeadline", "cover_headline"),
        ):
            val = data.get(src_key) or data.get(dst_key)
            if val is not None and str(val).strip():
                parsed_payload[dst_key] = str(val).strip()

        for int_src, int_dst in (
            ("CumulativeIssueNumber", "cumulative_issue_number"),
            ("PublicationMonth", "publication_month"),
            ("PublicationYear", "publication_year"),
        ):
            raw_int = data.get(int_src) if data.get(int_src) not in (None, "") else data.get(int_dst)
            if raw_int not in (None, ""):
                try:
                    parsed_payload[int_dst] = int(str(raw_int).strip())
                except ValueError:
                    pass

        headline_or_title = " ".join(
            str(part) for part in (title, subtitle, data.get("CoverHeadline") or "", data.get("ISSN") or "") if part
        )
        inferred_hints = parse_cover_issue_label(headline_or_title)
        for k, v in inferred_hints.items():
            parsed_payload.setdefault(k, v)

        return parsed_payload
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        logger.error("Failed to parse JSON response: %s", e)
        return None

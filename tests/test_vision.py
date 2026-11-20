"""Tests for the vision utility functions."""

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
import os
from unittest.mock import MagicMock, patch

import requests

from app.utils.vision import _extract_via_gemini, _extract_via_ollama, _extract_via_tesseract, extract_metadata_from_cover


@patch("app.utils.vision._extract_via_ollama")
@patch("app.utils.vision._extract_via_tesseract")
@patch.dict(os.environ, {"GEMINI_API_KEY": ""})
def test_extract_waterfall_missing_api_key(mock_tesseract, mock_ollama):
    """Test that missing API key falls back to Ollama and Tesseract."""
    mock_ollama.return_value = None
    mock_tesseract.return_value = None

    result = extract_metadata_from_cover(b"test image")

    assert result is None
    mock_ollama.assert_called_once()
    mock_tesseract.assert_called_once()


@patch("app.utils.vision._extract_via_gemini")
@patch("app.utils.vision._extract_via_ollama")
@patch("app.utils.vision._extract_via_tesseract")
def test_extract_waterfall_gemini_success(mock_tesseract, mock_ollama, mock_gemini):
    mock_gemini.return_value = {"Title": "Dune", "Authors": ["Frank Herbert"]}

    result = extract_metadata_from_cover(b"test image", user_id="00000000-0000-0000-0000-000000000000")

    assert result == {"Title": "Dune", "Authors": ["Frank Herbert"]}
    mock_gemini.assert_called_once()
    mock_ollama.assert_not_called()
    mock_tesseract.assert_not_called()


@patch("app.utils.vision._extract_via_gemini")
@patch("app.utils.vision._extract_via_ollama")
@patch("app.utils.vision._extract_via_tesseract")
def test_extract_waterfall_ollama_success(mock_tesseract, mock_ollama, mock_gemini):
    mock_gemini.return_value = None
    mock_ollama.return_value = {"Title": "Dune", "Authors": ["Frank Herbert"]}

    result = extract_metadata_from_cover(b"test image", user_id="00000000-0000-0000-0000-000000000000")

    assert result == {"Title": "Dune", "Authors": ["Frank Herbert"]}
    mock_gemini.assert_called_once()
    mock_ollama.assert_called_once()
    mock_tesseract.assert_not_called()


@patch("app.utils.vision._extract_via_gemini")
@patch("app.utils.vision._extract_via_ollama")
@patch("app.utils.vision._extract_via_tesseract")
def test_extract_waterfall_tesseract_success(mock_tesseract, mock_ollama, mock_gemini):
    mock_gemini.return_value = None
    mock_ollama.return_value = None
    mock_tesseract.return_value = {"Title": "Dune", "Authors": []}

    result = extract_metadata_from_cover(b"test image", user_id="00000000-0000-0000-0000-000000000000")

    assert result == {"Title": "Dune", "Authors": []}
    mock_gemini.assert_called_once()
    mock_ollama.assert_called_once()
    mock_tesseract.assert_called_once()


@patch("app.utils.vision.Config.ALLOW_LLM", True)
@patch("app.utils.vision.db.session")
@patch("app.utils.llm_covers.record_telemetry")
@patch.dict(os.environ, {"GEMINI_API_KEY": "dummy_key"})
@patch("google.genai.Client", create=True)
def test_extract_gemini_success(mock_client_class, mock_record, mock_session):
    """Test successful extraction for Gemini."""
    mock_user = MagicMock()
    mock_user.has_permission.return_value = True
    mock_session.get.return_value = mock_user

    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_response = MagicMock()
    mock_response.text = '{"Title": "Dune", "Authors": ["Frank Herbert"]}'
    mock_client.models.generate_content.return_value = mock_response

    result = _extract_via_gemini(b"test image", "image/jpeg", user_id="00000000-0000-0000-0000-000000000000")

    assert result == {
        "Title": "Dune",
        "Subtitle": "",
        "Authors": ["Frank Herbert"],
        "Publisher": "",
        "Year": "",
        "ISBN": "",
        "Edition": "",
        "Language": "",
        "Genre": "",
    }


@patch("app.utils.vision.Config.ALLOW_LLM", True)
@patch("app.utils.vision.db.session")
@patch("app.utils.llm_covers.record_telemetry")
@patch.dict(os.environ, {"GEMINI_API_KEY": "dummy_key"})
@patch("google.genai.Client", create=True)
def test_extract_gemini_with_markdown_fences(mock_client_class, mock_record, mock_session):
    """Test successful extraction when model wraps the JSON in markdown code blocks."""
    mock_user = MagicMock()
    mock_user.has_permission.return_value = True
    mock_session.get.return_value = mock_user

    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_response = MagicMock()
    mock_response.text = '```json\n{"Title": "Dune 2", "Authors": ["Frank Herbert"]}\n```'
    mock_client.models.generate_content.return_value = mock_response

    result = _extract_via_gemini(b"test image", "image/jpeg", user_id="00000000-0000-0000-0000-000000000000")

    assert result == {
        "Title": "Dune 2",
        "Subtitle": "",
        "Authors": ["Frank Herbert"],
        "Publisher": "",
        "Year": "",
        "ISBN": "",
        "Edition": "",
        "Language": "",
        "Genre": "",
    }


@patch("app.utils.vision.Config.ALLOW_LLM", True)
@patch("app.utils.vision.db.session")
@patch("app.utils.llm_covers.record_telemetry")
@patch.dict(os.environ, {"GEMINI_API_KEY": "dummy_key"})
@patch("google.genai.Client", create=True)
def test_extract_gemini_invalid_json(mock_client_class, mock_record, mock_session):
    """Test handling of invalid JSON response."""
    mock_user = MagicMock()
    mock_user.has_permission.return_value = True
    mock_session.get.return_value = mock_user

    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_response = MagicMock()
    mock_response.text = "This is not JSON"
    mock_client.models.generate_content.return_value = mock_response

    result = _extract_via_gemini(b"test image", "image/jpeg", user_id="00000000-0000-0000-0000-000000000000")

    assert result is None


@patch("app.utils.vision.Config.ALLOW_LLM", True)
@patch("requests.post")
def test_extract_ollama_success(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {"response": '{"Title": "Dune", "Authors": ["Frank Herbert"]}'}
    mock_post.return_value = mock_response

    result = _extract_via_ollama(b"test image")

    assert result == {
        "Title": "Dune",
        "Subtitle": "",
        "Authors": ["Frank Herbert"],
        "Publisher": "",
        "Year": "",
        "ISBN": "",
        "Edition": "",
        "Language": "",
        "Genre": "",
    }


@patch.dict("sys.modules", {"pytesseract": MagicMock(), "PIL": MagicMock(), "PIL.Image": MagicMock()})
def test_extract_tesseract_success():
    import sys

    sys.modules["pytesseract"].image_to_string.return_value = "Dune\n\nFrank Herbert"

    result = _extract_via_tesseract(b"test image")

    assert result == {"Title": "Dune", "Authors": ["Frank Herbert"]}


@patch("app.utils.vision.Config.ALLOW_LLM", True)
@patch("app.utils.vision.db.session")
def test_extract_gemini_blocked_without_cloud_privilege(mock_session):
    """Test that Gemini extraction returns None if user lacks cloud privilege, even with API key."""
    mock_user = MagicMock()
    mock_user.has_permission.return_value = False
    mock_session.get.return_value = mock_user

    with patch.dict(os.environ, {"GEMINI_API_KEY": "dummy_key"}):
        result = _extract_via_gemini(b"test", "image/jpeg", user_id="00000000-0000-0000-0000-000000000000")
        assert result is None


def test_parse_authors_comma_separated_string():
    """Test that _parse_json_response splits comma-separated author string."""
    from app.utils.vision import _parse_json_response

    res = _parse_json_response('{"Title": "Dune", "Authors": "Frank Herbert, Brian Herbert"}')
    assert res == {
        "Title": "Dune",
        "Subtitle": "",
        "Authors": ["Frank Herbert", "Brian Herbert"],
        "Publisher": "",
        "Year": "",
        "ISBN": "",
        "Edition": "",
        "Language": "",
        "Genre": "",
    }


@patch("app.utils.vision._extract_via_gemini")
@patch("app.utils.vision._extract_via_ollama")
@patch("app.utils.vision._extract_via_tesseract")
def test_extract_waterfall_gemini_exception_falls_to_ollama(mock_tesseract, mock_ollama, mock_gemini):
    """Verify that an exception in Gemini correctly triggers Ollama."""
    mock_gemini.side_effect = RuntimeError("Gemini is down")
    mock_ollama.return_value = {"Title": "Ollama Result", "Authors": ["Ollama Author"]}

    result = extract_metadata_from_cover(b"test image")

    assert result == {"Title": "Ollama Result", "Authors": ["Ollama Author"]}
    mock_gemini.assert_called_once()
    mock_ollama.assert_called_once()
    mock_tesseract.assert_not_called()


@patch("app.utils.vision._extract_via_gemini")
@patch("app.utils.vision._extract_via_ollama")
@patch("app.utils.vision._extract_via_tesseract")
def test_extract_waterfall_ollama_exception_falls_to_tesseract(mock_tesseract, mock_ollama, mock_gemini):
    """Verify that an exception in Ollama correctly triggers Tesseract."""
    mock_gemini.return_value = None
    mock_ollama.side_effect = requests.exceptions.RequestException("Ollama connection failed")
    mock_tesseract.return_value = {"Title": "Tesseract Result", "Authors": []}

    result = extract_metadata_from_cover(b"test image")

    assert result == {"Title": "Tesseract Result", "Authors": []}
    mock_gemini.assert_called_once()
    mock_ollama.assert_called_once()
    mock_tesseract.assert_called_once()


@patch("app.utils.vision._extract_via_gemini")
@patch("app.utils.vision._extract_via_ollama")
@patch("app.utils.vision._extract_via_tesseract")
def test_extract_waterfall_all_exception_returns_none(mock_tesseract, mock_ollama, mock_gemini):
    """Verify that exceptions in all methods result in a None return."""
    mock_gemini.side_effect = RuntimeError("Gemini Error")
    mock_ollama.side_effect = requests.exceptions.RequestException("Ollama Error")
    mock_tesseract.side_effect = RuntimeError("Tesseract Error")

    result = extract_metadata_from_cover(b"test image")

    assert result is None


@patch("app.utils.vision._extract_via_gemini")
@patch("app.utils.vision._extract_via_ollama")
@patch("app.utils.vision._extract_via_tesseract")
def test_extract_waterfall_gemini_api_error_falls_to_ollama(mock_tesseract, mock_ollama, mock_gemini):
    """Verify that a 3rd party API exception in Gemini correctly triggers Ollama."""

    mock_gemini.side_effect = RuntimeError("Gemini API Error")
    mock_ollama.return_value = {"Title": "Ollama Result", "Authors": ["Ollama Author"]}

    result = extract_metadata_from_cover(b"test image", user_id="00000000-0000-0000-0000-000000000000")

    assert result == {"Title": "Ollama Result", "Authors": ["Ollama Author"]}
    mock_gemini.assert_called_once()
    mock_ollama.assert_called_once()
    mock_tesseract.assert_not_called()


@patch("app.utils.vision._extract_via_gemini")
@patch("app.utils.vision._extract_via_ollama")
@patch("app.utils.vision._extract_via_tesseract")
def test_extract_waterfall_ollama_json_decode_error_falls_to_tesseract(mock_tesseract, mock_ollama, mock_gemini):
    """Verify that an invalid JSON response from Ollama falls back to Tesseract."""
    mock_gemini.return_value = None
    mock_ollama.side_effect = json.JSONDecodeError("Expecting value", "doc", 0)
    mock_tesseract.return_value = {"Title": "Tesseract Result", "Authors": []}

    result = extract_metadata_from_cover(b"test image", user_id="00000000-0000-0000-0000-000000000000")

    assert result == {"Title": "Tesseract Result", "Authors": []}
    mock_gemini.assert_called_once()
    mock_ollama.assert_called_once()
    mock_tesseract.assert_called_once()


# ---------------------------------------------------------------------------
# C18 2.6 -- MOD-EXT-09: JSON extraction from noisy model output
#
# A local vision model does not reliably emit bare JSON. The previous parser
# accepted only a fenced or bare payload, so any surrounding prose produced
# None and silently fell through to Tesseract. The obvious fix -- a greedy
# r"\{.*\}" substring -- is wrong: it spans sibling objects and swallows
# trailing braces. raw_decode() consumes exactly one object and stops.
# ---------------------------------------------------------------------------


def test_parse_json_response_accepts_prose_wrapped_object():
    """The regression: a valid payload wrapped in prose used to return None."""
    from app.utils.vision import _parse_json_response

    res = _parse_json_response('Here is the result: {"Title": "Dune"} Hope that helps!')
    assert res is not None
    assert res["Title"] == "Dune"


def test_parse_json_response_takes_first_of_several_objects():
    """A greedy .*} would span both objects and fail to parse at all."""
    from app.utils.vision import _parse_json_response

    res = _parse_json_response('{"Title": "First"} {"Title": "Second"}')
    assert res is not None
    assert res["Title"] == "First"


def test_parse_json_response_tolerates_trailing_brace_in_prose():
    """Trailing prose containing a brace must not swallow the real object."""
    from app.utils.vision import _parse_json_response

    res = _parse_json_response('Result: {"Title": "Dune", "Genre": "sci-fi"} (2020) {note}')
    assert res is not None
    assert res["Title"] == "Dune"
    assert res["Genre"] == "sci-fi"


def test_parse_json_response_skips_a_non_object_brace_run():
    """A stray "{not json}" before the real object must not win."""
    from app.utils.vision import _parse_json_response

    res = _parse_json_response('{not json at all} {"Title": "Real"}')
    assert res is not None
    assert res["Title"] == "Real"


def test_parse_json_response_still_handles_fenced_and_bare_payloads():
    """The two shapes that already worked must keep working."""
    from app.utils.vision import _parse_json_response

    assert _parse_json_response('{"Title": "Bare"}')["Title"] == "Bare"
    assert _parse_json_response('```json\n{"Title": "Fenced"}\n```')["Title"] == "Fenced"


def test_parse_json_response_returns_none_without_a_json_object():
    """No object anywhere still yields None, so the Tesseract fallback runs."""
    from app.utils.vision import _parse_json_response

    assert _parse_json_response("I could not read that image.") is None
    assert _parse_json_response("") is None
    # A bare JSON array is not the expected shape and must not be coerced.
    assert _parse_json_response("[1, 2, 3]") is None


def test_ollama_vision_timeout_is_overridable(monkeypatch):
    """30s cut off a 45.7s cold start; the value depends on the host."""
    from app.utils import vision

    captured = {}

    class _Resp:
        @staticmethod
        def raise_for_status():
            return None

    def fake_post(url, json, timeout):  # noqa: A002 - mirrors requests.post signature
        captured["timeout"] = timeout
        return _Resp()

    monkeypatch.setattr(requests, "post", fake_post)

    monkeypatch.delenv("OLLAMA_VISION_TIMEOUT", raising=False)
    vision._call_ollama_api("http://ollama.local", {})
    assert captured["timeout"] == 90, "default must clear the measured 45.7s cold start"

    monkeypatch.setenv("OLLAMA_VISION_TIMEOUT", "180")
    vision._call_ollama_api("http://ollama.local", {})
    assert captured["timeout"] == 180, "a slower host must be able to raise the ceiling"


def test_normalize_cover_image_bytes_downscales_oversized_image():
    """Large camera images are downscaled cleanly without raising DecompressionBombError."""
    import io

    from PIL import Image

    from app.utils.vision import _normalize_cover_image_bytes

    buf = io.BytesIO()
    Image.new("RGB", (3000, 4000), color="yellow").save(buf, format="JPEG")
    out_bytes, mime = _normalize_cover_image_bytes(buf.getvalue(), max_dim=1200)
    assert mime == "image/jpeg"
    with Image.open(io.BytesIO(out_bytes)) as resized:
        assert max(resized.size) <= 1200


def test_extract_via_tesseract_enriches_serial_by_issn(monkeypatch):
    """When Tesseract detects an ISSN on a magazine cover, Title/Publisher come from SerialLookupStrategy."""
    import io

    import pytesseract
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (600, 800), color="white").save(buf, format="JPEG")

    monkeypatch.setattr(pytesseract, "get_languages", lambda: ["eng"])
    monkeypatch.setattr(
        pytesseract,
        "image_to_string",
        lambda *_a, **_kw: "wr --- is\nNR 7(58) LIPIEC 2004\nKOKAINA\nISSN 1507-5966 INDEKS 323357\n07>",
    )
    monkeypatch.setattr(
        "app.strategies.serials.SerialLookupStrategy.lookup",
        lambda _self, _q: ({"Title": "National Geographic Polska", "publisher": "G+J RBA"}, "biblioteka_narodowa"),
    )

    result = _extract_via_tesseract(buf.getvalue())
    assert result is not None
    assert result["Title"] == "National Geographic Polska"
    assert result["Publisher"] == "G+J RBA"
    assert result["Authors"] == []
    assert result["issn"] == "1507-5966"
    assert result["issue_number"] == "7"
    assert result["cumulative_issue_number"] == 58
    assert result["publication_month"] == 7
    assert result["publication_year"] == 2004
    assert result["ean_addon"] == "07"
    assert result["cover_headline"] == "KOKAINA"


def test_get_llm_vision_status_reports_providers_and_ollama_models(app, monkeypatch):
    """get_llm_vision_status reports ALLOW_LLM, Gemini, OpenAI, Ollama vision model readiness, and Tesseract."""
    from app.utils.vision import get_llm_vision_status

    class _FakeResp:
        def raise_for_status(self):
            return None

        @staticmethod
        def json():
            return {"models": [{"name": "llama3:latest"}, {"name": "llava:latest"}]}

    monkeypatch.setattr(requests, "get", lambda *_a, **_kw: _FakeResp())
    monkeypatch.setattr("app.utils.vision.Config.ALLOW_LLM", True)
    monkeypatch.setenv("OLLAMA_VISION_MODEL", "llava")

    with app.app_context():
        status = get_llm_vision_status(probe_ollama=True)

    assert status["allow_llm"] is True
    assert status["ollama"]["reachable"] is True
    assert status["ollama"]["vision_model_installed"] is True
    assert status["ollama"]["dedupe_model_installed"] is True
    assert status["vision_ready"] is True


@patch("app.utils.vision.Config.ALLOW_LLM", True)
@patch("app.utils.vision.db.session")
@patch("app.utils.llm_covers.record_telemetry")
@patch.dict(os.environ, {"GEMINI_API_KEY": "dummy_key"})
@patch("google.genai.Client", create=True)
def test_extract_gemini_accepts_uuid_object_user_id(mock_client_class, mock_record, mock_session):
    """Gemini extraction must accept uuid.UUID user_id objects from g.user_id without crashing."""
    import uuid

    uid = uuid.UUID("00000000-0000-0000-0000-000000000001")
    mock_user = MagicMock()
    mock_user.has_permission.return_value = True
    mock_session.get.return_value = mock_user

    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_response = MagicMock()
    mock_response.text = '{"Title": "Dune", "Authors": ["Frank Herbert"]}'
    mock_client.models.generate_content.return_value = mock_response

    result = _extract_via_gemini(b"test image", "image/jpeg", user_id=uid)
    assert result is not None
    assert result["Title"] == "Dune"
    mock_session.get.assert_called_once()
    mock_record.assert_called_once()
    assert isinstance(mock_record.call_args.args[1], str)


@patch("app.utils.vision.Config.ALLOW_LLM", True)
@patch("app.utils.vision._extract_via_gemini", return_value=None)
@patch("app.utils.vision._extract_via_tesseract", return_value={"Title": "Fallback", "Authors": []})
@patch("requests.post", side_effect=requests.exceptions.ReadTimeout("slow llava"))
def test_ollama_read_timeout_does_not_retry_and_falls_back_immediately(mock_post, mock_tess, _mock_gem):
    """ReadTimeout on Ollama must not retry 3x and must fall straight back to Tesseract."""
    result = extract_metadata_from_cover(b"test image")
    assert result == {"Title": "Fallback", "Authors": []}
    assert mock_post.call_count == 1
    mock_tess.assert_called_once()


@patch("app.utils.vision.Config.ALLOW_LLM", True)
@patch("app.utils.vision.db.session")
@patch("app.utils.llm_covers.record_telemetry")
@patch.dict(os.environ, {"GEMINI_API_KEY": "bad_key"})
@patch("google.genai.Client", create=True)
def test_extract_via_gemini_records_failed_telemetry(mock_client_class, mock_record, mock_session):
    """Gemini API failure records a 'failed' telemetry row rather than staying invisible."""
    mock_user = MagicMock()
    mock_user.has_permission.return_value = True
    mock_session.get.return_value = mock_user

    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.models.generate_content.side_effect = RuntimeError("400 API key not valid")

    result = _extract_via_gemini(b"test image", "image/jpeg", user_id="00000000-0000-0000-0000-000000000000")
    assert result is None
    mock_record.assert_called_once()
    assert mock_record.call_args.args[0] == "gemini"
    assert mock_record.call_args.kwargs["operation_type"] == "metadata_extraction"
    assert mock_record.call_args.kwargs["status"] == "failed"
    assert "400 API key not valid" in (mock_record.call_args.kwargs["error_message"] or "")


@patch("app.utils.vision.Config.ALLOW_LLM", True)
@patch("app.utils.vision.db.session")
@patch("app.utils.llm_covers.record_telemetry")
@patch("requests.post", side_effect=requests.exceptions.ReadTimeout("timed out"))
def test_extract_via_ollama_records_failed_telemetry(mock_post, mock_record, _mock_session):
    """Ollama timeout records a 'failed' telemetry row with error details."""
    result = _extract_via_ollama(b"test image", user_id="00000000-0000-0000-0000-000000000000")
    assert result is None
    mock_post.assert_called_once()
    mock_record.assert_called_once()
    assert mock_record.call_args.args[0] == "ollama"
    assert mock_record.call_args.kwargs["operation_type"] == "metadata_extraction"
    assert mock_record.call_args.kwargs["status"] == "failed"


@patch("app.utils.vision.db.session")
@patch("app.utils.llm_covers.record_telemetry")
@patch("pytesseract.image_to_string", return_value="Tesseract Book\nSome Author")
@patch("PIL.Image.open")
def test_extract_via_tesseract_records_success_telemetry(mock_open, _mock_ocr, mock_record, _mock_session):
    """Tesseract OCR fallback records a 'success' telemetry row when producing metadata."""
    mock_open.return_value = MagicMock()
    result = _extract_via_tesseract(b"test image", user_id="00000000-0000-0000-0000-000000000000")
    assert result is not None
    assert result["Title"] == "Tesseract Book"
    mock_record.assert_called_once()
    assert mock_record.call_args.args[0] == "tesseract"
    assert mock_record.call_args.kwargs["operation_type"] == "metadata_extraction"
    assert mock_record.call_args.kwargs["status"] == "success"


def test_pick_serial_headline_filters_dynamic_serial_title():
    """_pick_serial_headline filters out the resolved serial title rather than a hardcoded name."""
    from app.utils.vision import _pick_serial_headline

    lines = ["Polityka", "ISSN 0032-3500", "Wielka zmiana gospodarcza", "Nr 42"]
    assert _pick_serial_headline(lines, serial_title="Polityka") == "Wielka zmiana gospodarcza"


def test_get_llm_vision_status_ollama_only_without_probe(app, monkeypatch):
    """vision_ready reflects explicitly configured Ollama-only deployments even when probe_ollama=False."""
    from app.utils.vision import get_llm_vision_status

    monkeypatch.setattr("app.utils.vision.Config.ALLOW_LLM", True)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("OLLAMA_URL", "http://ollama.local:11434")
    monkeypatch.setenv("OLLAMA_VISION_MODEL", "llava")

    with app.app_context():
        status = get_llm_vision_status(probe_ollama=False)

    assert status["vision_ready"] is True

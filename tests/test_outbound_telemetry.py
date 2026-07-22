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
"""Unit tests for outbound HTTP request telemetry extraction, span attributes, and redaction."""

from unittest.mock import MagicMock, patch

from app.core.telemetry import record_outbound_telemetry, sanitize_headers


def test_sanitize_headers_redacts_sensitive_values() -> None:
    """Verify that sanitize_headers redacts Authorization, tokens, keys, and secrets."""
    headers = {
        "User-Agent": "iqoqo/0.7.9 (+https://iqoqo.cc)",
        "Accept": "application/json",
        "Authorization": "Bearer secret_token_123",
        "X-API-Key": "my-secret-key",
        "Client-Secret": "super_secret",
    }
    sanitized = sanitize_headers(headers)

    assert sanitized["User-Agent"] == "iqoqo/0.7.9 (+https://iqoqo.cc)"
    assert sanitized["Accept"] == "application/json"
    assert sanitized["Authorization"] == "***REDACTED***"
    assert sanitized["X-API-Key"] == "***REDACTED***"
    assert sanitized["Client-Secret"] == "***REDACTED***"


@patch("app.core.telemetry.logger")
def test_record_outbound_telemetry_recording_span(mock_logger: MagicMock) -> None:
    """Verify record_outbound_telemetry sets span attributes and emits structured logs."""
    mock_span = MagicMock()
    mock_span.is_recording.return_value = True

    with patch("opentelemetry.trace.get_current_span", return_value=mock_span):
        headers = {
            "User-Agent": "iqoqo/0.7.9 (+https://iqoqo.cc)",
            "Accept": "application/vnd.allegro.public.v1+json",
            "Authorization": "Bearer token123",
        }
        res = record_outbound_telemetry("Allegro", headers, url="https://api.allegro.pl/sale/products")

    assert res["Authorization"] == "***REDACTED***"

    # Verify span attributes set
    mock_span.set_attribute.assert_any_call("http.request.header.user_agent", "iqoqo/0.7.9 (+https://iqoqo.cc)")
    mock_span.set_attribute.assert_any_call("http.request.header.accept", "application/vnd.allegro.public.v1+json")
    mock_span.set_attribute.assert_any_call("http.request.header.authorization", "***REDACTED***")
    mock_span.set_attribute.assert_any_call("peer.service", "Allegro")
    mock_span.set_attribute.assert_any_call("http.url", "https://api.allegro.pl/sale/products")

    # Verify logger called with structured extra
    mock_logger.info.assert_called_once()
    called_extra = mock_logger.info.call_args[1].get("extra", {})
    assert called_extra.get("peer.service") == "Allegro"
    assert called_extra.get("http.request.header.authorization") == "***REDACTED***"
    assert called_extra.get("http.request.header.user_agent") == "iqoqo/0.7.9 (+https://iqoqo.cc)"


@patch("app.utils.covers.record_outbound_telemetry")
@patch("app.utils.covers.requests.get")
def test_download_direct_url_records_telemetry(mock_get: MagicMock, mock_record_telemetry: MagicMock) -> None:
    """Verify download_direct_url attaches Chrome User-Agent and records outbound telemetry."""
    from app.utils.covers import download_direct_url

    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_get.return_value.__enter__.return_value = mock_response

    download_direct_url("item123", "https://example.com/cover.jpg", "CoverSource")

    mock_record_telemetry.assert_called_once()
    called_args = mock_record_telemetry.call_args
    assert called_args[0][0] == "CoverSource"
    assert "User-Agent" in called_args[0][1]
    assert "Chrome" in called_args[0][1]["User-Agent"]
    assert called_args[1].get("url") == "https://example.com/cover.jpg"

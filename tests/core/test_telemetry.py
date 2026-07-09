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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
"""
Unit tests for the OpenTelemetry middleware hooks in app.core.telemetry.

These tests assert that:
- ``request_hook`` redacts the ``Authorization`` header before a span is dispatched.
- ``request_hook`` leaves spans unmodified when no Authorization header is present.
- ``request_hook`` is safe against a None span or a non-recording span.
- ``response_hook`` is a no-op (reserved for future use).
"""

from unittest.mock import MagicMock, call

import pytest

from app.core.telemetry import request_hook, response_hook


class TestRequestHookRedactsAuthHeader:
    """Ensure ``request_hook`` intercepts Authorization headers and marks them [REDACTED]."""

    def test_redacts_bearer_token_when_present(self) -> None:
        """Assert that a Bearer token in HTTP_AUTHORIZATION is overwritten with [REDACTED]."""
        span = MagicMock()
        span.is_recording.return_value = True

        environ = {
            "HTTP_AUTHORIZATION": "Bearer sensitive-token-abc123",
            "PATH_INFO": "/api/secure-endpoint",
        }

        request_hook(span, environ)

        span.set_attribute.assert_called_once_with("http.request.header.authorization", "[REDACTED]")

    def test_does_not_set_attribute_when_authorization_absent(self) -> None:
        """Assert that requests without an Authorization header pass through unmodified."""
        span = MagicMock()
        span.is_recording.return_value = True

        environ = {
            "PATH_INFO": "/api/public-endpoint",
            "REQUEST_METHOD": "GET",
        }

        request_hook(span, environ)

        span.set_attribute.assert_not_called()

    def test_no_op_when_span_is_none(self) -> None:
        """Assert that a None span does not raise and exits cleanly."""
        environ = {"HTTP_AUTHORIZATION": "Bearer token"}

        # Must not raise
        request_hook(None, environ)

    def test_no_op_when_span_is_not_recording(self) -> None:
        """Assert that a non-recording span (e.g. sampled-out) is skipped silently."""
        span = MagicMock()
        span.is_recording.return_value = False

        environ = {"HTTP_AUTHORIZATION": "Bearer token"}

        request_hook(span, environ)

        span.set_attribute.assert_not_called()

    def test_redacts_basic_auth_token(self) -> None:
        """Assert that HTTP Basic Auth (non-Bearer) is also redacted."""
        span = MagicMock()
        span.is_recording.return_value = True

        environ = {
            "HTTP_AUTHORIZATION": "Basic dXNlcjpwYXNzd29yZA==",
            "PATH_INFO": "/api/items/",
        }

        request_hook(span, environ)

        span.set_attribute.assert_called_once_with("http.request.header.authorization", "[REDACTED]")

    def test_tolerates_set_attribute_raising_exception(self) -> None:
        """Assert that internal span errors never propagate to application code."""
        span = MagicMock()
        span.is_recording.return_value = True
        span.set_attribute.side_effect = RuntimeError("span is closed")

        environ = {"HTTP_AUTHORIZATION": "Bearer token"}

        # Must not raise
        request_hook(span, environ)


class TestResponseHook:
    """Verify that response_hook is currently a safe no-op."""

    def test_response_hook_is_noop(self) -> None:
        """Assert that response_hook returns None and performs no side effects."""
        span = MagicMock()
        response_hook(span, "200 OK", [("Content-Type", "application/json")])
        span.set_attribute.assert_not_called()

    def test_response_hook_accepts_none_span(self) -> None:
        """Assert that response_hook tolerates a None span without raising."""
        response_hook(None, "500 Internal Server Error", [])  # must not raise

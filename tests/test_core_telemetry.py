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
"""Tests for the telemetry core module."""

from app.core.telemetry import sanitize_headers


def test_sanitize_headers_redacts_sensitive_info():
    """Ensure sensitive headers including Client-ID and Api-Key are redacted."""
    headers = {"Content-Type": "application/json", "Client-ID": "xxxxx", "Api-Key": "yyyyy", "Authorization": "Bearer token123"}

    sanitized = sanitize_headers(headers)

    assert sanitized["Content-Type"] == "application/json"
    assert sanitized["Client-ID"] == "***REDACTED***"
    assert sanitized["Api-Key"] == "***REDACTED***"
    assert sanitized["Authorization"] == "***REDACTED***"

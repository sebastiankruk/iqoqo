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

"""Tests for SSRF DNS resolution timeout enforcement."""

import concurrent.futures
from unittest.mock import patch

import pytest

from app.utils.http_client import SSRFError, is_safe_url, safe_get


def test_is_safe_url_dns_timeout() -> None:
    """Verifies that is_safe_url returns False when DNS resolution times out."""
    with patch("concurrent.futures.Future.result", side_effect=concurrent.futures.TimeoutError("DNS timed out")):
        assert is_safe_url("http://hanging-dns.example.com/") is False


def test_safe_get_dns_timeout() -> None:
    """Verifies that safe_get raises SSRFError when DNS resolution times out."""
    with patch("concurrent.futures.Future.result", side_effect=concurrent.futures.TimeoutError("DNS timed out")):
        with pytest.raises(SSRFError, match="timed out"):
            safe_get("http://hanging-dns.example.com/")

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
"""Unit tests for opaque keyset cursor encoding/decoding and its edge cases."""

import base64
import json

import pytest

from app.utils.pagination import (
    CURSOR_VERSION,
    MAX_CURSOR_LENGTH,
    InvalidCursorError,
    decode_cursor,
    decode_manifestation_cursor,
    encode_cursor,
    encode_manifestation_cursor,
)

# ── Round-trip ─────────────────────────────────────────────────────────


def test_manifestation_cursor_round_trip():
    token = encode_manifestation_cursor(42)
    assert decode_manifestation_cursor(token) == 42


def test_round_trip_is_stable_for_large_ids():
    token = encode_manifestation_cursor(2**53 + 7)
    assert decode_manifestation_cursor(token) == 2**53 + 7


def test_encoded_cursor_is_url_safe_and_unpadded():
    token = encode_manifestation_cursor(1234)
    assert "=" not in token, token
    assert "+" not in token and "/" not in token, token


def test_encoding_is_deterministic():
    assert encode_manifestation_cursor(99) == encode_manifestation_cursor(99)


def test_cursor_contains_no_raw_delimiters():
    """A raw JSON cursor would break URL query handling; base64 avoids that."""
    token = encode_cursor({"v": CURSOR_VERSION, "id": 5, "note": "a/b?c=d&e"})
    assert "&" not in token
    assert "?" not in token
    assert decode_cursor(token)["note"] == "a/b?c=d&e"


# ── Malformed / hostile input ──────────────────────────────────────────


@pytest.mark.parametrize(
    "token",
    [
        "",
        "!!!not-base64!!!",
        "a",
        "%%%%",
        "e30",  # valid base64 for "{}" but no version
    ],
)
def test_malformed_cursors_raise(token):
    with pytest.raises(InvalidCursorError):
        decode_cursor(token)


def test_non_string_cursor_raises():
    with pytest.raises(InvalidCursorError):
        decode_cursor(None)  # type: ignore[arg-type]


def test_oversized_cursor_rejected():
    with pytest.raises(InvalidCursorError):
        decode_cursor("A" * (MAX_CURSOR_LENGTH + 1))


def test_cursor_with_invalid_utf8_raises():
    token = base64.urlsafe_b64encode(b"\xff\xfe\xfd").decode("ascii").rstrip("=")
    with pytest.raises(InvalidCursorError):
        decode_cursor(token)


def test_cursor_with_non_json_content_raises():
    token = base64.urlsafe_b64encode(b"this is not json").decode("ascii").rstrip("=")
    with pytest.raises(InvalidCursorError):
        decode_cursor(token)


def test_cursor_with_json_array_raises():
    token = base64.urlsafe_b64encode(b"[1,2,3]").decode("ascii").rstrip("=")
    with pytest.raises(InvalidCursorError):
        decode_cursor(token)


def test_unsupported_cursor_version_raises():
    token = encode_cursor({"v": 999, "id": 1})
    with pytest.raises(InvalidCursorError):
        decode_manifestation_cursor(token)


def test_missing_version_raises():
    token = encode_cursor({"id": 1})
    with pytest.raises(InvalidCursorError):
        decode_manifestation_cursor(token)


# ── id payload validation ──────────────────────────────────────────────


@pytest.mark.parametrize("bad_id", [None, "12", 1.5, True, [], {}, -1])
def test_invalid_cursor_ids_rejected(bad_id):
    token = encode_cursor({"v": CURSOR_VERSION, "id": bad_id})
    with pytest.raises(InvalidCursorError):
        decode_manifestation_cursor(token)


def test_missing_id_raises():
    token = encode_cursor({"v": CURSOR_VERSION})
    with pytest.raises(InvalidCursorError):
        decode_manifestation_cursor(token)


def test_boundary_id_one_is_valid():
    assert decode_manifestation_cursor(encode_manifestation_cursor(1)) == 1


def test_start_sentinel_round_trips():
    from app.utils.pagination import CURSOR_START, encode_start_cursor

    assert decode_manifestation_cursor(encode_start_cursor()) == CURSOR_START


def test_encode_rejects_non_serializable_payload():
    with pytest.raises(TypeError):
        encode_cursor({"v": CURSOR_VERSION, "id": object()})


def test_decode_error_message_does_not_echo_token():
    """Error text is surfaced to API clients; it must not reflect the payload."""
    secret = "SUPER_SECRET_TOKEN_VALUE"
    with pytest.raises(InvalidCursorError) as exc:
        decode_cursor(secret)
    assert secret not in str(exc.value)

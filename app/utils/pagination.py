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
"""Opaque keyset cursor encoding and decoding for keyset pagination.

Keyset (seek) pagination avoids the ``O(offset)`` row scans that deep
``OFFSET`` pagination incurs, because the database can jump straight to the
index position implied by the last row of the previous page.

The cursor is an *opaque* client token: clients must round-trip it verbatim
and must not construct or interpret it.  It is a URL-safe base64 encoding of
a small JSON payload.  Because the payload is attacker-controllable, every
decode path is strictly validated and any malformed input raises
:class:`InvalidCursorError` rather than being silently coerced.
"""

import base64
import binascii
import json
from typing import Any

#: Maximum accepted encoded cursor length.  Keeps a hostile client from
#: forcing a large base64 decode (a cheap but avoidable DoS vector).
MAX_CURSOR_LENGTH = 512

#: Bumped if the payload shape ever changes, so old cursors fail loudly
#: instead of being misinterpreted.
CURSOR_VERSION = 1

#: Sentinel id meaning "start of the result set, no lower bound applied".
#: Ids are 1-based primary keys, so 0 can never collide with a real row.
CURSOR_START = 0


class InvalidCursorError(ValueError):
    """Raised when a cursor token is malformed, truncated or out of range."""


def encode_cursor(payload: dict[str, Any]) -> str:
    """Encode a cursor payload into an opaque URL-safe token.

    Parameters
    ----------
    payload:
        JSON-serializable mapping describing the position to resume from.
        For manifestation keyset pagination this is ``{"id": <int>}``.

    Returns
    -------
    str
        URL-safe base64 token with padding stripped.

    Raises
    ------
    TypeError
        If ``payload`` is not JSON-serializable.
    """
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(token: str) -> dict[str, Any]:
    """Decode and validate an opaque cursor token.

    Parameters
    ----------
    token:
        Token previously produced by :func:`encode_cursor`.

    Returns
    -------
    dict
        The decoded payload.

    Raises
    ------
    InvalidCursorError
        If the token is not a string, is empty, exceeds
        :data:`MAX_CURSOR_LENGTH`, is not valid URL-safe base64, does not
        decode to valid UTF-8 JSON, is not a JSON object, or carries an
        unsupported version.
    """
    if not isinstance(token, str):
        raise InvalidCursorError("Cursor must be a string")
    if not token:
        raise InvalidCursorError("Cursor must not be empty")
    if len(token) > MAX_CURSOR_LENGTH:
        raise InvalidCursorError("Cursor is too long")

    # Restore the stripped base64 padding before decoding.
    padding = "=" * (-len(token) % 4)
    try:
        raw = base64.urlsafe_b64decode(token + padding)
    except (binascii.Error, ValueError) as exc:
        raise InvalidCursorError("Cursor is not valid base64") from exc

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidCursorError("Cursor does not contain valid JSON") from exc

    if not isinstance(payload, dict):
        raise InvalidCursorError("Cursor payload must be a JSON object")

    version = payload.get("v")
    if version != CURSOR_VERSION:
        raise InvalidCursorError("Unsupported cursor version")

    return payload


def encode_manifestation_cursor(manifestation_id: int) -> str:
    """Encode a manifest-keyset cursor for the given manifestation id."""
    return encode_cursor({"v": CURSOR_VERSION, "id": int(manifestation_id)})


def decode_manifestation_cursor(token: str) -> int:
    """Decode a manifest-keyset cursor, returning the exclusive ``id`` bound.

    Returns :data:`CURSOR_START` (``0``) for the sentinel cursor that means
    "start of the result set, apply no lower bound".

    Raises
    ------
    InvalidCursorError
        If the token is malformed, carries an unexpected version, or does not
        contain a non-negative integer ``id``.
    """
    payload = decode_cursor(token)
    cursor_id = payload.get("id")

    # bool is a subclass of int; reject it explicitly so True never becomes 1.
    if isinstance(cursor_id, bool) or not isinstance(cursor_id, int):
        raise InvalidCursorError("Cursor id must be an integer")
    if cursor_id < 0:
        raise InvalidCursorError("Cursor id must not be negative")

    return cursor_id


def encode_start_cursor() -> str:
    """Encode the sentinel cursor denoting the first page of a result set."""
    return encode_cursor({"v": CURSOR_VERSION, "id": CURSOR_START})

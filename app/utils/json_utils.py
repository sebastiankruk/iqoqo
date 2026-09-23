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
"""Utilities for JSON serialization/deserialization of metadata fields."""

import json
import re

ARRAY_META_FIELDS = frozenset([
    "authors",
    "translators",
    "illustrators",
    "editors",
    "contributors",
    "tags",
    "genres",
    "mechanics",
    "narrators",
    "publishers",
])


def sanitize_meta(meta: dict | None) -> dict | None:
    """Convert non-native JSON types (dict/list) to JSON strings for frontend compatibility."""
    if not meta:
        return meta
    result = {}
    for key, value in meta.items():
        if isinstance(value, (dict, list)):
            result[key] = json.dumps(value)
        else:
            result[key] = value
    return result


def parse_meta(meta: dict | None) -> dict | None:
    """Parse JSON strings back to objects for backend storage.

    Only attempts to parse strings that look like JSON containers (start with
    '{' or '[') to avoid unintended type coercion (e.g. "00123" -> 123).

    Also normalizes known array fields (authors, tags, etc.) by splitting
    comma/semicolon-separated strings into arrays.
    """
    if not meta:
        return meta
    result = {}
    for key, value in meta.items():
        if isinstance(value, str) and value.strip().startswith(("{", "[")):
            try:
                result[key] = json.loads(value)
                continue
            except (ValueError, TypeError):
                pass

        if key in ARRAY_META_FIELDS:
            if isinstance(value, str):
                # Split on comma or semicolon using regex
                parts = [p.strip() for p in re.split(r'[,;]', value) if p.strip()]
                result[key] = parts if parts else []
            elif isinstance(value, list):
                result[key] = [str(item) for item in value if item is not None]
            elif value is None:
                result[key] = []
            else:
                result[key] = [str(value)]
        else:
            result[key] = value
    return result

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
    """
    if not meta:
        return meta
    result = {}
    for key, value in meta.items():
        if isinstance(value, str) and value.strip().startswith(("{", "[")):
            try:
                result[key] = json.loads(value)
            except (ValueError, TypeError):
                result[key] = value
        else:
            result[key] = value
    return result

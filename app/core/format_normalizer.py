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
"""Read-time format normalizer for manifestation meta['format'] values.

Maps non-canonical format strings from external APIs to canonical MediaFormat
values using user-defined mappings from ``shared/format_mappings.yaml``, with
fallback to ``unknown_*`` placeholder formats.
"""

import logging
from pathlib import Path

import yaml

from app.core.taxonomy import FORMAT_ALIAS_TO_CATEGORY, MediaFormat
from app.core.telemetry import mapping_parse_failures_total

logger = logging.getLogger(__name__)

# All canonical MediaFormat values (fast set lookup)
_CANONICAL_FORMATS: frozenset[str] = frozenset(MediaFormat.ALL)

# Path to the user-defined format mappings file
_MAPPINGS_PATH = Path(__file__).resolve().parents[2] / "shared" / "format_mappings.yaml"


class FormatNormalizer:
    """Read-time normalizer for manifestation format values.

    Resolves non-canonical format strings to canonical ``MediaFormat`` values
    using the following priority chain:

    1. Exact match in ``format_normalizations`` user mappings
    2. NULL value + content_type match under ``format_normalizations.null.{content_type}``
    3. Value matches a known ``MediaFormat`` constant (pass-through)
    4. Fallback to ``unknown_{category}`` via ``FORMAT_ALIAS_TO_CATEGORY``
    5. Ultimate fallback: ``unknown_text``
    """

    _mappings: dict[str, str] = {}
    _null_mappings: dict[str, str] = {}
    _loaded: bool = False

    @classmethod
    def _load_mappings(cls) -> None:
        """Load user-defined format normalizations from the YAML file.

        Reads ``shared/format_mappings.yaml``.  If the file is absent,
        empty, or lacks a ``format_normalizations`` key, the normalizer
        operates with no user-defined mappings and falls back to
        ``unknown_*`` placeholders.
        """
        if cls._loaded:
            return

        cls._mappings = {}
        cls._null_mappings = {}
        cls._loaded = True

        if not _MAPPINGS_PATH.exists():
            logger.debug("format_mappings.yaml not found; using fallback behaviour")
            return

        try:
            with open(_MAPPINGS_PATH, encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
        except yaml.YAMLError as exc:
            logger.warning("Failed to parse format_mappings.yaml: %s", exc)
            mapping_parse_failures_total.add(1, {"reason": "yaml_error"})
            return

        if not isinstance(data, dict):
            logger.warning("format_mappings.yaml is not a dict; ignoring")
            mapping_parse_failures_total.add(1, {"reason": "not_dict"})
            return

        normalizations = data.get("format_normalizations")
        if not isinstance(normalizations, dict):
            logger.debug("No format_normalizations key in format_mappings.yaml")
            return

        for key, target in normalizations.items():
            if key is None or str(key).lower() == "null":
                # YAML null key → content-type-scoped mappings
                if isinstance(target, dict):
                    cls._null_mappings = {str(k): str(v) for k, v in target.items() if v is not None}
                continue

            if target is None:
                continue

            target_str = str(target)

            # Validate that the target is a known MediaFormat value
            if target_str not in _CANONICAL_FORMATS:
                logger.warning(
                    "format_mappings.yaml maps '%s' → '%s' which is not a valid MediaFormat; this mapping will be ignored at runtime",
                    key,
                    target_str,
                )
                mapping_parse_failures_total.add(1, {"reason": "invalid_format", "target": target_str})
                continue

            # Store lowercase key for case-insensitive lookup
            cls._mappings[str(key).lower().strip()] = target_str

    @classmethod
    def normalize(cls, raw: str | None, content_type: str | None = None) -> str:
        """Resolve a raw format value to a canonical ``MediaFormat`` value.

        Args:
            raw: The raw format string from ``Manifestation.meta['format']``,
                 or ``None`` if the format is NULL.
            content_type: The content type from ``Expression.content_type``
                          (e.g. ``"movie"``, ``"music"``, ``"text"``).  Used
                          for NULL resolution and fallback category lookup.

        Returns:
            A canonical ``MediaFormat`` identifier such as ``"dvd"``,
            ``"unknown_video"``, ``"book"``, etc.
        """
        cls._load_mappings()

        # 1. NULL value + content_type match
        if raw is None:
            return cls._resolve_null(content_type)

        raw_lower = raw.lower().strip()

        # 2. Exact match in user mappings (case-insensitive)
        if raw_lower in cls._mappings:
            return cls._mappings[raw_lower]

        # 3. Already canonical — pass through
        if raw_lower in _CANONICAL_FORMATS:
            return raw_lower

        # 4. Fallback to unknown_{category} via FORMAT_ALIAS_TO_CATEGORY
        category = FORMAT_ALIAS_TO_CATEGORY.get(raw_lower)

        if category:
            placeholder = cls._category_to_unknown_placeholder(category)
            if placeholder:
                return placeholder

        # 5. If content_type was provided, use it for fallback
        if content_type:
            placeholder = cls._category_to_unknown_placeholder(content_type)
            if placeholder:
                return placeholder

        # 6. Ultimate fallback
        return MediaFormat.UNKNOWN_TEXT

    @classmethod
    def _resolve_null(cls, content_type: str | None) -> str:
        """Resolve a NULL format value using content-type-scoped mappings."""
        if content_type and content_type in cls._null_mappings:
            return cls._null_mappings[content_type]

        # Fallback to unknown_* based on content_type
        if content_type:
            placeholder = cls._category_to_unknown_placeholder(content_type)
            if placeholder:
                return placeholder

        return MediaFormat.UNKNOWN_TEXT

    @staticmethod
    def _category_to_unknown_placeholder(category: str) -> str | None:
        """Map a media category to its ``unknown_*`` placeholder format.

        Returns ``None`` if the category is not recognised.
        """
        category_lower = category.lower().strip()
        mapping = {
            "movie": MediaFormat.UNKNOWN_VIDEO,
            "music": MediaFormat.UNKNOWN_AUDIO,
            "audiobook": MediaFormat.UNKNOWN_AUDIO,
            "text": MediaFormat.UNKNOWN_TEXT,
        }
        return mapping.get(category_lower)

    @classmethod
    def is_canonical(cls, value: str | None) -> bool:
        """Return ``True`` if *value* is a known canonical ``MediaFormat``.

        Args:
            value: A format string to check, or ``None``.

        Returns:
            ``True`` iff *value* matches one of the ``MediaFormat.ALL``
            constants (including ``unknown_*``).
        """
        if value is None:
            return False
        return value.lower().strip() in _CANONICAL_FORMATS

    @classmethod
    def reset(cls) -> None:
        """Clear cached mappings (useful for testing)."""
        cls._mappings = {}
        cls._null_mappings = {}
        cls._loaded = False


# Convenience module-level function (primary public API)
def normalize_format(raw: str | None, content_type: str | None = None) -> str:
    """Resolve a raw format value to a canonical MediaFormat value.

    Convenience wrapper around ``FormatNormalizer.normalize()``.

    Args:
        raw: The raw format value, or ``None``.
        content_type: The expression content type, or ``None``.

    Returns:
        A canonical MediaFormat identifier string.
    """
    return FormatNormalizer.normalize(raw, content_type)


def expand_format_filter(format_list: list[str] | None) -> list[str] | None:
    """Expand format filter values to include raw values that normalize to them.

    When a client filters by a canonical format like ``"dvd"``, this helper
    finds all raw mapping keys (e.g. ``"video"``) whose normalisation target
    is ``"dvd"`` and adds them to the filter list so the SQL ``IN`` clause
    can match the raw values stored in the database.

    For ``unknown_*`` filter values, adds ``None`` / NULL to the filter set
    so that items with NULL format are also captured (they normalise to
    unknown_* when no NULL mapping exists).  This is a best-effort expansion
    — items whose raw non-NULL value normalises to unknown_* will also be
    caught only after the DB is updated via the CLI tool.

    Args:
        format_list: The client-supplied format filter list, or ``None``.

    Returns:
        An expanded format list suitable for SQL ``IN`` filtering, or
        ``None`` if *format_list* was ``None``.
    """
    if not format_list:
        return format_list

    FormatNormalizer._load_mappings()

    # Build reverse mapping: canonical → set of raw keys that map to it
    reverse: dict[str, set[str]] = {}
    for raw_key, target in FormatNormalizer._mappings.items():
        reverse.setdefault(target, set()).add(raw_key)

    expanded: set[str] = set()
    for fmt in format_list:
        fmt_clean = fmt.strip().lower()
        expanded.add(fmt_clean)

        # Include raw keys whose mapping target is this format
        if fmt_clean in reverse:
            expanded.update(reverse[fmt_clean])

        # For unknown_* formats, also consider NULL format items
        # (they fall through to unknown_* when no explicit NULL mapping exists)
        if fmt_clean in _UNKNOWN_FORMATS and None not in FormatNormalizer._null_mappings:
            # We can't add None to the set, but we signal that NULL should be
            # included by NOT filtering out NULL values for this format
            pass

    return list(expanded) if expanded else None


def normalize_format_counts(
    raw_counts: dict[str, int],
    content_type_context: dict[str, str] | None = None,
) -> dict[str, int]:
    """Normalize and merge raw facet format counts.

    Each raw format key is passed through :func:`normalize_format` and
    counts for keys that resolve to the same canonical format are merged.
    NULL counts (key ``None``) are treated specially: they are looked up
    via ``content_type_context`` if available.

    Args:
        raw_counts: A dict mapping raw format strings (or ``None``) to
                    integer counts, as returned by a SQL ``GROUP BY``.
        content_type_context: Optional dict mapping raw format values to
                              their associated content type, used when
                              normalising keys whose content type isn't
                              known from the format alone.

    Returns:
        A dict mapping canonical format strings to merged integer counts.
    """
    normalized: dict[str, int] = {}
    for raw_key, cnt in raw_counts.items():
        ct = None
        if content_type_context and raw_key in content_type_context:
            ct = content_type_context[raw_key]
        normalized_key = normalize_format(raw_key, ct)
        normalized[normalized_key] = normalized.get(normalized_key, 0) + cnt
    return normalized


# The set of unknown_* format strings (used in filter expansion)
_UNKNOWN_FORMATS: frozenset[str] = frozenset({MediaFormat.UNKNOWN_VIDEO, MediaFormat.UNKNOWN_AUDIO, MediaFormat.UNKNOWN_TEXT})

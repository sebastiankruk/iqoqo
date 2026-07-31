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

from app.strategies.base import LookupStrategy
from app.utils.discogs import fetch_discogs_by_id, fetch_discogs_metadata
from app.utils.musicbrainz import fetch_audio_metadata

#: Raw format labels (case-insensitive) that signal a Blu-ray Pure Audio
#: carrier in provider payloads (Discogs ``formats`` / MusicBrainz media).
BLURAY_AUDIO_RAW_LABELS: frozenset[str] = frozenset(
    {
        "blu-ray audio",
        "bd-a",
        "bluray hifi",
        "pure audio blu-ray",
        "blu-ray pure audio",
    }
)

#: Raw format labels (case-insensitive) that signal a generic Blu-ray carrier,
#: regardless of whether the content is audio or video.
BLURAY_CARRIER_RAW_LABELS: frozenset[str] = frozenset(
    {
        "blu-ray",
        "bluray",
        "bd",
        "bd-rom",
    }
)


def is_bluray_audio_release(format_labels: list[str] | tuple[str, ...] | None) -> bool:
    """Return ``True`` if any label in *format_labels* signals Blu-ray Pure Audio.

    Args:
        format_labels: Raw provider format labels (Discogs ``formats`` names +
                       descriptions, MusicBrainz media format, etc.).

    Returns:
        ``True`` iff at least one label (case-insensitive, stripped) matches
        :data:`BLURAY_AUDIO_RAW_LABELS`.
    """
    if not format_labels:
        return False
    return any(str(label).strip().lower() in BLURAY_AUDIO_RAW_LABELS for label in format_labels if label)


def is_bluray_carrier(format_labels: list[str] | tuple[str, ...] | None) -> bool:
    """Return ``True`` if any label signals a Blu-ray carrier (audio or video)."""
    if not format_labels:
        return False
    return any(str(label).strip().lower() in (BLURAY_AUDIO_RAW_LABELS | BLURAY_CARRIER_RAW_LABELS) for label in format_labels if label)


def classify_bluray_carrier(
    work_content_type: str | None,
    expression_kind: str | None = None,
) -> tuple[str, str]:
    """Work-driven classification for Blu-ray carriers.

    Decision rule (release-0-7-13 design, "BluRay Pure Audio = new music format"):

    - A live-performance Expression on a BD carrier is a **movie** — the BD is
      a video carrier of a Performance Event. → ``("movie", "bluray")``
    - A music Work (studio album, etc.) on a BD carrier is **music** in the
      Blu-ray Pure Audio format. → ``("music", "bluray_audio")``
    - Anything else on a BD carrier defaults to the video boundary.
      → ``("movie", "bluray")``

    Args:
        work_content_type: The Work's content type (e.g. ``"music"``,
                           ``"movie"``). May be ``None`` when unknown.
        expression_kind:   The Expression's ``kind`` (e.g. ``"live_performance"``),
                           or ``None`` for studio/unknown Expressions.

    Returns:
        A ``(content_type, format)`` pair suitable for ``Expression.content_type``
        and the canonical manifestation format.
    """
    if expression_kind == "live_performance":
        return ("movie", "bluray")
    if work_content_type == "music":
        return ("music", "bluray_audio")
    return ("movie", "bluray")


class AudioLookupStrategy(LookupStrategy):
    def lookup(self, barcode: str, query: str | None = None) -> tuple[dict | None, str | None]:
        meta, provider = None, None
        if barcode.isdigit() and len(barcode) <= 7:
            meta = fetch_discogs_by_id(barcode)
            if meta:
                meta["data_source"] = "discogs"
                provider = "discogs"

        if not meta:
            meta = fetch_discogs_metadata(barcode)
            if meta:
                meta["data_source"] = "discogs"
                provider = "discogs"

        if not meta:
            meta = fetch_audio_metadata(barcode)
            if meta:
                meta["data_source"] = "musicbrainz"
                provider = "musicbrainz"

        return meta, provider

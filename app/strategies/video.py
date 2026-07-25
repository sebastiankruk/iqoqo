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
from app.strategies.audio import classify_bluray_carrier
from app.strategies.base import LookupStrategy
from app.utils.tmdb import clean_video_title, fetch_video_metadata
from app.utils.upc import resolve_physical_media


def should_defer_bluray_to_audio(
    work_content_type: str | None,
    expression_kind: str | None = None,
) -> bool:
    """Return ``True`` when a Blu-ray carrier belongs to the audio boundary.

    A BD carrier of a **music Work** that is *not* a live-performance Expression
    is Blu-ray Pure Audio (``music``/``bluray_audio``) and must be claimed by
    the audio boundary — not by the video/movie pipeline.  Concerts
    (``live_performance`` Expressions) and non-music Works stay on the video
    side as ``movie``/``bluray``.

    The rule mirrors :func:`app.strategies.audio.classify_bluray_carrier` so
    both sides of the boundary agree.

    Args:
        work_content_type: The Work's content type, or ``None`` if unknown.
        expression_kind:   The Expression's ``kind``, or ``None``.

    Returns:
        ``True`` iff the BD carrier should be handled as Blu-ray Pure Audio.
    """
    content_type, fmt = classify_bluray_carrier(work_content_type, expression_kind)
    return (content_type, fmt) == ("music", "bluray_audio")


class VideoLookupStrategy(LookupStrategy):
    def lookup(self, barcode: str, query: str | None = None) -> tuple[dict | None, str | None]:
        meta, provider = None, None
        upc_meta = resolve_physical_media(barcode)

        if upc_meta and upc_meta.get("title"):
            title = clean_video_title(upc_meta["title"])
            meta = fetch_video_metadata(title)
            if meta:
                meta["data_source"] = "tmdb"
                provider = "tmdb"
                meta.update({k: v for k, v in upc_meta.items() if k not in meta})
            else:
                meta = upc_meta
                provider = "upc"
                meta["data_source"] = "upc"

        if not meta:
            meta = fetch_video_metadata(barcode)
            if meta:
                meta["data_source"] = "tmdb"
                provider = "tmdb"

        return meta, provider

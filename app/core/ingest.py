"""Handles data ingestion from external sources."""

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
from app.core.frbr_service import (
    add_expression_contribution,
    add_work_contribution,
    get_or_create_contributor,
    get_or_create_live_performance_expression,
)
from app.db.core import MediaCategory, MediaFormat
from app.db.models import Expression, Manifestation, Work, db
from app.utils.bgg import fetch_bgg_metadata
from app.utils.covers import start_cover_processing
from app.utils.discogs import fetch_discogs_metadata
from app.utils.isbn import fetch_isbn_metadata
from app.utils.musicbrainz import fetch_audio_metadata
from app.utils.tmdb import clean_video_title, fetch_video_metadata
from app.utils.upc import resolve_physical_media


def _extract_genres(meta: dict) -> list[str]:
    genres: list[str] = []
    for key in ("Categories", "genres", "genre", "Genre"):
        raw = meta.get(key)
        if isinstance(raw, list):
            for v in raw:
                if isinstance(v, str) and v.strip():
                    genres.append(v.strip())
        elif isinstance(raw, str) and raw.strip():
            genres.append(raw.strip())
    return genres


#: Case-insensitive title substrings that strongly indicate a live recording.
_LIVE_TITLE_MARKERS: tuple[str, ...] = (
    "(live",
    "[live",
    " live at ",
    " live in ",
    " live from ",
    " unplugged",
)


def _detect_live_performance(meta: dict) -> bool:
    """Return ``True`` when provider metadata signals a live recording.

    Signals inspected (any hit → live):

    - ``meta['styles']`` / ``meta['genres']`` containing a value equal to
      ``"Live"`` (Discogs style tag, MusicBrainz secondary type).
    - ``meta['secondary_types']`` containing ``"Live"`` (MusicBrainz
      release-group secondary types).
    - ``meta['title']`` containing a live marker substring such as
      ``"(live"``, ``"[live"``, ``" live at "``, ``" unplugged"``.

    This is a *detector only* — it never mutates ``meta``.  The ingestion
    pipeline uses the hit to type the resulting Expression as
    ``kind='live_performance'`` (Performance Event), never as a genre tag or
    item-level flag.
    """
    if not isinstance(meta, dict):
        return False

    def _iter_str(value):
        if isinstance(value, str):
            yield value
        elif isinstance(value, list):
            for v in value:
                if isinstance(v, str):
                    yield v

    for key in ("styles", "genres", "secondary_types", "secondary-types"):
        for raw in _iter_str(meta.get(key)):
            if raw.strip().lower() == "live":
                return True

    title = meta.get("title") or meta.get("Title") or ""
    if isinstance(title, str):
        lowered = f" {title.lower()} "
        for marker in _LIVE_TITLE_MARKERS:
            if marker in lowered:
                return True

    return False


class IngestService:
    @staticmethod
    def batch_ingest_manifestations(manifestations_data: list[dict]) -> list[Manifestation]:
        """Batch-ingest a list of pre-fetched metadata dicts with deferred tsvector updates.

        Phase 4 (0.7.8): Issues ``SET CONSTRAINTS ALL DEFERRED`` before the
        bulk inserts so that the ``DEFERRABLE INITIALLY DEFERRED`` constraint
        triggers (added by the 20260709_defer_tsvector_triggers migration) fire
        *after* the final COMMIT rather than synchronously on every row.  This
        eliminates the write-latency spike that previously occurred when adding
        many items in quick succession.

        Each dict in ``manifestations_data`` is passed directly to
        :meth:`ingest_from_meta`, which handles FRBR hierarchy creation.
        A single :py:meth:`db.session.commit` is issued at the end so that all
        tsvector indexes are rebuilt in one batch.

        Parameters
        ----------
        manifestations_data:
            List of metadata dicts; see :meth:`ingest_from_meta` for the
            required keys (``title``, ``format`` at minimum).

        Returns
        -------
        list[Manifestation]
            The newly created :class:`~app.db.models.Manifestation` objects.
        """
        # Force all deferred constraint triggers to wait until the final COMMIT
        if db.engine.dialect.name == "postgresql":
            from sqlalchemy import text

            db.session.execute(text("SET CONSTRAINTS ALL DEFERRED;"))

        ingested: list[Manifestation] = []
        for meta in manifestations_data:
            manifestation = IngestService.ingest_from_meta(meta)
            ingested.append(manifestation)

        # Single commit – tsvector indexes are rebuilt post-transaction
        db.session.commit()
        return ingested

    @staticmethod
    def ingest_from_meta(meta: dict) -> Manifestation:
        """Save a manifestation from pre-fetched metadata without calling any external API.

        Used by the 'Save to Catalog Only' flow so we can persist the data the
        lookup endpoint already retrieved, avoiding redundant / slow network calls.
        The caller must include at minimum a ``title`` and ``format`` key.
        """
        title = meta.get("title") or meta.get("Title") or "Unknown Title"
        raw_author = meta.get("author") or meta.get("artist") or (meta.get("Authors") or meta.get("authors") or [None])[0]
        author_name = raw_author.get("name") if isinstance(raw_author, dict) else raw_author
        cover_url = meta.get("cover_url") or meta.get("thumb") or meta.get("cover")
        raw_format = (meta.get("format") or meta.get("Format") or "audio").lower()

        from app.core.taxonomy import FORMAT_ALIAS_TO_CATEGORY

        # Map format string → FRBR content type (canonical formats + aliases)
        content_type = FORMAT_ALIAS_TO_CATEGORY.get(raw_format, MediaCategory.MUSIC)

        work_genres = _extract_genres(meta)
        work_meta: dict = {"authors": [author_name] if author_name else []}
        if work_genres:
            work_meta["genres"] = work_genres
        work = Work(title=title, meta=work_meta)
        db.session.add(work)
        db.session.flush()

        if author_name:
            contributor = get_or_create_contributor(author_name, "person")
            if contributor:
                add_work_contribution(work.id, contributor.id, "author")

        expression = Expression(work=work, language=meta.get("language", "en"), content_type=content_type)
        db.session.add(expression)
        db.session.flush()

        man_meta = meta.copy()
        man_meta.update(
            {
                "title": title,
                "author": author_name,
                "authors": [author_name] if author_name else [],
                "cover_url": cover_url,
                "format": raw_format,
            }
        )

        manifestation = Manifestation(expression=expression, meta=man_meta)
        db.session.add(manifestation)
        db.session.commit()

        identifier = meta.get("identifier") or meta.get("barcode") or meta.get("isbn") or title
        start_cover_processing(manifestation_id=manifestation.id, identifier=identifier, title=title, author=author_name or "")
        return manifestation

    @staticmethod
    def ingest_puzzle_from_barcode(barcode: str) -> Manifestation:
        # Puzzles are purely manifestation-based (no cinematic 'work' resolution)
        # but we still benefit from the Tier 1a/1b/2 waterfall.
        meta = resolve_physical_media(barcode)

        if not meta:
            raise ValueError("Puzzle metadata not found in external services.")

        title = meta.get("title") or "Unknown Puzzle"
        author_name = meta.get("manufacturer") or meta.get("brand") or "Unknown Manufacturer"
        cover_url = meta.get("cover_url")

        work_genres = _extract_genres(meta)
        work_meta: dict = {"authors": [author_name]} if author_name else {}
        if work_genres:
            work_meta["genres"] = work_genres
        work = Work(title=title, meta=work_meta)
        db.session.add(work)
        db.session.flush()

        expression = Expression(work=work, language=meta.get("language", "en"), content_type=MediaCategory.PUZZLE)
        db.session.add(expression)
        db.session.flush()

        if author_name:
            get_or_create_contributor(author_name, "organization")
            # Note: "manufacturer" is not a supported WorkContribution role,
            # so we keep manufacturer info in manifestation metadata instead.

        man_meta = meta.copy()
        man_meta.update(
            {
                "barcode": barcode,
                "format": MediaFormat.JIGSAW_PUZZLE,
                "title": title,
                "author": author_name,
                "authors": [author_name] if author_name else [],
                "cover_url": cover_url,
                "publisher": meta.get("publisher") or author_name,
                "manufacturer": author_name,
            }
        )

        manifestation = Manifestation(
            expression=expression,
            meta=man_meta,
        )
        db.session.add(manifestation)
        db.session.commit()

        start_cover_processing(manifestation_id=manifestation.id, identifier=barcode, title=title, author=author_name or "")
        return manifestation

    @staticmethod
    def ingest_from_isbn(isbn: str) -> Manifestation:
        meta = fetch_isbn_metadata(isbn)
        if not meta:
            raise ValueError("ISBN metadata not found in external services.")

        # Normalize common fields
        title = meta.get("title") or meta.get("Title") or "Unknown Title"
        raw_author = meta.get("author") or (meta.get("Authors") or meta.get("authors") or [None])[0] or meta.get("Artist")
        author_name = raw_author.get("name") if isinstance(raw_author, dict) else raw_author
        cover_url = meta.get("cover_url") or meta.get("cover") or meta.get("thumbnail")

        # Create FRBR hierarchy
        work_genres = _extract_genres(meta)
        work_meta = {"authors": [author_name]} if author_name else {}
        if work_genres:
            work_meta["genres"] = work_genres
        work = Work(title=title, meta=work_meta)
        db.session.add(work)
        db.session.flush()

        if author_name:
            contributor = get_or_create_contributor(author_name, "person")
            if contributor:
                add_work_contribution(work.id, contributor.id, "author")

        expression = Expression(work=work, language=meta.get("language", "en"), content_type=MediaCategory.TEXT)
        db.session.add(expression)

        # Merge raw meta with explicit standard keys for the UI
        man_meta = meta.copy()
        man_meta.update(
            {
                "isbn": isbn,
                "title": title,
                "author": author_name,
                "authors": [author_name] if author_name else [],
                "cover_url": cover_url,
                "publisher": meta.get("publisher"),
            }
        )

        manifestation = Manifestation(
            expression=expression,
            meta=man_meta,
        )
        db.session.add(manifestation)
        db.session.commit()

        # Trigger background processing to secure the cover natively
        start_cover_processing(manifestation_id=manifestation.id, identifier=isbn, title=title, author=author_name or "")

        return manifestation

    @staticmethod
    def ingest_audio_from_barcode(barcode: str) -> Manifestation:
        # Try Discogs first (if token is available inside the utility), then MusicBrainz
        meta = fetch_discogs_metadata(barcode) or fetch_audio_metadata(barcode)

        if not meta:
            raise ValueError("Audio metadata not found in external services.")

        # Normalize keys that might come back differently from MusicBrainz/Discogs
        title = meta.get("title") or meta.get("Title") or "Unknown Title"
        author_name = meta.get("author") or meta.get("artist") or meta.get("Artist")
        cover_url = meta.get("cover_url") or meta.get("thumb") or meta.get("cover")

        # Create FRBR hierarchy
        work_genres = _extract_genres(meta)
        work_meta = {"authors": [author_name]} if author_name else {}
        if work_genres:
            work_meta["genres"] = work_genres
        work = Work(title=title, meta=work_meta)
        db.session.add(work)
        db.session.flush()

        is_live = _detect_live_performance(meta)
        if is_live:
            expression = get_or_create_live_performance_expression(
                work_id=work.id,
                content_type=MediaCategory.MUSIC,
                language=meta.get("language", "en"),
                venue=meta.get("venue"),
                performance_date=meta.get("performance_date") or meta.get("date"),
                performers=[(author_name, "performer")] if author_name else [],
            )
        else:
            expression = Expression(work=work, language=meta.get("language", "en"), content_type=MediaCategory.MUSIC)
            db.session.add(expression)
            db.session.flush()

        if author_name and not is_live:
            contributor = get_or_create_contributor(author_name, "person")
            if contributor:
                add_expression_contribution(expression.id, contributor.id, "performer")

        # Merge raw meta with explicit standard keys for the UI
        man_meta = meta.copy()
        man_meta.update(
            {
                "barcode": barcode,
                "format": meta.get("format", "music"),
                "title": title,
                "author": author_name,
                "authors": [author_name] if author_name else [],
                "cover_url": cover_url,
                "publisher": meta.get("publisher") or meta.get("label"),
            }
        )

        manifestation = Manifestation(
            expression=expression,
            meta=man_meta,
        )
        db.session.add(manifestation)
        db.session.commit()

        # Trigger background processing so covers.py intercepts the URL and saves locally
        start_cover_processing(manifestation_id=manifestation.id, identifier=barcode, title=title, author=author_name or "")
        return manifestation

    @staticmethod
    def ingest_video_from_barcode(query: str) -> Manifestation:
        """Ingest video by title query or barcode (via UPC resolution)."""
        meta = None
        is_barcode = len(query) in (8, 12, 13, 14) and query.isdigit()

        if is_barcode:
            upc_meta = resolve_physical_media(query)
            if upc_meta and upc_meta.get("title"):
                title = clean_video_title(upc_meta["title"])
                meta = fetch_video_metadata(title)
                if meta:
                    meta.update({k: v for k, v in upc_meta.items() if k not in meta})
                else:
                    meta = upc_meta

        if not meta:
            meta = fetch_video_metadata(query)

        if not meta:
            raise ValueError("Video metadata not found in external services.")

        title = meta.get("title") or meta.get("Title") or "Unknown Title"
        author_name = meta.get("author") or meta.get("director") or meta.get("Director")
        cover_url = meta.get("cover_url")

        work_genres = _extract_genres(meta)
        work_meta = {"authors": [author_name]} if author_name else {}
        if work_genres:
            work_meta["genres"] = work_genres
        work = Work(title=title, meta=work_meta)
        db.session.add(work)
        db.session.flush()

        is_live = _detect_live_performance(meta)
        if is_live:
            # A concert video (e.g. Live at Wembley Blu-ray) is a Performance
            # Event Expression realized in a video Manifestation.
            expression = get_or_create_live_performance_expression(
                work_id=work.id,
                content_type=MediaCategory.MOVIE,
                language=meta.get("language", "en"),
                venue=meta.get("venue"),
                performance_date=meta.get("performance_date") or meta.get("date"),
                performers=[(author_name, "performer")] if author_name else [],
            )
        else:
            expression = Expression(work=work, language=meta.get("language", "en"), content_type=MediaCategory.MOVIE)
            db.session.add(expression)
            db.session.flush()

        if author_name and not is_live:
            contributor = get_or_create_contributor(author_name, "person")
            if contributor:
                # Directors are Work-level (CreationEvent) per FRBRoo ontology
                add_work_contribution(work.id, contributor.id, "director")

        stored_barcode = query if is_barcode else None

        man_meta = meta.copy()
        man_meta.update(
            {
                "barcode": stored_barcode,
                "format": meta.get("format", "movie"),
                "title": title,
                "author": author_name,
                "authors": [author_name] if author_name else [],
                "cover_url": cover_url,
                "publisher": meta.get("publisher"),
            }
        )

        manifestation = Manifestation(
            expression=expression,
            meta=man_meta,
        )
        db.session.add(manifestation)
        db.session.commit()

        start_cover_processing(manifestation_id=manifestation.id, identifier=query, title=title, author=author_name or "")
        return manifestation

    @staticmethod
    def ingest_game_from_barcode(query: str) -> Manifestation:
        """Ingest board game by title query or barcode (via UPC resolution)."""
        meta = None
        is_barcode = len(query) in (8, 12, 13, 14) and query.isdigit()

        if is_barcode:
            # For games, we use the waterfall for manifestation/title resolution,
            # then link to BoardGameGeek (BGG).
            upc_meta = resolve_physical_media(query)
            if upc_meta and upc_meta.get("title"):
                meta = fetch_bgg_metadata(upc_meta["title"])
                if meta:
                    # Merge manifestation info (covers/affiliates from Allegro)
                    meta.update({k: v for k, v in upc_meta.items() if k not in meta})
                else:
                    from app.utils.igdb import fetch_game_metadata

                    meta = fetch_game_metadata(upc_meta["title"])
                    if meta:
                        meta.update({k: v for k, v in upc_meta.items() if k not in meta})
                    else:
                        meta = upc_meta

        if not meta:
            meta = fetch_bgg_metadata(query)
            if not meta:
                from app.utils.igdb import fetch_game_metadata

                meta = fetch_game_metadata(query)

        if not meta:
            raise ValueError("Board game metadata not found in external services.")

        title = meta.get("title") or meta.get("Title") or "Unknown Title"
        author_name = meta.get("author") or meta.get("designer") or (meta.get("Designers", [None])[0] if meta.get("Designers") else None)
        cover_url = meta.get("cover_url")
        mechanics = meta.get("Mechanics", []) or meta.get("mechanics", [])

        work_genres = _extract_genres(meta)
        work_meta = {"authors": [author_name], "mechanics": mechanics} if author_name else {"mechanics": mechanics}
        if work_genres:
            work_meta["genres"] = work_genres
        work = Work(title=title, meta=work_meta)
        db.session.add(work)
        db.session.flush()

        expression = Expression(work=work, language=meta.get("language", "en"), content_type=MediaCategory.BOARD_GAME)
        db.session.add(expression)
        db.session.flush()

        if author_name:
            contributor = get_or_create_contributor(author_name, "person")
            if contributor:
                add_work_contribution(work.id, contributor.id, "designer")

        stored_barcode = query if is_barcode else None

        man_meta = meta.copy()
        man_meta.update(
            {
                "barcode": stored_barcode,
                "format": meta.get("format", meta.get("Format", MediaFormat.BOARD_GAME)),
                "title": title,
                "author": author_name,
                "authors": [author_name] if author_name else [],
                "cover_url": cover_url,
                "mechanics": mechanics,
            }
        )

        manifestation = Manifestation(
            expression=expression,
            meta=man_meta,
        )
        db.session.add(manifestation)
        db.session.commit()

        start_cover_processing(manifestation_id=manifestation.id, identifier=query, title=title, author=author_name or "")
        return manifestation

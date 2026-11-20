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
from typing import Any

from sqlalchemy import or_, select

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
from app.utils.issn import is_977_periodical_barcode, normalize_issn, parse_issn_or_977
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
    """Creates manifestations from an external identifier.

    Each ``ingest_from_*`` method owns one resolution path (ISBN, audio barcode,
    puzzle barcode) and returns the resulting Manifestation. Resolution is
    idempotent: an identifier that is already present returns the existing row
    rather than creating a duplicate, which is what makes bulk re-ingest safe."""

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

        is_lego = (
            meta.get("category") == MediaCategory.LEGO
            or FORMAT_ALIAS_TO_CATEGORY.get(raw_format) == MediaCategory.LEGO
            or raw_format
            in (
                "standard_set",
                "ucs_collector_set",
                "technic_set",
                "minifigure_series",
                "polybag",
                "modular_building",
                "unknown_lego",
                "lego",
                "construction_set",
                "brick_set",
                "brick",
            )
        )

        # Map format string → FRBR content type (canonical formats + aliases)
        content_type = MediaCategory.LEGO if is_lego else FORMAT_ALIAS_TO_CATEGORY.get(raw_format, MediaCategory.MUSIC)

        candidate_barcode = meta.get("barcode") or meta.get("identifier")
        candidate_ean = meta.get("ean") or (
            candidate_barcode if candidate_barcode and len(str(candidate_barcode)) == 13 and str(candidate_barcode).isdigit() else None
        )
        candidate_upc = meta.get("upc") or (
            candidate_barcode if candidate_barcode and len(str(candidate_barcode)) == 12 and str(candidate_barcode).isdigit() else None
        )
        candidate_set_num = meta.get("set_number") or meta.get("set_num")

        is_serial = (
            raw_format in ("magazine", "journal", "periodical", "serial")
            or meta.get("work_kind") == "serial"
            or bool(meta.get("issn"))
            or is_977_periodical_barcode(str(candidate_ean or candidate_barcode or ""))
        )
        if is_serial:
            return IngestService.ingest_serial_from_meta(meta)

        # Deduplicate existing manifestation
        conditions = []
        if candidate_barcode:
            b_str = str(candidate_barcode).strip()
            conditions.extend([Manifestation.barcode == b_str, Manifestation.meta["barcode"].as_string() == b_str])
        if candidate_ean:
            e_str = str(candidate_ean).strip()
            conditions.extend([Manifestation.ean == e_str, Manifestation.meta["ean"].as_string() == e_str])
        if candidate_upc:
            u_str = str(candidate_upc).strip()
            conditions.extend([Manifestation.upc == u_str, Manifestation.meta["upc"].as_string() == u_str])
        if is_lego and candidate_set_num:
            s_clean = str(candidate_set_num).strip()
            conditions.extend(
                [
                    Manifestation.meta["set_number"].as_string() == s_clean,
                    Manifestation.barcode == s_clean,
                ]
            )
            if "-" in s_clean:
                base_s = s_clean.split("-")[0]
                conditions.append(Manifestation.meta["set_number"].as_string() == base_s)

        if conditions:
            stmt = select(Manifestation).where(or_(*conditions))
            existing_manifestation = db.session.execute(stmt).scalars().first()
            if existing_manifestation:
                return existing_manifestation

        raw_payload = meta.get("raw_payload") or meta

        from app.core.frbr_service import derive_sort_title

        theme = meta.get("theme")
        work_genres = _extract_genres(meta)
        if is_lego and theme and theme not in work_genres:
            work_genres.append(theme)

        work_meta: dict = {"authors": [author_name] if author_name else []}
        if is_lego and theme:
            work_meta["theme"] = theme
        if work_genres:
            work_meta["genres"] = work_genres

        work = Work(title=title, sort_title=derive_sort_title(title), meta=work_meta, raw_payload=raw_payload)
        db.session.add(work)
        db.session.flush()

        if author_name:
            role = "designer" if is_lego else "author"
            contributor = get_or_create_contributor(author_name, "person")
            if contributor:
                add_work_contribution(work.id, contributor.id, role)

        expression = Expression(
            work=work,
            language=meta.get("language", "en"),
            content_type=content_type,
            raw_payload=raw_payload,
        )
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
        if is_lego and candidate_set_num:
            man_meta.setdefault("set_number", str(candidate_set_num).strip())

        manifestation = Manifestation(
            expression=expression,
            format=raw_format,
            format_type=raw_format,
            label=meta.get("publisher") or meta.get("label"),
            barcode=candidate_barcode,
            ean=candidate_ean,
            upc=candidate_upc,
            cover_url=cover_url,
            catalog_number=meta.get("catalog_number") or meta.get("catno"),
            meta=man_meta,
            raw_payload=raw_payload,
        )
        db.session.add(manifestation)
        db.session.commit()

        identifier = meta.get("identifier") or meta.get("barcode") or meta.get("isbn") or title
        start_cover_processing(manifestation_id=manifestation.id, identifier=identifier, title=title, author=author_name or "")
        return manifestation

    @staticmethod
    def ingest_puzzle_from_barcode(barcode: str) -> Manifestation:
        """Resolve a puzzle or game from a barcode.

        Tries the BoardGameGeek path first and falls back to UPC/EAN resolution, since
        puzzles are catalogued inconsistently across both."""
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
        """Resolve a book from an ISBN.

        Canonicalises the ISBN before lookup, so hyphenated and check-digit variants of
        the same identifier resolve to one record instead of duplicates."""
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
        if "_provenance" in meta:
            man_meta["_provenance"] = meta["_provenance"]

        manifestation = Manifestation(
            expression=expression,
            meta=man_meta,
            raw_payload=meta.get("raw_payload") or meta,
        )
        db.session.add(manifestation)
        db.session.commit()

        # Trigger background processing to secure the cover natively
        start_cover_processing(manifestation_id=manifestation.id, identifier=isbn, title=title, author=author_name or "")

        return manifestation

    @staticmethod
    def ingest_audio_from_barcode(barcode: str) -> Manifestation:
        """Resolve an audio release from a barcode.

        Audio carriers are identified inconsistently across MusicBrainz, Discogs and
        UPC databases, so this consults all three before giving up."""
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

    @staticmethod
    def ingest_lego_from_barcode(query: str) -> Manifestation:
        """Ingest LEGO set by set number or barcode (via Rebrickable and UPC resolution)."""
        from app.strategies.lego import LegoLookupStrategy

        strategy = LegoLookupStrategy()
        meta, _ = strategy.lookup(query)

        if not meta:
            raise ValueError("LEGO set metadata not found in external services.")

        is_barcode = len(query) in (8, 12, 13, 14) and query.isdigit()
        stored_barcode = query if is_barcode else meta.get("barcode")
        set_num = meta.get("set_number") or (query if not is_barcode else None)
        ean_val = meta.get("ean") or (
            stored_barcode if stored_barcode and len(str(stored_barcode)) == 13 and str(stored_barcode).isdigit() else None
        )
        upc_val = meta.get("upc") or (
            stored_barcode if stored_barcode and len(str(stored_barcode)) == 12 and str(stored_barcode).isdigit() else None
        )

        # Deduplicate existing manifestation
        conditions = []
        if stored_barcode:
            b_str = str(stored_barcode).strip()
            conditions.extend([Manifestation.barcode == b_str, Manifestation.meta["barcode"].as_string() == b_str])
        if ean_val:
            e_str = str(ean_val).strip()
            conditions.extend([Manifestation.ean == e_str, Manifestation.meta["ean"].as_string() == e_str])
        if upc_val:
            u_str = str(upc_val).strip()
            conditions.extend([Manifestation.upc == u_str, Manifestation.meta["upc"].as_string() == u_str])
        if set_num:
            s_clean = str(set_num).strip()
            conditions.extend(
                [
                    Manifestation.meta["set_number"].as_string() == s_clean,
                    Manifestation.barcode == s_clean,
                ]
            )
            if "-" in s_clean:
                base_s = s_clean.split("-")[0]
                conditions.append(Manifestation.meta["set_number"].as_string() == base_s)

        if conditions:
            stmt = select(Manifestation).where(or_(*conditions))
            existing_manifestation = db.session.execute(stmt).scalars().first()
            if existing_manifestation:
                return existing_manifestation

        title = meta.get("title") or "Unknown LEGO Set"
        author_name = meta.get("author") or meta.get("designer")
        cover_url = meta.get("cover_url")
        theme = meta.get("theme")
        work_genres = _extract_genres(meta)
        if theme and theme not in work_genres:
            work_genres.append(theme)

        work_meta: dict[str, Any] = {"theme": theme} if theme else {}
        if author_name:
            work_meta["authors"] = [author_name]
        if work_genres:
            work_meta["genres"] = work_genres

        from app.core.frbr_service import derive_sort_title

        work = Work(title=title, sort_title=derive_sort_title(title), meta=work_meta)
        db.session.add(work)
        db.session.flush()

        expression = Expression(work=work, language=meta.get("language", "en"), content_type=MediaCategory.LEGO)
        db.session.add(expression)
        db.session.flush()

        if author_name:
            contributor = get_or_create_contributor(author_name, "person")
            if contributor:
                add_work_contribution(work.id, contributor.id, "designer")

        format_val = meta.get("format", MediaFormat.STANDARD_SET)

        man_meta = meta.copy()
        man_meta.update(
            {
                "barcode": stored_barcode,
                "format": format_val,
                "title": title,
                "cover_url": cover_url,
            }
        )
        if set_num:
            man_meta.setdefault("set_number", str(set_num).strip())

        manifestation = Manifestation(
            expression=expression,
            format=format_val,
            format_type=format_val,
            label=meta.get("publisher") or meta.get("label"),
            barcode=stored_barcode,
            ean=ean_val,
            upc=upc_val,
            cover_url=cover_url,
            meta=man_meta,
            raw_payload=meta.get("raw_payload") or meta,
        )
        db.session.add(manifestation)
        db.session.commit()

        start_cover_processing(manifestation_id=manifestation.id, identifier=query, title=title, author=author_name or "")
        return manifestation

    @staticmethod
    def ingest_serial_from_meta(meta: dict, *, commit: bool = True) -> Manifestation:
        """Persist or match an individual periodical issue Manifestation under an F18 Serial Work.

        Unlike books/albums, GS1 977 EAN-13 barcodes repeat across issues within a year/price variant,
        so deduplication NEVER matches on ``Manifestation.ean`` alone; instead it matches on exact
        ``full_barcode`` (15/18-digit) or ``(work_id, issue_number, publication_year)``.
        """
        raw_code = str(meta.get("full_barcode") or meta.get("barcode") or meta.get("ean") or meta.get("issn") or "").strip()
        parsed = parse_issn_or_977(raw_code) if raw_code else None
        if not parsed and meta.get("issn"):
            parsed = parse_issn_or_977(str(meta["issn"]))

        issn = normalize_issn(str(meta["issn"])) if meta.get("issn") else (parsed["issn"] if parsed else None)
        eissn = normalize_issn(str(meta["eissn"])) if meta.get("eissn") else None
        ean = meta.get("ean") or (parsed["ean"] if parsed else None)
        ean_addon = meta.get("ean_addon") or (parsed["ean_addon"] if parsed else None)
        if ean_addon is not None:
            ean_addon = str(ean_addon).strip() or None
        full_barcode = meta.get("full_barcode") or (parsed["full_barcode"] if parsed else None)
        if not full_barcode and ean and ean_addon:
            full_barcode = f"{ean}{ean_addon}"

        issue_number_raw = meta.get("issue_number")
        issue_number = str(issue_number_raw).strip() if issue_number_raw not in (None, "") else None
        if issue_number is None and parsed and parsed.get("addon_issue_hint") is not None:
            issue_number = str(parsed["addon_issue_hint"])

        cum_issue_raw = meta.get("cumulative_issue_number")
        cum_issue = int(cum_issue_raw) if cum_issue_raw not in (None, "") else None
        pub_year_raw = meta.get("publication_year") or meta.get("year")
        pub_year = int(pub_year_raw) if pub_year_raw not in (None, "") and str(pub_year_raw).strip().isdigit() else None
        pub_month_raw = meta.get("publication_month")
        pub_month = int(pub_month_raw) if pub_month_raw not in (None, "") and str(pub_month_raw).strip().isdigit() else None
        volume = str(meta["volume"]).strip() if meta.get("volume") not in (None, "") else None

        raw_pub = meta.get("publisher") or meta.get("Publisher") or meta.get("label") or meta.get("Label")
        publisher_val = (
            str(raw_pub).strip()
            if isinstance(raw_pub, str) and raw_pub.strip() and raw_pub.strip().lower() not in {"unknown", "n/a", "none"}
            else None
        )
        raw_pub_date = meta.get("publication_date") or meta.get("PublicationDate")
        pub_date_obj = None
        if isinstance(raw_pub_date, str) and raw_pub_date.strip():
            from datetime import date

            try:
                pub_date_obj = date.fromisoformat(raw_pub_date.strip()[:10])
            except (ValueError, TypeError):
                pub_date_obj = None

        # 1. Exact full_barcode lookup first (unambiguous 15/18-digit barcode)
        if full_barcode:
            existing_full = db.session.execute(select(Manifestation).where(Manifestation.full_barcode == full_barcode)).scalars().first()
            if existing_full is not None:
                return existing_full

        # 2. Resolve or create parent F18 Serial Work
        from app.core.frbr_service import derive_sort_title

        title = (meta.get("title") or meta.get("Title") or (f"ISSN {issn}" if issn else "Unknown Periodical")).strip()
        work: Work | None = None
        if issn:
            work = db.session.execute(select(Work).where(Work.issn == issn)).scalars().first()
        if work is None and ean:
            work = (
                db.session.execute(
                    select(Work)
                    .join(Expression, Expression.work_id == Work.id)
                    .join(Manifestation, Manifestation.expression_id == Expression.id)
                    .where(Manifestation.ean == str(ean), Work.work_kind == "serial")
                )
                .scalars()
                .first()
            )
        if work is None:
            work_meta = dict(meta.get("work_meta") or {})
            if meta.get("indeks"):
                work_meta["indeks"] = meta["indeks"]
            if publisher_val:
                work_meta["publisher"] = publisher_val
            work = Work(
                title=title,
                sort_title=derive_sort_title(title),
                issn=issn,
                eissn=eissn,
                work_kind="serial",
                meta=work_meta,
                raw_payload=meta.get("raw_payload") or meta,
            )
            db.session.add(work)
            db.session.flush()
        else:
            if issn and not work.issn:
                work.issn = issn
            if eissn and not work.eissn:
                work.eissn = eissn
            if not work.work_kind:
                work.work_kind = "serial"
            if publisher_val and isinstance(work.meta, dict) and not work.meta.get("publisher"):
                work.meta = {**work.meta, "publisher": publisher_val}

        # 3. Resolve or create Expression for language under serial Work
        lang = str(meta.get("language") or "en").strip().lower()[:10] or "en"
        expression = (
            db.session.execute(
                select(Expression).where(
                    Expression.work_id == work.id,
                    Expression.content_type == MediaCategory.TEXT,
                    Expression.language == lang,
                )
            )
            .scalars()
            .first()
        )
        if expression is None:
            expression = Expression(
                work=work,
                language=lang,
                content_type=MediaCategory.TEXT,
                raw_payload=meta.get("raw_payload") or meta,
            )
            db.session.add(expression)
            db.session.flush()

        # 4. Issue-scoped deduplication under this parent Serial Work (never by bare EAN alone)
        if issue_number and pub_year is not None:
            existing_issue = (
                db.session.execute(
                    select(Manifestation)
                    .join(Expression, Manifestation.expression_id == Expression.id)
                    .where(
                        Expression.work_id == work.id,
                        Manifestation.issue_number == issue_number,
                        Manifestation.publication_year == pub_year,
                    )
                )
                .scalars()
                .first()
            )
            if existing_issue is not None:
                return existing_issue

        # Guard against bare 977 collision when no distinguishing issue attribute was provided at all
        cover_headline = str(meta.get("cover_headline") or "").strip()
        has_issue_specifier = any(
            [
                full_barcode,
                ean_addon,
                issue_number,
                cum_issue is not None,
                pub_year is not None,
                pub_month is not None,
                bool(cover_headline),
            ]
        )
        if is_977_periodical_barcode(str(ean or "")) and not has_issue_specifier:
            existing_for_ean = db.session.execute(select(Manifestation.id).where(Manifestation.ean == str(ean))).scalars().first()
            if existing_for_ean is not None:
                raise ValueError("Ambiguous bare 977 periodical barcode requires an EAN-2 add-on, issue number, date, or headline.")

        # 5. Create new issue Manifestation
        cover_url = meta.get("cover_url") or meta.get("thumb") or meta.get("cover")
        _item_only_keys = {
            "collection_status",
            "status",
            "local_barcode",
            "lent_to_user_id",
            "lent_to_name",
            "visibility",
            "is_hidden",
            "tags",
        }
        man_meta = {k: v for k, v in meta.items() if k not in _item_only_keys and v is not None}
        man_meta.update(
            {
                "title": title,
                "format": MediaFormat.MAGAZINE,
                "work_kind": "serial",
            }
        )
        if publisher_val:
            man_meta["publisher"] = publisher_val
            man_meta.pop("Publisher", None)
        if "authors" in man_meta and isinstance(man_meta["authors"], list):
            man_meta["authors"] = [
                a for a in man_meta["authors"] if isinstance(a, str) and a.strip().lower() not in {"unknown", "n/a", "none", ""}
            ]
        if "Authors" in man_meta and isinstance(man_meta["Authors"], list):
            man_meta["Authors"] = [
                a for a in man_meta["Authors"] if isinstance(a, str) and a.strip().lower() not in {"unknown", "n/a", "none", ""}
            ]
        if issn:
            man_meta["issn"] = issn
        if issue_number:
            man_meta["issue_number"] = issue_number
        if cum_issue is not None:
            man_meta["cumulative_issue_number"] = cum_issue
        if pub_year is not None:
            man_meta["publication_year"] = pub_year
        if pub_month is not None:
            man_meta["publication_month"] = pub_month
        if ean_addon:
            man_meta["ean_addon"] = ean_addon
        if full_barcode:
            man_meta["full_barcode"] = full_barcode

        manifestation = Manifestation(
            expression=expression,
            format=MediaFormat.MAGAZINE,
            format_type=MediaFormat.MAGAZINE,
            publisher=publisher_val,
            label=publisher_val,
            publication_date=pub_date_obj,
            barcode=full_barcode or ean or meta.get("barcode"),
            ean=ean,
            cover_url=cover_url,
            issue_number=issue_number,
            cumulative_issue_number=cum_issue,
            volume=volume,
            publication_year=pub_year,
            publication_month=pub_month,
            ean_addon=ean_addon,
            full_barcode=full_barcode,
            meta=man_meta,
            raw_payload=meta.get("raw_payload") or meta,
        )
        db.session.add(manifestation)
        if commit:
            db.session.commit()
        else:
            db.session.flush()
        return manifestation

    @staticmethod
    def ingest_serial_issue(barcode: str, meta: dict | None = None) -> Manifestation:
        """Ingest a periodical issue by ISSN or GS1 977 barcode using SerialLookupStrategy."""
        from app.strategies.serials import SerialLookupStrategy

        merged_meta = dict(meta or {})
        parsed = parse_issn_or_977(barcode)
        if not parsed:
            raise ValueError(f"Invalid ISSN or 977 periodical barcode: {barcode}")

        # Prevent silent collision when bare 13-digit 977 or plain ISSN lacks issue identification
        has_issue_spec = bool(
            parsed.get("full_barcode") or merged_meta.get("full_barcode") or merged_meta.get("issue_number") or merged_meta.get("ean_addon")
        )
        if not has_issue_spec:
            raise ValueError("Ambiguous bare 977 periodical barcode requires an EAN-2 add-on or issue number.")

        if "title" not in merged_meta and "Title" not in merged_meta:
            strategy = SerialLookupStrategy()
            fetched_meta, _provider = strategy.lookup(barcode)
            if fetched_meta:
                for k, v in fetched_meta.items():
                    merged_meta.setdefault(k, v)

        if parsed.get("issn"):
            merged_meta.setdefault("issn", parsed["issn"])
        if parsed.get("ean"):
            merged_meta.setdefault("ean", parsed["ean"])
        if parsed.get("ean_addon"):
            merged_meta.setdefault("ean_addon", parsed["ean_addon"])
        if parsed.get("full_barcode"):
            merged_meta.setdefault("full_barcode", parsed["full_barcode"])
        if parsed.get("addon_issue_hint") is not None:
            merged_meta.setdefault("issue_number", str(parsed["addon_issue_hint"]))

        return IngestService.ingest_serial_from_meta(merged_meta)

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
from app.core.frbr_service import add_expression_contribution, add_work_contribution, get_or_create_contributor
from app.db.core import MediaCategory, MediaFormat
from app.db.models import Expression, Manifestation, Work, db
from app.utils.bgg import fetch_bgg_metadata
from app.utils.covers import start_cover_processing
from app.utils.discogs import fetch_discogs_metadata
from app.utils.isbn import fetch_isbn_metadata
from app.utils.musicbrainz import fetch_audio_metadata
from app.utils.tmdb import clean_video_title, fetch_video_metadata
from app.utils.upc import resolve_physical_media


class IngestService:
    @staticmethod
    def ingest_from_meta(meta: dict) -> Manifestation:
        """Save a manifestation from pre-fetched metadata without calling any external API.

        Used by the 'Save to Catalog Only' flow so we can persist the data the
        lookup endpoint already retrieved, avoiding redundant / slow network calls.
        The caller must include at minimum a ``title`` and ``format`` key.
        """
        title = meta.get("title") or meta.get("Title") or "Unknown Title"
        author_name = meta.get("author") or meta.get("artist") or (meta.get("authors") or meta.get("Authors") or [None])[0]
        cover_url = meta.get("cover_url") or meta.get("thumb") or meta.get("cover")
        raw_format = (meta.get("format") or meta.get("Format") or "audio").lower()

        from app.core.taxonomy import FORMAT_ALIAS_TO_CATEGORY

        # Map format string → FRBR content type (canonical formats + aliases)
        content_type = FORMAT_ALIAS_TO_CATEGORY.get(raw_format, MediaCategory.MUSIC)

        work_meta: dict = {"authors": [author_name] if author_name else []}
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

        work_meta = {"authors": [author_name]} if author_name else {}
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
        author_name = meta.get("author") or meta.get("authors", [None])[0] or meta.get("Artist")
        cover_url = meta.get("cover_url") or meta.get("cover") or meta.get("thumbnail")

        # Create FRBR hierarchy
        work_meta = {"authors": [author_name]} if author_name else {}
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
        work_meta = {"authors": [author_name]} if author_name else {}
        work = Work(title=title, meta=work_meta)
        db.session.add(work)
        db.session.flush()

        expression = Expression(work=work, language=meta.get("language", "en"), content_type=MediaCategory.MUSIC)
        db.session.add(expression)
        db.session.flush()

        if author_name:
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

        work_meta = {"authors": [author_name]} if author_name else {}
        work = Work(title=title, meta=work_meta)
        db.session.add(work)
        db.session.flush()

        expression = Expression(work=work, language=meta.get("language", "en"), content_type=MediaCategory.MOVIE)
        db.session.add(expression)
        db.session.flush()

        if author_name:
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
                    meta = upc_meta

        if not meta:
            meta = fetch_bgg_metadata(query)

        if not meta:
            raise ValueError("Board game metadata not found in external services.")

        title = meta.get("title") or meta.get("Title") or "Unknown Title"
        author_name = meta.get("author") or meta.get("designer") or (meta.get("Designers", [None])[0] if meta.get("Designers") else None)
        cover_url = meta.get("cover_url")
        mechanics = meta.get("Mechanics", []) or meta.get("mechanics", [])

        work_meta = {"authors": [author_name], "mechanics": mechanics} if author_name else {"mechanics": mechanics}
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

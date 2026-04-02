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
from app.core.frbr_service import add_work_contribution, get_or_create_contributor
from app.db.models import Expression, Manifestation, Work, db
from app.utils.discogs import fetch_discogs_metadata
from app.utils.isbn import fetch_isbn_metadata
from app.utils.musicbrainz import fetch_audio_metadata


class IngestService:
    @staticmethod
    def ingest_from_isbn(isbn: str) -> Manifestation:
        meta = fetch_isbn_metadata(isbn)
        if not meta:
            raise ValueError("ISBN metadata not found in external services.")

        # Create FRBR hierarchy
        author_name = meta.get("author")
        work_meta = {"authors": [author_name]} if author_name else {}
        work = Work(title=meta.get("title"), meta=work_meta)
        db.session.add(work)
        db.session.flush()

        if author_name:
            contributor = get_or_create_contributor(author_name, "person")
            add_work_contribution(work.id, contributor.id, "author")

        expression = Expression(work=work, language=meta.get("language", "en"))
        db.session.add(expression)

        manifestation = Manifestation(
            expression=expression,
            meta={"isbn": isbn, "cover_url": meta.get("cover_url"), "publisher": meta.get("publisher")},
        )
        db.session.add(manifestation)
        db.session.commit()

        return manifestation

    @staticmethod
    def ingest_audio_from_barcode(barcode: str) -> Manifestation:
        # Try Discogs first (if token is available inside the utility), then MusicBrainz
        meta = fetch_discogs_metadata(barcode) or fetch_audio_metadata(barcode)

        if not meta:
            raise ValueError("Audio metadata not found in external services.")

        # Create FRBR hierarchy
        author_name = meta.get("author")
        work_meta = {"authors": [author_name]} if author_name else {}
        work = Work(title=meta.get("title"), meta=work_meta)
        db.session.add(work)
        db.session.flush()

        if author_name:
            contributor = get_or_create_contributor(author_name, "person")
            add_work_contribution(work.id, contributor.id, "artist")

        expression = Expression(work=work, language=meta.get("language", "en"))
        db.session.add(expression)

        manifestation = Manifestation(
            expression=expression,
            meta={
                "barcode": barcode,
                "format": meta.get("format", "audio"),
                "cover_url": meta.get("cover_url"),
                "publisher": meta.get("publisher"),
            },
        )
        db.session.add(manifestation)
        db.session.commit()

        return manifestation

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
from app.db.models import Expression, Manifestation, Work, db
from app.utils.isbn import fetch_isbn_metadata  # Your external fetcher (Google Books/OpenLibrary)


class IngestService:
    @staticmethod
    def ingest_from_isbn(isbn: str) -> Manifestation:
        meta = fetch_isbn_metadata(isbn)
        if not meta:
            raise ValueError("ISBN metadata not found in external services.")

        # Create FRBR hierarchy
        work = Work(title=meta.get("title"), author=meta.get("author"))
        db.session.add(work)

        expression = Expression(work=work, language=meta.get("language", "en"))
        db.session.add(expression)

        manifestation = Manifestation(
            expression=expression,
            title=meta.get("title"),
            meta={"isbn": isbn, "cover_url": meta.get("cover_url"), "publisher": meta.get("publisher")},
        )
        db.session.add(manifestation)
        db.session.commit()

        return manifestation

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
from .frbr_service import create_work


def ingest_isbn(isbn):
    """
    Ingests a book from an ISBN.
    Fetches metadata from an external API and creates the FRBR objects.
    """
    # Placeholder for fetching data from a service like Open Library or Google Books
    # response = requests.get(f"https://openlibrary.org/isbn/{isbn}.json")
    # data = response.json()

    # Placeholder data
    data = {
        "title": "The Hobbit",
        "publishers": ["George Allen & Unwin"],
        "publish_date": "1937-09-21",
    }

    # This is a simplified example. A real implementation would need to handle
    # existing works, expressions, and manifestations.

    work = create_work(title=data["title"])
    # ... and so on

    return work

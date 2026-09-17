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
"""Tests for Schema.org SEO type mapping and enhanced RDF serialization."""

import pytest
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF

from app.core.frbr_service import SCHEMA, SCHEMA_TYPE_MAP, serialize_collection_to_rdf

FRBR = Namespace("http://iflastandards.info/ns/frbr/frbrer/")


class TestSchemaOrgTypeMapping:
    """Tests for Schema.org type expansion by content type."""

    def _serialize_and_parse(self, items):
        turtle = serialize_collection_to_rdf(items, "http://localhost:5000", output_format="turtle")
        g = Graph()
        g.parse(data=turtle, format="turtle")
        return g

    def test_text_maps_to_book(self):
        items = [
            {
                "id": "i1",
                "manifestation_id": "m1",
                "expression_id": "e1",
                "work_id": "w1",
                "title": "A Book",
                "authors": [],
                "tags": [],
                "status": None,
                "content_type": "text",
                "publisher": None,
                "language": None,
            }
        ]
        g = self._serialize_and_parse(items)
        m_uri = URIRef("http://localhost:5000/api/public/manifestations/m1")
        assert (m_uri, RDF.type, SCHEMA.Book) in g
        assert (m_uri, RDF.type, SCHEMA.CreativeWork) in g

    def test_music_maps_to_musicalbum(self):
        items = [
            {
                "id": "i1",
                "manifestation_id": "m1",
                "expression_id": "e1",
                "work_id": "w1",
                "title": "An Album",
                "authors": ["Artist"],
                "tags": [],
                "status": None,
                "content_type": "music",
                "publisher": "Label",
                "language": None,
            }
        ]
        g = self._serialize_and_parse(items)
        m_uri = URIRef("http://localhost:5000/api/public/manifestations/m1")
        assert (m_uri, RDF.type, SCHEMA.MusicAlbum) in g

    def test_movie_maps_to_movie(self):
        items = [
            {
                "id": "i1",
                "manifestation_id": "m1",
                "expression_id": "e1",
                "work_id": "w1",
                "title": "A Film",
                "authors": ["Director"],
                "tags": [],
                "status": None,
                "content_type": "movie",
                "publisher": None,
                "language": "en",
            }
        ]
        g = self._serialize_and_parse(items)
        m_uri = URIRef("http://localhost:5000/api/public/manifestations/m1")
        assert (m_uri, RDF.type, SCHEMA.Movie) in g

    def test_board_game_maps_to_game(self):
        items = [
            {
                "id": "i1",
                "manifestation_id": "m1",
                "expression_id": "e1",
                "work_id": "w1",
                "title": "A Game",
                "authors": [],
                "tags": [],
                "status": None,
                "content_type": "board_game",
                "publisher": "Publisher",
                "language": None,
            }
        ]
        g = self._serialize_and_parse(items)
        m_uri = URIRef("http://localhost:5000/api/public/manifestations/m1")
        assert (m_uri, RDF.type, SCHEMA.Game) in g

    def test_puzzle_maps_to_product(self):
        items = [
            {
                "id": "i1",
                "manifestation_id": "m1",
                "expression_id": "e1",
                "work_id": "w1",
                "title": "A Puzzle",
                "authors": [],
                "tags": [],
                "status": None,
                "content_type": "puzzle",
                "publisher": None,
                "language": None,
            }
        ]
        g = self._serialize_and_parse(items)
        m_uri = URIRef("http://localhost:5000/api/public/manifestations/m1")
        assert (m_uri, RDF.type, SCHEMA.Product) in g

    def test_audiobook_maps_to_audiobook(self):
        items = [
            {
                "id": "i1",
                "manifestation_id": "m1",
                "expression_id": "e1",
                "work_id": "w1",
                "title": "An Audiobook",
                "authors": ["Narrator"],
                "tags": [],
                "status": None,
                "content_type": "audiobook",
                "publisher": None,
                "language": "en",
            }
        ]
        g = self._serialize_and_parse(items)
        m_uri = URIRef("http://localhost:5000/api/public/manifestations/m1")
        assert (m_uri, RDF.type, SCHEMA.Audiobook) in g

    def test_publisher_included(self):
        items = [
            {
                "id": "i1",
                "manifestation_id": "m1",
                "expression_id": "e1",
                "work_id": "w1",
                "title": "Test",
                "authors": [],
                "tags": [],
                "status": None,
                "content_type": "text",
                "publisher": "Test Publisher",
                "language": None,
            }
        ]
        g = self._serialize_and_parse(items)
        m_uri = URIRef("http://localhost:5000/api/public/manifestations/m1")
        assert (m_uri, SCHEMA.publisher, Literal("Test Publisher")) in g

    def test_language_included(self):
        items = [
            {
                "id": "i1",
                "manifestation_id": "m1",
                "expression_id": "e1",
                "work_id": "w1",
                "title": "Test",
                "authors": [],
                "tags": [],
                "status": None,
                "content_type": "text",
                "publisher": None,
                "language": "fr",
            }
        ]
        g = self._serialize_and_parse(items)
        m_uri = URIRef("http://localhost:5000/api/public/manifestations/m1")
        assert (m_uri, SCHEMA.inLanguage, Literal("fr")) in g

    def test_no_content_type_still_has_creative_work(self):
        items = [
            {
                "id": "i1",
                "manifestation_id": "m1",
                "expression_id": "e1",
                "work_id": "w1",
                "title": "Unknown Type",
                "authors": [],
                "tags": [],
                "status": None,
                "content_type": None,
                "publisher": None,
                "language": None,
            }
        ]
        g = self._serialize_and_parse(items)
        m_uri = URIRef("http://localhost:5000/api/public/manifestations/m1")
        assert (m_uri, RDF.type, SCHEMA.CreativeWork) in g
        # Should NOT have a specific type
        for specific_type in SCHEMA_TYPE_MAP.values():
            assert (m_uri, RDF.type, specific_type) not in g

    def test_backward_compatible_dict_without_new_fields(self):
        """Items dicts without content_type/publisher/language still work."""
        items = [
            {
                "id": "i1",
                "manifestation_id": "m1",
                "expression_id": "e1",
                "work_id": "w1",
                "title": "Old Format",
                "isbn": "9780000000001",
                "authors": ["Author"],
                "tags": ["tag1"],
                "status": "read",
            }
        ]
        g = self._serialize_and_parse(items)
        m_uri = URIRef("http://localhost:5000/api/public/manifestations/m1")
        assert (m_uri, RDF.type, SCHEMA.CreativeWork) in g
        assert (m_uri, SCHEMA.name, Literal("Old Format")) in g

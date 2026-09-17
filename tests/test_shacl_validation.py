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
"""Tests for SHACL validation service."""

import pytest
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD

from app.core.shacl_service import validate_graph, validate_rdf_string

FRBR = Namespace("http://iflastandards.info/ns/frbr/frbrer/")
SCHEMA = Namespace("https://schema.org/")


class TestSHACLValidation:
    """Tests for SHACL shape validation of FRBR graphs."""

    def _build_valid_graph(self) -> Graph:
        """Build a minimal valid FRBR graph for testing."""
        g = Graph()
        g.bind("frbr", FRBR)
        g.bind("schema", SCHEMA)

        w_uri = URIRef("http://example.org/works/1")
        e_uri = URIRef("http://example.org/expressions/1")
        m_uri = URIRef("http://example.org/manifestations/1")
        i_uri = URIRef("http://example.org/items/1")

        # Work
        g.add((w_uri, RDF.type, FRBR.Work))
        g.add((w_uri, FRBR.creator, Literal("Test Author")))

        # Expression
        g.add((e_uri, RDF.type, FRBR.Expression))
        g.add((e_uri, FRBR.expressionOf, w_uri))

        # Manifestation
        g.add((m_uri, RDF.type, FRBR.Manifestation))
        g.add((m_uri, RDF.type, SCHEMA.CreativeWork))
        g.add((m_uri, FRBR.embodimentOf, e_uri))
        g.add((m_uri, SCHEMA.name, Literal("Test Book")))
        g.add((m_uri, SCHEMA.isbn, Literal("9780123456789")))

        # Item
        g.add((i_uri, RDF.type, FRBR.Item))
        g.add((i_uri, FRBR.exemplarOf, m_uri))

        return g

    def test_valid_graph_passes(self):
        g = self._build_valid_graph()
        conforms, _, results_text = validate_graph(g)
        assert conforms, f"Valid graph should conform. Violations: {results_text}"

    def test_manifestation_without_name_fails(self):
        g = Graph()
        g.bind("frbr", FRBR)
        g.bind("schema", SCHEMA)

        m_uri = URIRef("http://example.org/manifestations/1")
        e_uri = URIRef("http://example.org/expressions/1")

        g.add((e_uri, RDF.type, FRBR.Expression))
        g.add((e_uri, FRBR.expressionOf, URIRef("http://example.org/works/1")))
        g.add((URIRef("http://example.org/works/1"), RDF.type, FRBR.Work))

        g.add((m_uri, RDF.type, FRBR.Manifestation))
        g.add((m_uri, RDF.type, SCHEMA.CreativeWork))
        g.add((m_uri, FRBR.embodimentOf, e_uri))
        # Missing schema:name intentionally

        conforms, _, results_text = validate_graph(g)
        assert not conforms
        assert "schema:name" in results_text or "name" in results_text

    def test_invalid_isbn_pattern_fails(self):
        g = self._build_valid_graph()
        m_uri = URIRef("http://example.org/manifestations/1")
        # Remove valid ISBN and add invalid one
        g.remove((m_uri, SCHEMA.isbn, Literal("9780123456789")))
        g.add((m_uri, SCHEMA.isbn, Literal("invalid-isbn")))

        conforms, _, results_text = validate_graph(g)
        assert not conforms
        assert "ISBN" in results_text or "13 digits" in results_text

    def test_item_without_exemplarof_fails(self):
        g = Graph()
        g.bind("frbr", FRBR)
        g.bind("schema", SCHEMA)

        i_uri = URIRef("http://example.org/items/1")
        g.add((i_uri, RDF.type, FRBR.Item))
        # Missing frbr:exemplarOf

        conforms, _, results_text = validate_graph(g)
        assert not conforms
        assert "exemplarOf" in results_text

    def test_expression_without_expressionof_fails(self):
        g = Graph()
        g.bind("frbr", FRBR)

        e_uri = URIRef("http://example.org/expressions/1")
        g.add((e_uri, RDF.type, FRBR.Expression))
        # Missing frbr:expressionOf

        conforms, _, results_text = validate_graph(g)
        assert not conforms
        assert "expressionOf" in results_text

    def test_validate_rdf_string_turtle(self):
        turtle = """
        @prefix frbr: <http://iflastandards.info/ns/frbr/frbrer/> .
        @prefix schema: <https://schema.org/> .

        <http://ex.org/w/1> a frbr:Work ;
            frbr:creator "Author A" .
        <http://ex.org/e/1> a frbr:Expression ;
            frbr:expressionOf <http://ex.org/w/1> .
        <http://ex.org/m/1> a frbr:Manifestation, schema:CreativeWork ;
            frbr:embodimentOf <http://ex.org/e/1> ;
            schema:name "A Book" ;
            schema:isbn "9781234567890" .
        <http://ex.org/i/1> a frbr:Item ;
            frbr:exemplarOf <http://ex.org/m/1> .
        """
        conforms, report = validate_rdf_string(turtle, "turtle")
        assert conforms, f"Valid Turtle should conform: {report}"

    def test_validate_rdf_string_invalid(self):
        turtle = """
        @prefix frbr: <http://iflastandards.info/ns/frbr/frbrer/> .
        @prefix schema: <https://schema.org/> .

        <http://ex.org/m/1> a frbr:Manifestation, schema:CreativeWork ;
            frbr:embodimentOf <http://ex.org/e/1> ;
            schema:isbn "bad" .
        """
        conforms, _results_text = validate_rdf_string(turtle, "turtle")
        assert not conforms

    def test_serialize_collection_validates(self, app):
        """Test that the output of serialize_collection_to_rdf passes SHACL validation."""
        from app.core.frbr_service import serialize_collection_to_rdf

        items = [
            {
                "id": "item-1",
                "manifestation_id": "m-1",
                "expression_id": "e-1",
                "work_id": "w-1",
                "title": "Valid Book",
                "isbn": "9780000000001",
                "authors": ["Author"],
                "tags": ["fiction"],
                "status": "read",
            }
        ]
        turtle = serialize_collection_to_rdf(items, "http://localhost:5000", output_format="turtle")
        conforms, results_text = validate_rdf_string(turtle, "turtle")
        assert conforms, f"serialize_collection_to_rdf output should conform: {results_text}"

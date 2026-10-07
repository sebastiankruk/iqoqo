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
"""End-to-end tests for public RDF multi-chunk streaming serialization.

Verifies that streaming RDF responses spanning multiple chunks produce
syntactically and semantically valid concatenated documents across all supported
formats: JSON-LD (@graph container), Turtle (prefix deduplication), and N-Triples.
"""

import json
from unittest.mock import patch

import pytest
from rdflib import Graph, URIRef
from rdflib.namespace import RDF

import app.api.public_items as public_items_mod
from app.core.frbr_service import SCHEMA, stream_collection_to_rdf
from app.db.models import Expression, Item, Manifestation, User, Work, db


@pytest.fixture
def multi_chunk_user_and_items(app):
    """Set up a public user with multiple catalog items across FRBR tiers."""
    with app.app_context():
        user = User(
            email="streaming_e2e@iqoqo.local",
            display_name="Streaming E2E User",
            visibility="public",
            public_username="streaming_user",
        )
        user.set_password("valid-pass-12345")
        db.session.add(user)
        db.session.flush()

        items = []
        for i in range(1, 7):
            work = Work(title=f"Streaming Book {i}", meta={"authors": [f"Author {i}"]})
            db.session.add(work)
            db.session.flush()

            expr = Expression(work_id=work.id, content_type="book", language="en")
            db.session.add(expr)
            db.session.flush()

            manif = Manifestation(
                expression_id=expr.id,
                isbn13=f"97800000000{i:02d}",
                publisher=f"Publisher {i}",
            )
            db.session.add(manif)
            db.session.flush()

            item = Item(owner_id=user.id, manifestation_id=manif.id, status="read", is_hidden=False)
            db.session.add(item)
            items.append(item)

        db.session.commit()

        return {
            "username": "streaming_user",
            "user_id": user.id,
            "item_count": len(items),
        }


class TestPublicRDFStreamingE2E:
    """End-to-end verification of multi-chunk streaming across RDF formats."""

    def test_jsonld_multi_chunk_streaming_valid(self, client, multi_chunk_user_and_items, monkeypatch):
        """JSON-LD streaming across >1 chunk must produce a single valid JSON-LD document with @graph."""
        username = multi_chunk_user_and_items["username"]
        orig_stream = stream_collection_to_rdf

        def chunked_stream(*args, **kwargs):
            kwargs["chunk_size"] = 2
            return orig_stream(*args, **kwargs)

        monkeypatch.setattr(public_items_mod, "stream_collection_to_rdf", chunked_stream)

        response = client.get(f"/api/public/u/{username}/items?format=json-ld&stream=true")
        assert response.status_code == 200
        assert "application/ld+json" in response.headers.get("Content-Type", "")

        raw_data = response.data.decode("utf-8")
        assert raw_data.strip()

        # Concatenated payload must be valid JSON
        doc = json.loads(raw_data)
        assert "@context" in doc
        assert "@graph" in doc
        assert isinstance(doc["@graph"], list)
        assert len(doc["@graph"]) >= multi_chunk_user_and_items["item_count"]

        # Concatenated payload must parse into an RDF graph without error
        g = Graph()
        g.parse(data=raw_data, format="json-ld")
        assert len(g) > 0

        # Assert all manifestations exist in the parsed graph
        for i in range(1, multi_chunk_user_and_items["item_count"] + 1):
            assert any(f"97800000000{i:02d}" in str(o) for _, _, o in g)

    def test_turtle_multi_chunk_streaming_valid(self, client, multi_chunk_user_and_items, monkeypatch):
        """Turtle streaming across >1 chunk must concatenate cleanly without duplicate prefix syntax errors."""
        username = multi_chunk_user_and_items["username"]
        orig_stream = stream_collection_to_rdf

        def chunked_stream(*args, **kwargs):
            kwargs["chunk_size"] = 2
            return orig_stream(*args, **kwargs)

        monkeypatch.setattr(public_items_mod, "stream_collection_to_rdf", chunked_stream)

        response = client.get(f"/api/public/u/{username}/items?format=turtle&stream=true")
        assert response.status_code == 200
        assert "text/turtle" in response.headers.get("Content-Type", "")

        raw_data = response.data.decode("utf-8")
        assert raw_data.strip()

        # Concatenated payload must parse into an RDF graph without syntax error
        g = Graph()
        g.parse(data=raw_data, format="turtle")
        assert len(g) > 0

        # Assert all manifestations exist in the parsed graph
        for i in range(1, multi_chunk_user_and_items["item_count"] + 1):
            assert any(f"97800000000{i:02d}" in str(o) for _, _, o in g)

    def test_ntriples_multi_chunk_streaming_valid(self, client, multi_chunk_user_and_items, monkeypatch):
        """N-Triples streaming across >1 chunk must concatenate cleanly and parse into valid RDF."""
        username = multi_chunk_user_and_items["username"]
        orig_stream = stream_collection_to_rdf

        def chunked_stream(*args, **kwargs):
            kwargs["chunk_size"] = 2
            return orig_stream(*args, **kwargs)

        monkeypatch.setattr(public_items_mod, "stream_collection_to_rdf", chunked_stream)

        response = client.get(f"/api/public/u/{username}/items?format=nt&stream=true")
        assert response.status_code == 200
        assert "application/n-triples" in response.headers.get("Content-Type", "")

        raw_data = response.data.decode("utf-8")
        assert raw_data.strip()

        # Concatenated payload must parse into an RDF graph without syntax error
        g = Graph()
        g.parse(data=raw_data, format="nt")
        assert len(g) > 0

        # Assert all manifestations exist in the parsed graph
        for i in range(1, multi_chunk_user_and_items["item_count"] + 1):
            assert any(f"97800000000{i:02d}" in str(o) for _, _, o in g)

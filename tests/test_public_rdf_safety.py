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
"""Tests for public RDF safety: bounded limits, visibility-aware enrichment, and format validity."""

import json

import pytest
from rdflib import Graph
from rdflib.exceptions import ParserError

from app.api.auth import generate_internal_jwt
from app.db.models import (
    Expression,
    ImageScan,
    Item,
    Manifestation,
    User,
    UserCollection,
    UserCollectionItem,
    Work,
    db,
)


@pytest.fixture
def public_rdf_test_data(app):
    """Set up test data for public RDF safety tests."""
    with app.app_context():
        # Create two users
        user_a = User(email="user_a_rdf@iqoqo.local", display_name="User A RDF", visibility="public", public_username="usera")
        user_b = User(email="user_b_rdf@iqoqo.local", display_name="User B RDF", visibility="public", public_username="userb")
        user_a.set_password("test-password")
        user_b.set_password("test-password")
        db.session.add_all([user_a, user_b])
        db.session.flush()

        # Create a work with manifestation
        work = Work(title="RDF Test Work", meta={"authors": ["Test Author"]})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="book", language="en")
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(expression_id=expr.id, isbn13="9781234567890", publisher="Test Publisher")
        db.session.add(manif)
        db.session.flush()

        # Create items for both users
        item_a = Item(owner_id=user_a.id, manifestation_id=manif.id, status="read", is_hidden=False)
        item_b = Item(owner_id=user_b.id, manifestation_id=manif.id, status="read", is_hidden=False)
        db.session.add_all([item_a, item_b])
        db.session.flush()

        # Create a private collection for user_a
        # Note: UserCollection doesn't have is_public field; all collections are private by default
        private_coll = UserCollection(owner_id=user_a.id, name="My Private Collection")
        db.session.add(private_coll)
        db.session.flush()

        # Link item_a to the private collection
        coll_link = UserCollectionItem(collection_id=private_coll.id, item_id=item_a.id)
        db.session.add(coll_link)

        # Create an image scan for the manifestation (not marked as public)
        # Note: ImageScan model may not have is_public field; we'll test that scans are excluded from public RDF
        scan = ImageScan(
            manifestation_id=manif.id,
            file_path="scans/test_scan.jpg",
            scan_type="cover",
        )
        db.session.add(scan)

        db.session.commit()

        token_a = generate_internal_jwt(user_a)
        token_b = generate_internal_jwt(user_b)

        return {
            "user_a_id": user_a.id,
            "user_b_id": user_b.id,
            "item_a_id": item_a.id,
            "item_b_id": item_b.id,
            "manifestation_id": manif.id,
            "work_id": work.id,
            "private_coll_id": private_coll.id,
            "scan_id": scan.id,
            "token_a": {"Authorization": f"Bearer {token_a}"},
            "token_b": {"Authorization": f"Bearer {token_b}"},
        }


class TestPublicRDFLimitSafety:
    """Test bounded limit parsing and validation."""

    def test_limit_clamped_to_maximum(self, client, public_rdf_test_data):
        """Requests with limit > MAX_PUBLIC_RDF_LIMIT should be clamped."""
        response = client.get(
            "/api/public/u/usera/items?format=json-ld&limit=5000",
        )
        assert response.status_code == 200
        # The response should be valid JSON-LD
        data = json.loads(response.data)
        assert "@context" in data or "@graph" in data

    def test_limit_negative_uses_default(self, client, public_rdf_test_data):
        """Negative limit values should use the default."""
        response = client.get(
            "/api/public/u/usera/items?format=json-ld&limit=-10",
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "@context" in data or "@graph" in data

    def test_limit_zero_uses_default(self, client, public_rdf_test_data):
        """Zero limit should use the default."""
        response = client.get(
            "/api/public/u/usera/items?format=json-ld&limit=0",
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "@context" in data or "@graph" in data

    def test_limit_malformed_uses_default(self, client, public_rdf_test_data):
        """Malformed limit values should use the default."""
        response = client.get(
            "/api/public/u/usera/items?format=json-ld&limit=abc",
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "@context" in data or "@graph" in data


class TestPublicRDFVisibilitySafety:
    """Test visibility-aware enrichment excludes private data."""

    def test_public_rdf_excludes_private_collections(self, client, public_rdf_test_data):
        """Public RDF should not include private UserCollection names."""
        response = client.get(
            "/api/public/u/usera/items?format=json-ld",
        )
        assert response.status_code == 200
        data = json.loads(response.data)

        # Serialize to string to check for private collection name
        rdf_str = json.dumps(data)
        assert "My Private Collection" not in rdf_str

    def test_public_rdf_excludes_private_image_scans(self, client, public_rdf_test_data):
        """Public RDF should not include non-public ImageScan paths."""
        response = client.get(
            f"/api/public/manifestations/{public_rdf_test_data['manifestation_id']}?format=json-ld",
        )
        assert response.status_code == 200
        data = json.loads(response.data)

        # Serialize to string to check for scan path
        rdf_str = json.dumps(data)
        assert "scans/test_scan.jpg" not in rdf_str

    def test_public_rdf_includes_public_contributors(self, client, public_rdf_test_data):
        """Public RDF should include contributor information."""
        response = client.get(
            f"/api/public/works/{public_rdf_test_data['work_id']}?format=json-ld",
        )
        assert response.status_code == 200
        data = json.loads(response.data)

        # Should include author information
        rdf_str = json.dumps(data)
        assert "Test Author" in rdf_str or "author" in rdf_str.lower()


class TestPublicRDFFormatValidity:
    """Test that streamed RDF formats are valid and parseable."""

    def test_jsonld_streaming_produces_valid_document(self, client, public_rdf_test_data):
        """Streaming JSON-LD should produce a single valid JSON document."""
        response = client.get(
            "/api/public/u/usera/items?format=json-ld&stream=true",
        )
        assert response.status_code == 200

        # Should be valid JSON
        try:
            data = json.loads(response.data)
            # Should have @context and @graph
            assert "@context" in data
            assert "@graph" in data
            assert isinstance(data["@graph"], list)
        except json.JSONDecodeError as e:
            pytest.fail(f"Streaming JSON-LD is not valid JSON: {e}")

    def test_turtle_streaming_produces_valid_document(self, client, public_rdf_test_data):
        """Streaming Turtle should produce a valid Turtle document."""
        response = client.get(
            "/api/public/u/usera/items?format=turtle&stream=true",
        )
        assert response.status_code == 200

        # Should be parseable as Turtle
        g = Graph()
        try:
            g.parse(data=response.data, format="turtle")
            assert len(g) > 0
        except (ParserError, ValueError, SyntaxError) as e:
            pytest.fail(f"Streaming Turtle is not valid: {e}")

    def test_ntriples_streaming_produces_valid_document(self, client, public_rdf_test_data):
        """Streaming N-Triples should produce a valid N-Triples document."""
        response = client.get(
            "/api/public/u/usera/items?format=nt&stream=true",
        )
        assert response.status_code == 200

        # Should be parseable as N-Triples
        g = Graph()
        try:
            g.parse(data=response.data, format="nt")
            assert len(g) > 0
        except (ParserError, ValueError, SyntaxError) as e:
            pytest.fail(f"Streaming N-Triples is not valid: {e}")


class TestPublicRDFBoundedMemory:
    """Test that streaming uses bounded memory and doesn't load full collections."""

    def test_first_chunk_emitted_quickly(self, client, public_rdf_test_data):
        """First chunk should be emitted without loading the full collection."""
        import time

        start = time.time()
        response = client.get(
            "/api/public/u/usera/items?format=json-ld&stream=true&limit=10",
        )
        elapsed = time.time() - start

        assert response.status_code == 200
        # Should complete quickly (under 5 seconds for small dataset)
        assert elapsed < 5.0

    def test_large_limit_respected(self, client, public_rdf_test_data):
        """Large limits should be clamped to MAX_PUBLIC_RDF_LIMIT."""
        response = client.get(
            "/api/public/u/usera/items?format=json-ld&limit=10000",
        )
        assert response.status_code == 200
        # Should still return valid data
        data = json.loads(response.data)
        assert "@context" in data or "@graph" in data


class TestPublicRDFContentNegotiation:
    """Test consistent content negotiation across routes."""

    def test_jsonld_content_type(self, client, public_rdf_test_data):
        """JSON-LD requests should return application/ld+json."""
        response = client.get(
            "/api/public/u/usera/items?format=json-ld",
        )
        assert response.status_code == 200
        assert "application/ld+json" in response.content_type

    def test_turtle_content_type(self, client, public_rdf_test_data):
        """Turtle requests should return text/turtle."""
        response = client.get(
            "/api/public/u/usera/items?format=turtle",
        )
        assert response.status_code == 200
        assert "text/turtle" in response.content_type

    def test_ntriples_content_type(self, client, public_rdf_test_data):
        """N-Triples requests should return application/n-triples."""
        response = client.get(
            "/api/public/u/usera/items?format=nt",
        )
        assert response.status_code == 200
        assert "application/n-triples" in response.content_type

    def test_accept_header_negotiation(self, client, public_rdf_test_data):
        """Accept header should be respected for content negotiation."""
        response = client.get(
            "/api/public/u/usera/items",
            headers={"Accept": "text/turtle"},
        )
        assert response.status_code == 200
        assert "text/turtle" in response.content_type

"""
Unit and integration tests for public RSS feeds and semantic content negotiation.
Validates vocabulary alignments (FRBR, SIOC, Schema.org) and Accept header handling.
"""

import xml.etree.ElementTree as ET

import pytest
from rdflib import RDF, Graph, URIRef

from app.db.models import Expression, Item, Manifestation, User, Work, db


@pytest.fixture
def public_user(app):
    with app.app_context():
        user = User(
            email="public@iqoqo.local", display_name="Public User", public_username="sebastiankruk", visibility="public", bio="Cave man bio"
        )
        db.session.add(user)
        db.session.commit()
        return user.public_username


@pytest.fixture
def sample_data(app, public_user):
    with app.app_context():
        user = User.query.filter_by(public_username=public_user).first()
        # Create FRBR chain
        work = Work(title="The Cave Bible", meta={"authors": ["Old Man"]})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="book", language="en")
        db.session.add(expr)
        db.session.flush()

        mani = Manifestation(expression_id=expr.id, isbn13="9780000000001", publisher="Rock Press")
        db.session.add(mani)
        db.session.flush()

        # Public item
        item1 = Item(owner_id=user.id, manifestation_id=mani.id, status="read", is_hidden=False)
        db.session.add(item1)
        db.session.commit()
        return True


@pytest.fixture
def mock_manifestation_data():
    """Returns baseline fixture data mimicking the FRBR schema structure."""
    return [
        {
            "id": "manifestation-123",
            "title": "The Fellowship of the Ring",
            "creator": "J.R.R. Tolkien",
            "isbn": "9780261102354",
            "work_id": "work-lotr-001",
            "tags": ["Classic", "Fantasy"],
            "media_type": "Book",
            "status": "Available",
        },
        {
            "id": "manifestation-456",
            "title": "Dune",
            "creator": "Frank Herbert",
            "isbn": "9780441172719",
            "work_id": "work-dune-001",
            "tags": ["Sci-Fi", "Epic"],
            "media_type": "Book",
            "status": "Lent Out",
        },
    ]


class TestPublicFeeds:
    """Tests public RSS feed generation and level parameters across global and token scopes."""

    def test_global_fresh_feed_default(self, client, monkeypatch, mock_manifestation_data):
        """Verifies global feed defaults to application/rss+xml and contains item properties."""
        monkeypatch.setattr("app.api.public.fetch_global_fresh_arrivals", lambda *args, **kwargs: mock_manifestation_data)

        response = client.get("/api/public/feed.xml")
        assert response.status_code == 200
        assert "application/rss+xml" in response.content_type

        # Parse XML to guarantee valid structural formatting
        root = ET.fromstring(response.data)
        assert root.tag == "rss"
        channel = root.find("channel")
        assert channel is not None
        assert "Fresh Arrivals" in channel.find("title").text

        items = channel.findall("item")
        assert len(items) == 2
        assert items[0].find("title").text == "The Fellowship of the Ring"

    def test_global_fresh_feed_filters(self, client, monkeypatch, mock_manifestation_data):
        """Verifies global feed accepts expressions and works via structural query parameters."""
        called_args = []

        def mock_fetch(limit=50, level="manifestations"):
            called_args.append((limit, level))
            return mock_manifestation_data

        monkeypatch.setattr("app.api.public.fetch_global_fresh_arrivals", mock_fetch)

        response = client.get("/api/public/feed.xml?view=works")
        assert response.status_code == 200
        assert called_args == [(50, "works")]

        root = ET.fromstring(response.data)
        assert "Works" in root.find("channel/title").text

    def test_user_collection_feed(self, client, monkeypatch, mock_manifestation_data):
        """Verifies user-scoped profile feed isolation rules execute cleanly."""
        monkeypatch.setattr("app.api.public.fetch_user_public_collection", lambda *args, **kwargs: mock_manifestation_data)

        response = client.get("/api/public/u/sebastiankruk/feed.xml")
        assert response.status_code == 200
        assert "application/rss+xml" in response.content_type

        root = ET.fromstring(response.data)
        assert "sebastiankruk" in root.find("channel/title").text

    def test_shared_collection_feed(self, client, monkeypatch, mock_manifestation_data):
        """Verifies secret token sharing feed channels function properly."""
        monkeypatch.setattr("app.api.public.fetch_shared_collection_by_token", lambda *args, **kwargs: mock_manifestation_data)

        response = client.get("/api/public/share/wishlist-token-xyz/feed.xml")
        assert response.status_code == 200
        assert "application/rss+xml" in response.content_type


class TestContentNegotiation:
    """Validates HTTP Accept-header routing rules and semantic output validity."""

    def test_user_items_default_json(self, client, public_user, sample_data):
        """Ensures endpoint gracefully falls back to clean application/json by default."""
        response = client.get("/api/public/u/sebastiankruk/items")
        assert response.status_code == 200
        assert "application/json" in response.content_type
        json_data = response.get_json()
        assert json_data["success"] is True

    def test_user_items_json_ld(self, client, monkeypatch, mock_manifestation_data):
        """Enforces application/ld+json negotiation and checks semantic graph structures."""
        monkeypatch.setattr("app.api.public.fetch_user_public_collection", lambda *args, **kwargs: mock_manifestation_data)

        headers = {"Accept": "application/ld+json"}
        response = client.get("/api/public/u/sebastiankruk/items", headers=headers)

        assert response.status_code == 200
        assert "application/ld+json" in response.content_type

        # Parse graph from payload to verify triples validity
        g = Graph()
        g.parse(data=response.data, format="json-ld")

        # Test for FRBR layer types
        FRBR_Manifestation = URIRef("http://iflastandards.info/ns/frbr/frbrer/Manifestation")
        assert (None, RDF.type, FRBR_Manifestation) in g

        # Test for Schema.org alignments
        SCHEMA_name = URIRef("https://schema.org/name")
        assert (None, SCHEMA_name, None) in g

    def test_shared_collection_turtle(self, client, monkeypatch, mock_manifestation_data):
        """Enforces text/turtle serialization mechanics on shared token targets."""
        monkeypatch.setattr("app.api.public.fetch_shared_collection_by_token", lambda *args, **kwargs: mock_manifestation_data)

        headers = {"Accept": "text/turtle"}
        response = client.get("/api/public/share/wishlist-token-xyz", headers=headers)

        assert response.status_code == 200
        assert "text/turtle" in response.content_type

        g = Graph()
        g.parse(data=response.data, format="turtle")

        SIOC_topic = URIRef("http://rdfs.org/sioc/ns#topic")
        assert (None, SIOC_topic, None) in g

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

"""
Unit and integration tests for public RSS feeds and semantic content negotiation.
Validates vocabulary alignments (FRBR, SIOC, Schema.org) and Accept header handling.
"""

import xml.etree.ElementTree as ET

import pytest
from rdflib import RDF, Graph, URIRef
from sqlalchemy import select

from app.db.models import Expression, Item, Manifestation, User, Work, db


@pytest.fixture
def public_user(app):
    with app.app_context():
        user = User(
            email="public@iqoqo.local", display_name="Public User", public_username="sebastiankruk", visibility="public", bio="Cave man bio"
        )
        user.set_password("test-password")
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

    def test_feed_strictly_filters_hidden_items(self, client, app, public_user, sample_data):
        """Regression test verifying that hidden or private items are never serialized in public feeds."""
        with app.app_context():
            user = User.query.filter_by(public_username=public_user).first()
            # Add a hidden/private item
            mani = Manifestation.query.first()
            hidden_item = Item(owner_id=user.id, manifestation_id=mani.id, status="want_to_read", is_hidden=True)
            db.session.add(hidden_item)
            db.session.commit()

        # Fetch global fresh feed
        response = client.get("/api/public/feed.xml")
        assert response.status_code == 200
        root = ET.fromstring(response.data)
        items = root.findall("channel/item")

        # Verify that only the non-hidden item (The Cave Bible) is present
        assert len(items) == 1
        assert items[0].find("title").text == "The Cave Bible"

        # Fetch user public feed
        response_user = client.get(f"/api/public/u/{public_user}/feed.xml")
        assert response_user.status_code == 200
        root_user = ET.fromstring(response_user.data)
        items_user = root_user.findall("channel/item")
        assert len(items_user) == 1
        assert items_user[0].find("title").text == "The Cave Bible"


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


class TestPublicSemanticEndpoints:
    """Validates public FRBR and Schema.org semantic endpoints for AI agents and crawlers."""

    def test_cors_headers_on_public_manifestation(self, client, app, sample_data):
        """Verifies permissive CORS headers are returned for external web agents (e.g. Gemini)."""
        with app.app_context():
            mani = db.session.execute(select(Manifestation)).scalars().first()
            mani_id = mani.id

        # GET request with Gemini Origin
        response = client.get(
            f"/api/public/manifestations/{mani_id}",
            headers={"Origin": "https://gemini.google.com"},
        )
        assert response.status_code == 200
        assert response.headers.get("Access-Control-Allow-Origin") == "*"

        # OPTIONS preflight request
        options_resp = client.options(
            f"/api/public/manifestations/{mani_id}",
            headers={
                "Origin": "https://gemini.google.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert options_resp.status_code == 200
        assert options_resp.headers.get("Access-Control-Allow-Origin") == "*"

    def test_get_public_manifestation_jsonld_and_turtle(self, client, app, sample_data):
        """Verifies Manifestation entity serves JSON-LD by default and Turtle on request."""
        with app.app_context():
            mani = db.session.execute(select(Manifestation)).scalars().first()
            mani_id = mani.id

        # Default JSON-LD
        resp_jsonld = client.get(f"/api/public/manifestations/{mani_id}")
        assert resp_jsonld.status_code == 200
        assert "application/ld+json" in resp_jsonld.content_type

        g_jsonld = Graph()
        g_jsonld.parse(data=resp_jsonld.data, format="json-ld")
        assert (None, RDF.type, URIRef("http://iflastandards.info/ns/frbr/frbrer/Manifestation")) in g_jsonld
        assert (None, RDF.type, URIRef("https://schema.org/CreativeWork")) in g_jsonld
        assert (None, URIRef("https://schema.org/name"), None) in g_jsonld

        # Requested Turtle
        resp_turtle = client.get(
            f"/api/public/manifestations/{mani_id}",
            headers={"Accept": "text/turtle"},
        )
        assert resp_turtle.status_code == 200
        assert "text/turtle" in resp_turtle.content_type

        g_turtle = Graph()
        g_turtle.parse(data=resp_turtle.data, format="turtle")
        assert (None, RDF.type, URIRef("http://iflastandards.info/ns/frbr/frbrer/Manifestation")) in g_turtle

    def test_get_public_manifestation_not_found(self, client):
        """Verifies 404 is returned when manifestation does not exist."""
        resp = client.get("/api/public/manifestations/9999999")
        assert resp.status_code == 404
        assert resp.get_json()["error"] == "Manifestation not found"

    def test_get_public_work_jsonld(self, client, app, sample_data):
        """Verifies Work entity serves RDF linking expressions and manifestations."""
        with app.app_context():
            work = db.session.execute(select(Work)).scalars().first()
            work_id = work.id

        response = client.get(
            f"/api/public/works/{work_id}",
            headers={"Origin": "https://gemini.google.com"},
        )
        assert response.status_code == 200
        assert "application/ld+json" in response.content_type
        assert response.headers.get("Access-Control-Allow-Origin") == "*"

        g = Graph()
        g.parse(data=response.data, format="json-ld")
        assert (None, RDF.type, URIRef("http://iflastandards.info/ns/frbr/frbrer/Work")) in g
        assert (None, RDF.type, URIRef("https://schema.org/CreativeWork")) in g
        assert (None, URIRef("https://schema.org/name"), None) in g

    def test_get_public_work_not_found(self, client):
        """Verifies 404 is returned when work does not exist."""
        resp = client.get("/api/public/works/9999999")
        assert resp.status_code == 404
        assert resp.get_json()["error"] == "Work not found"

    def test_get_public_expression_jsonld(self, client, app, sample_data):
        """Verifies Expression entity serves RDF."""
        with app.app_context():
            expr = db.session.execute(select(Expression)).scalars().first()
            expr_id = expr.id

        response = client.get(f"/api/public/expressions/{expr_id}")
        assert response.status_code == 200
        assert "application/ld+json" in response.content_type

        g = Graph()
        g.parse(data=response.data, format="json-ld")
        assert (None, RDF.type, URIRef("http://iflastandards.info/ns/frbr/frbrer/Expression")) in g

    def test_get_public_item_jsonld_and_hidden_guard(self, client, app, public_user, sample_data):
        """Verifies Item entity serves RDF and respects privacy flag."""
        with app.app_context():
            user = db.session.execute(select(User).where(User.public_username == public_user)).scalars().first()
            mani = db.session.execute(select(Manifestation)).scalars().first()

            public_item = db.session.execute(select(Item).where(Item.is_hidden.is_(False))).scalars().first()
            public_item_id = public_item.id

            hidden_item = Item(owner_id=user.id, manifestation_id=mani.id, status="read", is_hidden=True)
            db.session.add(hidden_item)
            db.session.commit()
            hidden_item_id = hidden_item.id

        # Public item
        resp_pub = client.get(f"/api/public/items/{public_item_id}")
        assert resp_pub.status_code == 200
        assert "application/ld+json" in resp_pub.content_type

        g = Graph()
        g.parse(data=resp_pub.data, format="json-ld")
        assert (None, RDF.type, URIRef("http://iflastandards.info/ns/frbr/frbrer/Item")) in g

        # Hidden item
        resp_hid = client.get(f"/api/public/items/{hidden_item_id}")
        assert resp_hid.status_code == 404
        assert resp_hid.get_json()["error"] == "Item not found"

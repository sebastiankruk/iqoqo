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
"""Tests for user collection RDF export endpoint."""

import json

import pytest
from rdflib import Graph, URIRef

from app.db.models import Expression, Item, Manifestation, User, Work, db


@pytest.fixture
def export_user(app):
    """Create a user with a full FRBR collection for export testing."""
    from app.api.auth import generate_internal_jwt
    from app.db.models import Permission, Role

    with app.app_context():
        user_role = Role(name="export_user_role")
        write_perm = Permission.query.filter_by(name="write:item").first()
        if not write_perm:
            write_perm = Permission(name="write:item")
            db.session.add(write_perm)
        user_role.permissions.append(write_perm)
        db.session.add(user_role)

        user = User(email="export@iqoqo.local", display_name="Export User")
        user.roles.append(user_role)
        db.session.add(user)
        db.session.flush()

        # Create full FRBR chain
        work = Work(title="Export Test Book", meta={"authors": ["Jane Doe", "John Smith"]})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="book", language="en", meta={"tags": ["science", "tech"]})
        db.session.add(expr)
        db.session.flush()

        mani = Manifestation(expression_id=expr.id, isbn13="9781111111111", publisher="Test Press")
        db.session.add(mani)
        db.session.flush()

        item = Item(owner_id=user.id, manifestation_id=mani.id, status="read", is_hidden=False)
        db.session.add(item)

        # Second item (different type)
        work2 = Work(title="Export Test Album", meta={"authors": ["DJ Test"]})
        db.session.add(work2)
        db.session.flush()

        expr2 = Expression(work_id=work2.id, content_type="sound", language="en")
        db.session.add(expr2)
        db.session.flush()

        mani2 = Manifestation(expression_id=expr2.id, publisher="Music Inc")
        db.session.add(mani2)
        db.session.flush()

        item2 = Item(owner_id=user.id, manifestation_id=mani2.id, status="listening", is_hidden=False)
        db.session.add(item2)

        db.session.commit()

        token = generate_internal_jwt(user)
        return {"Authorization": f"Bearer {token}", "user_id": str(user.id)}


@pytest.fixture
def other_user_with_items(app):
    """Create another user with items to verify isolation."""
    from app.api.auth import generate_internal_jwt
    from app.db.models import Permission, Role

    with app.app_context():
        user_role = Role.query.filter_by(name="export_user_role").first()
        if not user_role:
            user_role = Role(name="other_role")
            write_perm = Permission.query.filter_by(name="write:item").first()
            if not write_perm:
                write_perm = Permission(name="write:item")
                db.session.add(write_perm)
            user_role.permissions.append(write_perm)
            db.session.add(user_role)

        other_user = User(email="other@iqoqo.local", display_name="Other User")
        other_user.roles.append(user_role)
        db.session.add(other_user)
        db.session.flush()

        work = Work(title="Other User's Private Book", meta={"authors": ["Private Author"]})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="book", language="fr")
        db.session.add(expr)
        db.session.flush()

        mani = Manifestation(expression_id=expr.id, isbn13="9782222222222")
        db.session.add(mani)
        db.session.flush()

        item = Item(owner_id=other_user.id, manifestation_id=mani.id, status="to_read", is_hidden=False)
        db.session.add(item)
        db.session.commit()

        token = generate_internal_jwt(other_user)
        return {"Authorization": f"Bearer {token}"}


class TestUserExport:
    """Tests for user-facing collection export."""

    def test_export_json_format(self, client, export_user):
        response = client.get("/api/v1/items/export?format=json", headers=export_user)
        assert response.status_code == 200
        assert "application/json" in response.content_type
        data = json.loads(response.data)
        assert len(data) == 2
        titles = [d.get("work_title") or d.get("title") for d in data]
        assert "Export Test Book" in titles

    def test_export_json_contains_frbr_fields(self, client, export_user):
        response = client.get("/api/v1/items/export?format=json", headers=export_user)
        data = json.loads(response.data)
        book = next(d for d in data if d.get("work_title") == "Export Test Book")
        assert book["isbn13"] == "9781111111111"
        assert book["content_type"] == "book"
        assert "Jane Doe" in book["authors"]
        assert book["publisher"] == "Test Press"

    def test_export_jsonld_format(self, client, export_user):
        response = client.get("/api/v1/items/export?format=json-ld", headers=export_user)
        assert response.status_code == 200
        assert "application/ld+json" in response.content_type
        # Verify it's valid JSON-LD by parsing with rdflib
        g = Graph()
        g.parse(data=response.data, format="json-ld")
        assert len(g) > 0
        # Check FRBR types exist
        FRBR_Manifestation = URIRef("http://iflastandards.info/ns/frbr/frbrer/Manifestation")
        FRBR_Work = URIRef("http://iflastandards.info/ns/frbr/frbrer/Work")
        from rdflib import RDF

        assert (None, RDF.type, FRBR_Manifestation) in g
        assert (None, RDF.type, FRBR_Work) in g

    def test_export_turtle_format(self, client, export_user):
        response = client.get("/api/v1/items/export?format=turtle", headers=export_user)
        assert response.status_code == 200
        assert "text/turtle" in response.content_type
        # Verify valid Turtle
        g = Graph()
        g.parse(data=response.data, format="turtle")
        assert len(g) > 0

    def test_export_unsupported_format(self, client, export_user):
        response = client.get("/api/v1/items/export?format=xml", headers=export_user)
        assert response.status_code == 400
        assert "Unsupported format" in response.get_json()["error"]

    def test_export_unauthenticated(self, client):
        response = client.get("/api/v1/items/export?format=json")
        assert response.status_code == 401

    def test_export_isolation(self, client, export_user, other_user_with_items):
        """Verify a user can only export their own items."""
        response = client.get("/api/v1/items/export?format=json", headers=export_user)
        data = json.loads(response.data)
        # Should only see export_user's 2 items, not other_user's
        assert len(data) == 2
        for item in data:
            assert item.get("work_title") != "Other User's Private Book"

    def test_export_jsonld_contains_schema_org(self, client, export_user):
        response = client.get("/api/v1/items/export?format=json-ld", headers=export_user)
        g = Graph()
        g.parse(data=response.data, format="json-ld")
        SCHEMA_name = URIRef("https://schema.org/name")
        assert (None, SCHEMA_name, None) in g

    def test_export_turtle_contains_isbn(self, client, export_user):
        response = client.get("/api/v1/items/export?format=turtle", headers=export_user)
        assert b"9781111111111" in response.data

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
"""Tests for enriched RDF serialization, SHACL import validation, and sitemap."""

import json

import pytest
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF

SCHEMA = Namespace("https://schema.org/")
FRBR = Namespace("http://iflastandards.info/ns/frbr/frbrer/")


@pytest.fixture
def enriched_user(app):
    """Create a user with contributors, work parts, image scans, and collections."""
    from app.api.auth import generate_internal_jwt
    from app.db.audio import Contributor, ExpressionContribution, WorkContribution, WorkPart
    from app.db.core import Expression, ImageScan, Item, Manifestation, UserCollection, UserCollectionItem, Work
    from app.db.models import Permission, Role, User, db

    with app.app_context():
        user_role = Role(name="enriched_user_role")
        write_perm = Permission.query.filter_by(name="write:item").first()
        if not write_perm:
            write_perm = Permission(name="write:item")
            db.session.add(write_perm)
        user_role.permissions.append(write_perm)
        db.session.add(user_role)

        user = User(email="enriched@iqoqo.local", display_name="Enriched User")
        user.roles.append(user_role)
        db.session.add(user)
        db.session.flush()

        # Create Works
        work1 = Work(title="Symphony No. 5", meta={"authors": ["Beethoven"]})
        work2 = Work(title="Symphony No. 5 - Movement 1", meta={})
        db.session.add_all([work1, work2])
        db.session.flush()

        # WorkPart relationship
        wp = WorkPart(container_work_id=work1.id, part_work_id=work2.id, sequence=1)
        db.session.add(wp)

        # Contributor
        contributor = Contributor(name="Herbert von Karajan", type="person")
        db.session.add(contributor)
        db.session.flush()

        # WorkContribution
        wc = WorkContribution(work_id=work1.id, contributor_id=contributor.id, role="composer")
        db.session.add(wc)

        # Expression
        expr = Expression(work_id=work1.id, content_type="music", language="de")
        db.session.add(expr)
        db.session.flush()

        # ExpressionContribution
        ec = ExpressionContribution(expression_id=expr.id, contributor_id=contributor.id, role="conductor")
        db.session.add(ec)

        # Manifestation with publication_date
        mani = Manifestation(
            expression_id=expr.id,
            isbn13="9783161484100",
            publisher="Deutsche Grammophon",
            meta={"publication_date": "1962-01-01"},
        )
        db.session.add(mani)
        db.session.flush()

        # ImageScan
        scan = ImageScan(manifestation_id=mani.id, file_path="covers/test_cover.jpg", scan_type="front")
        db.session.add(scan)

        # Item
        item = Item(owner_id=user.id, manifestation_id=mani.id, status="owned", is_hidden=False)
        db.session.add(item)
        db.session.flush()

        # UserCollection
        coll = UserCollection(owner_id=user.id, name="Classical Favorites")
        db.session.add(coll)
        db.session.flush()

        # UserCollectionItem
        coll_item = UserCollectionItem(collection_id=coll.id, item_id=item.id)
        db.session.add(coll_item)

        db.session.commit()

        token = generate_internal_jwt(user)
        return {"Authorization": f"Bearer {token}", "user_id": str(user.id)}


class TestEnrichedSerialization:
    """Tests for the enriched serialize_collection_to_rdf with contributors, parts, etc."""

    def test_export_includes_contributors(self, app, client, enriched_user):
        """WorkContribution and ExpressionContribution appear as schema:contributor triples."""
        resp = client.get("/api/v1/items/export?format=turtle", headers=enriched_user)
        assert resp.status_code == 200
        g = Graph()
        g.parse(data=resp.data.decode(), format="turtle")
        # Check contributor triples exist
        contributor_triples = list(g.triples((None, SCHEMA.contributor, None)))
        assert len(contributor_triples) >= 1
        # Check contributor has a name
        for _, _, c_uri in contributor_triples:
            names = list(g.objects(c_uri, SCHEMA.name))
            assert len(names) >= 1
            assert "Karajan" in str(names[0])

    def test_export_includes_work_parts(self, app, client, enriched_user):
        """WorkPart relationships emit schema:isPartOf and schema:hasPart triples."""
        resp = client.get("/api/v1/items/export?format=turtle", headers=enriched_user)
        assert resp.status_code == 200
        g = Graph()
        g.parse(data=resp.data.decode(), format="turtle")
        has_part_triples = list(g.triples((None, SCHEMA.hasPart, None)))
        is_part_of_triples = list(g.triples((None, SCHEMA.isPartOf, None)))
        assert len(has_part_triples) >= 1
        assert len(is_part_of_triples) >= 1

    def test_export_includes_image_scans(self, app, client, enriched_user):
        """ImageScan records emit schema:image triples."""
        resp = client.get("/api/v1/items/export?format=turtle", headers=enriched_user)
        assert resp.status_code == 200
        g = Graph()
        g.parse(data=resp.data.decode(), format="turtle")
        image_triples = list(g.triples((None, SCHEMA.image, None)))
        assert len(image_triples) >= 1
        # The image URI should contain the file path
        assert "covers/test_cover.jpg" in str(image_triples[0][2])

    def test_export_includes_user_collections(self, app, client, enriched_user):
        """UserCollection membership emits schema:Collection with schema:hasPart."""
        resp = client.get("/api/v1/items/export?format=turtle", headers=enriched_user)
        assert resp.status_code == 200
        g = Graph()
        g.parse(data=resp.data.decode(), format="turtle")
        # Find Collection type
        collections = list(g.subjects(RDF.type, SCHEMA.Collection))
        assert len(collections) >= 1
        # Check collection has name
        coll_uri = collections[0]
        names = list(g.objects(coll_uri, SCHEMA.name))
        assert any("Classical Favorites" in str(n) for n in names)

    def test_export_includes_date_published(self, app, client, enriched_user):
        """Manifestation publication_date emits schema:datePublished."""
        resp = client.get("/api/v1/items/export?format=turtle", headers=enriched_user)
        assert resp.status_code == 200
        g = Graph()
        g.parse(data=resp.data.decode(), format="turtle")
        date_triples = list(g.triples((None, SCHEMA.datePublished, None)))
        assert len(date_triples) >= 1
        assert "1962" in str(date_triples[0][2])


class TestSHACLImportValidation:
    """Tests for SHACL validation in the admin import endpoint."""

    @pytest.fixture
    def admin_headers(self, app):
        """Create admin user headers."""
        from app.api.auth import generate_internal_jwt
        from app.db.models import Role, User, db

        with app.app_context():
            admin_role = Role.query.filter_by(name="admin").first()
            if not admin_role:
                admin_role = Role(name="admin")
                db.session.add(admin_role)

            user = User(email="shacl_admin@iqoqo.local", display_name="SHACL Admin")
            user.roles.append(admin_role)
            db.session.add(user)
            db.session.commit()

            token = generate_internal_jwt(user)
            return {"Authorization": f"Bearer {token}"}

    def test_import_valid_turtle_passes_shacl(self, app, client, admin_headers):
        """Valid RDF import passes SHACL validation."""
        valid_turtle = """
        @prefix frbr: <http://iflastandards.info/ns/frbr/frbrer/> .
        @prefix schema: <https://schema.org/> .

        <http://example.org/m/1> a frbr:Manifestation, schema:CreativeWork ;
            frbr:embodimentOf <http://example.org/e/1> ;
            schema:name "Valid Book" ;
            schema:isbn "9781234567890" .

        <http://example.org/e/1> a frbr:Expression ;
            frbr:expressionOf <http://example.org/w/1> .

        <http://example.org/w/1> a frbr:Work .
        """
        resp = client.post(
            "/api/admin/import?format=turtle",
            data=valid_turtle,
            content_type="text/turtle",
            headers=admin_headers,
        )
        # Should not get 422 (SHACL error) — may get other errors since we're not
        # actually importing RDF into the JSON importer, but SHACL should pass
        assert resp.status_code != 422

    def test_import_invalid_turtle_fails_shacl(self, app, client, admin_headers):
        """Invalid RDF (missing required name) fails SHACL validation with 422."""
        invalid_turtle = """
        @prefix frbr: <http://iflastandards.info/ns/frbr/frbrer/> .
        @prefix schema: <https://schema.org/> .

        <http://example.org/m/1> a frbr:Manifestation, schema:CreativeWork ;
            frbr:embodimentOf <http://example.org/e/1> ;
            schema:isbn "bad" .
        """
        resp = client.post(
            "/api/admin/import?format=turtle",
            data=invalid_turtle,
            content_type="text/turtle",
            headers=admin_headers,
        )
        assert resp.status_code == 422
        data = json.loads(resp.data)
        assert "SHACL" in data["error"]


class TestSitemap:
    """Tests for the public sitemap.xml endpoint."""

    @pytest.fixture
    def public_user(self, app):
        """Create a public user for sitemap testing."""
        from app.db.models import User, db

        with app.app_context():
            user = User(
                email="sitemap@iqoqo.local",
                display_name="Sitemap User",
                public_username="sitemapuser",
                visibility="public",
            )
            db.session.add(user)
            db.session.commit()
            return user.public_username

    def test_sitemap_returns_xml(self, app, client, public_user):
        """Sitemap endpoint returns valid XML."""
        resp = client.get("/api/public/sitemap.xml")
        assert resp.status_code == 200
        assert resp.content_type.startswith("application/xml")
        assert b"<?xml" in resp.data
        assert b"<urlset" in resp.data

    def test_sitemap_includes_public_users(self, app, client, public_user):
        """Sitemap lists URLs for public user profiles."""
        resp = client.get("/api/public/sitemap.xml")
        assert resp.status_code == 200
        assert b"sitemapuser" in resp.data

    def test_sitemap_includes_shared_collections(self, app, client):
        """Sitemap lists URLs for shared collections."""
        from app.db.models import SharedCollection, User, db

        with app.app_context():
            user = User(email="share_sitemap@iqoqo.local", display_name="Share User")
            db.session.add(user)
            db.session.flush()
            share = SharedCollection(user_id=user.id, name="My Share", share_token="test-share-token-xyz")
            db.session.add(share)
            db.session.commit()

        resp = client.get("/api/public/sitemap.xml")
        assert resp.status_code == 200
        assert b"test-share-token-xyz" in resp.data


class TestETLScript:
    """Tests for the ETL strict script ISBN normalization."""

    def test_normalize_isbn_valid(self):
        """Valid ISBN-13 with hyphens is normalized."""
        from scripts.etl_frbr_strict import normalize_isbn

        assert normalize_isbn("978-3-16-148410-0") == "9783161484100"

    def test_normalize_isbn_invalid_check_digit(self):
        """Invalid check digit returns None."""
        from scripts.etl_frbr_strict import normalize_isbn

        assert normalize_isbn("9781234567899") is None

    def test_normalize_isbn_wrong_length(self):
        """Non-13-digit string returns None."""
        from scripts.etl_frbr_strict import normalize_isbn

        assert normalize_isbn("12345") is None

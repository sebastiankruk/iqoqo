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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
"""Automated tests for data sovereignty collection export and SHACL semantic conformity.

Verifies:
1. Canonical JSON-LD @context bindings (FRBR, Schema.org, Dublin Core, iqoqo).
2. Endpoint security and HTTP 401 unauthenticated rejection.
3. Multi-format negotiation (json-ld, turtle, json) and rejection of unsupported formats.
4. Chunked streaming transfer and Content-Disposition headers.
5. Strict FRBR hierarchy (Item -> Manifestation -> Expression -> Work) and isbn13 placement.
6. User scoping (only authenticated user's items exported).
7. SHACL validation of JSON-LD and Turtle outputs against docs/ontology/iqoqo-shapes.ttl.
"""

import json
import uuid

import pytest
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF

from app.api.auth import generate_internal_jwt
from app.core.export_service import CANONICAL_JSONLD_CONTEXT, ExportService
from app.core.shacl_service import validate_graph
from app.db.auth import User
from app.db.core import Expression, Item, Manifestation, Work, db

FRBR_IFLA = Namespace("http://iflastandards.info/ns/frbr/frbrer/")
SCHEMA = Namespace("https://schema.org/")


@pytest.fixture
def export_user(app):
    """Create a test user for export tests."""
    with app.app_context():
        user = User(email=f"export_{uuid.uuid4().hex[:8]}@iqoqo.local", display_name="Export User")
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        _ = user.id
        return user


@pytest.fixture
def other_user(app):
    """Create another user to verify export isolation."""
    with app.app_context():
        user = User(email=f"other_{uuid.uuid4().hex[:8]}@iqoqo.local", display_name="Other User")
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        _ = user.id
        return user


@pytest.fixture
def auth_headers(export_user):
    """Generate JWT auth headers for the primary test user."""
    token = generate_internal_jwt(export_user)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def populated_library(app, export_user, other_user):
    """Populate a complete FRBR hierarchy for export_user and a decoy for other_user."""
    with app.app_context():
        # 1. Primary test user library
        work1 = Work(
            title="Dune",
            sort_title="Dune",
            meta={"authors": ["Frank Herbert"]},
        )
        db.session.add(work1)
        db.session.flush()

        expr1 = Expression(
            work_id=work1.id,
            content_type="text",
            language="en",
            kind=None,
        )
        db.session.add(expr1)
        db.session.flush()

        manif1 = Manifestation(
            expression_id=expr1.id,
            isbn13="9780441172719",
            publisher="Chilton Books",
            format="Hardcover",
            meta={"title": "Dune"},
        )
        db.session.add(manif1)
        db.session.flush()

        item1 = Item(
            manifestation_id=manif1.id,
            owner_id=export_user.id,
            condition="fine",
            status="available",
        )
        db.session.add(item1)

        # 2. Second item for primary test user
        work2 = Work(
            title="The Left Hand of Darkness",
            sort_title="Left Hand of Darkness",
            meta={"authors": ["Ursula K. Le Guin"]},
        )
        db.session.add(work2)
        db.session.flush()

        expr2 = Expression(
            work_id=work2.id,
            content_type="text",
            language="en",
            kind=None,
        )
        db.session.add(expr2)
        db.session.flush()

        manif2 = Manifestation(
            expression_id=expr2.id,
            isbn13="9780441478125",
            publisher="Ace Books",
            format="Paperback",
            meta={"title": "The Left Hand of Darkness"},
        )
        db.session.add(manif2)
        db.session.flush()

        item2 = Item(
            manifestation_id=manif2.id,
            owner_id=export_user.id,
            condition="good",
            status="available",
        )
        db.session.add(item2)

        # 3. Decoy item belonging to other_user
        decoy_work = Work(title="Decoy Secret Diary", meta={"authors": ["Secret Author"]})
        db.session.add(decoy_work)
        db.session.flush()
        decoy_expr = Expression(work_id=decoy_work.id, content_type="text", language="en")
        db.session.add(decoy_expr)
        db.session.flush()
        decoy_manif = Manifestation(expression_id=decoy_expr.id, isbn13="9781234567890")
        db.session.add(decoy_manif)
        db.session.flush()
        decoy_item = Item(manifestation_id=decoy_manif.id, owner_id=other_user.id)
        db.session.add(decoy_item)

        db.session.commit()

        return {
            "work1_id": work1.id,
            "expr1_id": expr1.id,
            "manif1_id": manif1.id,
            "item1_id": item1.id,
            "item2_id": item2.id,
            "decoy_item_id": decoy_item.id,
        }


class TestCanonicalJsonLdContext:
    """Tests verifying canonical JSON-LD @context bindings."""

    def test_canonical_context_namespaces(self):
        """Verify FRBR, Schema.org, Dublin Core, and iqoqo namespace definitions."""
        assert CANONICAL_JSONLD_CONTEXT["frbr"] == "http://purl.org/vocab/frbr/core#"
        assert CANONICAL_JSONLD_CONTEXT["schema"] == "https://schema.org/"
        assert CANONICAL_JSONLD_CONTEXT["dc"] == "http://purl.org/dc/terms/"
        assert CANONICAL_JSONLD_CONTEXT["iqoqo"] == "https://iqoqo.org/ontology#"

    def test_canonical_context_terms(self):
        """Verify canonical FRBR entity types and property terms."""
        assert CANONICAL_JSONLD_CONTEXT["Work"] == "frbr:Work"
        assert CANONICAL_JSONLD_CONTEXT["Expression"] == "frbr:Expression"
        assert CANONICAL_JSONLD_CONTEXT["Manifestation"] == "frbr:Manifestation"
        assert CANONICAL_JSONLD_CONTEXT["Item"] == "frbr:Item"
        assert CANONICAL_JSONLD_CONTEXT["title"] == "dc:title"
        assert CANONICAL_JSONLD_CONTEXT["creator"] == "frbrer:creator"
        assert CANONICAL_JSONLD_CONTEXT["isbn"] == "schema:isbn"
        assert CANONICAL_JSONLD_CONTEXT["publisher"] == "schema:publisher"
        assert CANONICAL_JSONLD_CONTEXT["format"] == "schema:bookFormat"


class TestExportEndpointValidation:
    """Tests for authentication and format validation on GET /api/v1/items/export."""

    def test_unauthenticated_request_rejected(self, client):
        """Unauthenticated requests must be rejected with HTTP 401 Unauthorized."""
        response = client.get("/api/v1/items/export")
        assert response.status_code == 401

    def test_unsupported_format_rejected(self, client, auth_headers):
        """Unsupported format must return HTTP 400 Bad Request."""
        response = client.get("/api/v1/items/export?format=xml", headers=auth_headers)
        assert response.status_code == 400
        data = response.get_json()
        assert "Invalid export format" in data["error"] or "Unsupported" in data["error"]

    def test_default_format_is_jsonld(self, client, auth_headers, populated_library):
        """When format parameter is omitted, default to json-ld with correct headers."""
        response = client.get("/api/v1/items/export", headers=auth_headers)
        assert response.status_code == 200
        assert "application/ld+json" in response.content_type
        assert "attachment" in response.headers.get("Content-Disposition", "")
        assert response.headers.get("Content-Disposition", "").endswith('.jsonld"')
        assert response.headers.get("X-Accel-Buffering") == "no"

    def test_turtle_format_headers(self, client, auth_headers, populated_library):
        """Requesting format=turtle produces text/turtle with .ttl filename."""
        response = client.get("/api/v1/items/export?format=turtle", headers=auth_headers)
        assert response.status_code == 200
        assert "text/turtle" in response.content_type
        assert "attachment" in response.headers.get("Content-Disposition", "")
        assert response.headers.get("Content-Disposition", "").endswith('.ttl"')

    def test_json_format_headers(self, client, auth_headers, populated_library):
        """Requesting format=json produces application/json with .json filename."""
        response = client.get("/api/v1/items/export?format=json", headers=auth_headers)
        assert response.status_code == 200
        assert "application/json" in response.content_type
        assert "attachment" in response.headers.get("Content-Disposition", "")
        assert response.headers.get("Content-Disposition", "").endswith('.json"')


class TestFrbrHierarchyCompleteness:
    """Tests verifying complete FRBR hierarchy traversal and isbn13 isolation."""

    def test_hierarchical_json_structure_and_isbn_placement(self, client, auth_headers, populated_library):
        """Hierarchical JSON export must preserve full FRBR hierarchy and keep isbn13 on Manifestation only."""
        response = client.get("/api/v1/items/export?format=json", headers=auth_headers)
        assert response.status_code == 200
        items_data = json.loads(response.get_data(as_text=True))

        # Must export exactly 2 items for this user (decoy item excluded)
        assert len(items_data) == 2
        exported_ids = {item["id"] for item in items_data}
        assert populated_library["item1_id"] in exported_ids
        assert populated_library["item2_id"] in exported_ids
        assert populated_library["decoy_item_id"] not in exported_ids

        # Inspect first item hierarchy
        dune_item = next(it for it in items_data if it["id"] == populated_library["item1_id"])
        manif = dune_item["manifestation"]
        assert manif is not None
        assert manif["isbn13"] == "9780441172719"
        assert manif["publisher"] == "Chilton Books"
        assert manif["format"] == "Hardcover"

        expr = manif["expression"]
        assert expr is not None
        assert expr["language"] == "en"
        assert expr["content_type"] == "text"

        work = expr["work"]
        assert work is not None
        assert work["title"] == "Dune"
        assert work["authors"] == ["Frank Herbert"]

        # Crucial ontological purity: Work MUST NOT have isbn13
        assert "isbn13" not in work
        assert "isbn" not in work


class TestShaclConformityAndSemanticValidation:
    """Tests validating exported Linked Data against docs/ontology/iqoqo-shapes.ttl."""

    def test_jsonld_export_shacl_conformity(self, client, auth_headers, populated_library):
        """Exported JSON-LD must parse into rdflib Graph and pass SHACL shape validation."""
        response = client.get("/api/v1/items/export?format=json-ld", headers=auth_headers)
        assert response.status_code == 200
        jsonld_str = response.get_data(as_text=True)

        # Parse with rdflib JSON-LD parser
        graph = Graph()
        graph.parse(data=jsonld_str, format="json-ld")
        assert len(graph) > 0

        # Validate against canonical SHACL shapes
        conforms, _, results_text = validate_graph(graph)
        assert conforms, f"JSON-LD export violated SHACL shapes: {results_text}"

        # Verify Dune Work creator and Manifestation ISBN in graph
        work_query = graph.query("""
            SELECT ?title ?creatorName ?isbn
            WHERE {
                ?w a <http://purl.org/vocab/frbr/core#Work> ;
                   <https://schema.org/name> ?title ;
                   <http://iflastandards.info/ns/frbr/frbrer/creator> ?creator .
                ?creator <https://schema.org/name> ?creatorName .
                ?e a <http://purl.org/vocab/frbr/core#Expression> ;
                   <http://iflastandards.info/ns/frbr/frbrer/expressionOf> ?w .
                ?m a <http://purl.org/vocab/frbr/core#Manifestation> ;
                   <http://iflastandards.info/ns/frbr/frbrer/embodimentOf> ?e ;
                   <https://schema.org/isbn> ?isbn .
                ?i a <http://purl.org/vocab/frbr/core#Item> ;
                   <http://iflastandards.info/ns/frbr/frbrer/exemplarOf> ?m .
                FILTER(?title = "Dune")
            }
        """)
        rows = list(work_query)
        assert len(rows) == 1
        row = rows[0]
        assert str(row[0]) == "Dune"
        assert str(row[1]) == "Frank Herbert"
        assert str(row[2]) == "9780441172719"

    def test_turtle_export_shacl_conformity(self, client, auth_headers, populated_library):
        """Exported RDF Turtle must parse into rdflib Graph and pass SHACL shape validation."""
        response = client.get("/api/v1/items/export?format=turtle", headers=auth_headers)
        assert response.status_code == 200
        turtle_str = response.get_data(as_text=True)

        # Parse with rdflib Turtle parser
        graph = Graph()
        graph.parse(data=turtle_str, format="turtle")
        assert len(graph) > 0

        # Validate against canonical SHACL shapes
        conforms, _, results_text = validate_graph(graph)
        assert conforms, f"Turtle export violated SHACL shapes: {results_text}"


class TestBatchedStreamingIteration:
    """Tests verifying batched cursor querying and memory-safe streaming."""

    def test_stream_batch_iteration(self, app, export_user, populated_library):
        """Verify stream_user_collection yields batches properly with custom batch_size."""
        with app.app_context():
            generator = ExportService.stream_user_collection(
                user_id=export_user.id,
                export_format="json",
                batch_size=1,
            )
            chunks = list(generator)
            assert len(chunks) >= 3  # [ + at least 2 item chunks + ]
            full_payload = "".join(chunks)
            parsed = json.loads(full_payload)
            assert len(parsed) == 2

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
"""Tests for SPARQL query endpoint and service layer."""

import pytest
from rdflib import Graph

from app.core.sparql_service import (
    SPARQLQueryTooLarge,
    SPARQLWriteRejected,
    build_graph,
    execute_sparql,
    format_select_results,
    validate_query,
)
from app.db.models import Expression, Item, Manifestation, User, Work, db


@pytest.fixture
def sparql_user(app):
    """Create a user with items for SPARQL testing."""
    from app.api.auth import generate_internal_jwt

    with app.app_context():
        from app.db.models import Permission, Role

        user_role = Role(name="sparql_user_role")
        write_perm = Permission.query.filter_by(name="write:item").first()
        if not write_perm:
            write_perm = Permission(name="write:item")
            db.session.add(write_perm)
        user_role.permissions.append(write_perm)
        db.session.add(user_role)

        user = User(email="sparql@iqoqo.local", display_name="SPARQL User")
        user.roles.append(user_role)
        db.session.add(user)
        db.session.flush()

        # Create FRBR chain
        work = Work(title="Semantic Web Primer", meta={"authors": ["Tim Berners-Lee"]})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="book", language="en")
        db.session.add(expr)
        db.session.flush()

        mani = Manifestation(expression_id=expr.id, isbn13="9781234567890", publisher="W3C Press")
        db.session.add(mani)
        db.session.flush()

        item = Item(owner_id=user.id, manifestation_id=mani.id, status="read", is_hidden=False)
        db.session.add(item)

        # Second item
        work2 = Work(title="SPARQL By Example", meta={"authors": ["Bob DuCharme"]})
        db.session.add(work2)
        db.session.flush()

        expr2 = Expression(work_id=work2.id, content_type="book", language="en")
        db.session.add(expr2)
        db.session.flush()

        mani2 = Manifestation(expression_id=expr2.id, isbn13="9780987654321", publisher="Apress")
        db.session.add(mani2)
        db.session.flush()

        item2 = Item(owner_id=user.id, manifestation_id=mani2.id, status="to_read", is_hidden=False)
        db.session.add(item2)

        db.session.commit()

        token = generate_internal_jwt(user)
        return {"Authorization": f"Bearer {token}"}


class TestSPARQLService:
    """Unit tests for the SPARQL service layer."""

    def test_validate_query_accepts_select(self):
        validate_query("SELECT ?s ?p ?o WHERE { ?s ?p ?o }")

    def test_validate_query_accepts_construct(self):
        validate_query("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }")

    def test_validate_query_rejects_insert(self):
        with pytest.raises(SPARQLWriteRejected):
            validate_query("INSERT DATA { <s> <p> <o> }")

    def test_validate_query_rejects_delete(self):
        with pytest.raises(SPARQLWriteRejected):
            validate_query("DELETE WHERE { ?s ?p ?o }")

    def test_validate_query_rejects_drop(self):
        with pytest.raises(SPARQLWriteRejected):
            validate_query("DROP GRAPH <http://example.org/>")

    def test_validate_query_rejects_load(self):
        with pytest.raises(SPARQLWriteRejected):
            validate_query("LOAD <http://evil.example.org/data.ttl>")

    def test_validate_query_rejects_oversized(self):
        big_query = "SELECT ?s WHERE { ?s ?p ?o } " + " " * 11000
        with pytest.raises(SPARQLQueryTooLarge):
            validate_query(big_query)

    def test_build_graph_from_dicts(self):
        items = [
            {
                "id": "item-1",
                "manifestation_id": "m-1",
                "expression_id": "e-1",
                "work_id": "w-1",
                "title": "Test Book",
                "isbn": "9780000000001",
                "authors": ["Author One"],
                "tags": ["fiction"],
                "status": "read",
            }
        ]
        graph = build_graph(items, "http://localhost:5000")
        assert len(graph) > 0

    def test_execute_select_on_graph(self):
        items = [
            {
                "id": "item-1",
                "manifestation_id": "m-1",
                "expression_id": "e-1",
                "work_id": "w-1",
                "title": "Test Book",
                "isbn": "9780000000001",
                "authors": ["Author One"],
                "tags": [],
                "status": "read",
            }
        ]
        graph = build_graph(items, "http://localhost:5000")
        result = execute_sparql(graph, "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 5")
        formatted = format_select_results(result)
        assert "head" in formatted
        assert "results" in formatted
        assert len(formatted["results"]["bindings"]) > 0

    def test_execute_construct_on_graph(self):
        items = [
            {
                "id": "item-1",
                "manifestation_id": "m-1",
                "expression_id": "e-1",
                "work_id": "w-1",
                "title": "Test Book",
                "authors": [],
                "tags": [],
                "status": None,
            }
        ]
        graph = build_graph(items, "http://localhost:5000")
        result = execute_sparql(
            graph, "CONSTRUCT { ?s <https://schema.org/name> ?name } WHERE { ?s <https://schema.org/name> ?name }"
        )
        assert result.graph is not None
        assert len(result.graph) > 0


class TestSPARQLEndpoint:
    """Integration tests for the SPARQL API endpoint."""

    def test_post_select_query(self, client, sparql_user):
        response = client.post(
            "/api/sparql",
            json={"query": "SELECT ?title WHERE { ?s <https://schema.org/name> ?title }"},
            headers=sparql_user,
        )
        assert response.status_code == 200
        assert "application/sparql-results+json" in response.content_type
        data = response.get_json()
        assert "head" in data
        assert "title" in data["head"]["vars"]
        titles = [b["title"]["value"] for b in data["results"]["bindings"]]
        assert "Semantic Web Primer" in titles

    def test_post_construct_query_turtle(self, client, sparql_user):
        response = client.post(
            "/api/sparql",
            json={"query": "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o } LIMIT 10"},
            headers={**sparql_user, "Accept": "text/turtle"},
        )
        assert response.status_code == 200
        assert "text/turtle" in response.content_type
        # Verify it's parseable turtle
        g = Graph()
        g.parse(data=response.data, format="turtle")
        assert len(g) > 0

    def test_post_construct_query_jsonld(self, client, sparql_user):
        response = client.post(
            "/api/sparql",
            json={"query": "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o } LIMIT 10"},
            headers={**sparql_user, "Accept": "application/ld+json"},
        )
        assert response.status_code == 200
        assert "application/ld+json" in response.content_type

    def test_get_query(self, client, sparql_user):
        response = client.get(
            "/api/sparql?query=SELECT+%3Fs+WHERE+%7B+%3Fs+a+%3Chttp%3A%2F%2Fiflastandards.info%2Fns%2Ffrbr%2Ffrbrer%2FManifestation%3E+%7D",
            headers=sparql_user,
        )
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["results"]["bindings"]) == 2

    def test_rejects_write_operations(self, client, sparql_user):
        response = client.post(
            "/api/sparql",
            json={"query": "INSERT DATA { <http://x.org/s> <http://x.org/p> <http://x.org/o> }"},
            headers=sparql_user,
        )
        assert response.status_code == 400
        assert "not permitted" in response.get_json()["error"]

    def test_rejects_delete_operations(self, client, sparql_user):
        response = client.post(
            "/api/sparql",
            json={"query": "DELETE WHERE { ?s ?p ?o }"},
            headers=sparql_user,
        )
        assert response.status_code == 400

    def test_rejects_oversized_query(self, client, sparql_user):
        big_query = "SELECT ?s WHERE { ?s ?p ?o } " + " " * 11000
        response = client.post(
            "/api/sparql",
            json={"query": big_query},
            headers=sparql_user,
        )
        assert response.status_code == 400
        assert "maximum size" in response.get_json()["error"]

    def test_unauthenticated_returns_401(self, client):
        response = client.post(
            "/api/sparql",
            json={"query": "SELECT ?s WHERE { ?s ?p ?o }"},
        )
        assert response.status_code == 401

    def test_empty_query_returns_400(self, client, sparql_user):
        response = client.post(
            "/api/sparql",
            json={"query": ""},
            headers=sparql_user,
        )
        assert response.status_code == 400

    def test_missing_query_field_returns_400(self, client, sparql_user):
        response = client.post(
            "/api/sparql",
            json={"not_query": "SELECT ?s WHERE { ?s ?p ?o }"},
            headers=sparql_user,
        )
        assert response.status_code == 400

    def test_invalid_syntax_returns_400(self, client, sparql_user):
        response = client.post(
            "/api/sparql",
            json={"query": "SELCT ?s WHERE { ?s ?p ?o }"},
            headers=sparql_user,
        )
        assert response.status_code == 400

    def test_sparql_protocol_form_encoded(self, client, sparql_user):
        response = client.post(
            "/api/sparql",
            data={"query": "SELECT ?title WHERE { ?s <https://schema.org/name> ?title }"},
            headers=sparql_user,
            content_type="application/x-www-form-urlencoded",
        )
        assert response.status_code == 200

    def test_sparql_protocol_direct_body(self, client, sparql_user):
        response = client.post(
            "/api/sparql",
            data="SELECT ?title WHERE { ?s <https://schema.org/name> ?title }",
            headers={**sparql_user, "Content-Type": "application/sparql-query"},
        )
        assert response.status_code == 200

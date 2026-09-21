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
        for perm_name in ("write:item", "read:metadata"):
            perm = Permission.query.filter_by(name=perm_name).first()
            if not perm:
                perm = Permission(name=perm_name)
                db.session.add(perm)
            user_role.permissions.append(perm)
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

        item2 = Item(owner_id=user.id, manifestation_id=mani2.id, status="want_to_read", is_hidden=False)
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
        result = execute_sparql(graph, "CONSTRUCT { ?s <https://schema.org/name> ?name } WHERE { ?s <https://schema.org/name> ?name }")
        assert result.graph is not None
        assert len(result.graph) > 0

    def test_format_select_results_respects_max_rows(self):
        items = [
            {
                "id": "item-1",
                "manifestation_id": "m-1",
                "expression_id": "e-1",
                "work_id": "w-1",
                "title": "Test Book",
                "authors": ["Author 1", "Author 2"],
                "tags": ["tag1", "tag2"],
                "status": None,
            }
        ]
        graph = build_graph(items, "http://localhost:5000")
        result = execute_sparql(graph, "SELECT ?s ?p ?o WHERE { ?s ?p ?o }")
        formatted = format_select_results(result, max_rows=2)
        assert len(formatted["results"]["bindings"]) == 2

    def test_validate_query_rejects_with_value_error(self):
        with pytest.raises(ValueError):
            validate_query("INSERT DATA { <s> <p> <o> }")
        with pytest.raises(ValueError):
            validate_query("SELECT ?s WHERE { ?s ?p ?o } " + " " * 11000)

    def test_execute_ask_query(self):
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
        result = execute_sparql(graph, "ASK { ?s ?p ?o }")
        formatted = format_select_results(result)
        assert formatted.get("boolean") is True

    def test_execute_timeout_handling(self):
        """Test that timeout is enforced with a very short deadline."""
        from app.core.sparql_service import SPARQLTimeout

        # Create a small graph
        items = [
            {
                "id": "item-1",
                "manifestation_id": "m-1",
                "expression_id": "e-1",
                "work_id": "w-1",
                "title": "Test Book",
                "authors": ["Author One"],
                "tags": ["fiction"],
                "status": "read",
            }
        ]
        graph = build_graph(items, "http://localhost:5000")

        # Use an extremely short timeout that will be exceeded even for simple queries
        # due to process startup overhead
        with pytest.raises(SPARQLTimeout):
            execute_sparql(graph, "SELECT ?s WHERE { ?s ?p ?o }", timeout=0.01)

    def test_build_graph_excludes_other_users_private_items(self):
        items = [
            {
                "id": "pub-item",
                "manifestation_id": "m-1",
                "title": "Public Item",
                "is_hidden": False,
                "owner_id": "user-other",
            },
            {
                "id": "priv-item-other",
                "manifestation_id": "m-2",
                "title": "Private Item Other",
                "is_hidden": True,
                "owner_id": "user-other",
            },
            {
                "id": "priv-item-mine",
                "manifestation_id": "m-3",
                "title": "Private Item Mine",
                "is_hidden": True,
                "owner_id": "user-me",
            },
        ]
        graph = build_graph(items, "http://localhost:5000", user_id="user-me")
        # Check that pub-item is in graph
        res_pub = execute_sparql(graph, "ASK { <http://localhost:5000/api/public/items/pub-item> ?p ?o }")
        assert res_pub.askAnswer is True
        # Check that priv-item-mine is in graph
        res_mine = execute_sparql(graph, "ASK { <http://localhost:5000/api/public/items/priv-item-mine> ?p ?o }")
        assert res_mine.askAnswer is True
        # Check that priv-item-other is EXCLUDED
        res_other = execute_sparql(graph, "ASK { <http://localhost:5000/api/public/items/priv-item-other> ?p ?o }")
        assert res_other.askAnswer is False


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
        assert response.status_code in (400, 413)
        assert "maximum size" in response.get_json()["error"]

    def test_unauthenticated_returns_401(self, client):
        response = client.post(
            "/api/sparql",
            json={"query": "SELECT ?s WHERE { ?s ?p ?o }"},
        )
        assert response.status_code == 401

    def test_forbidden_without_read_metadata(self, client, app):
        from app.api.auth import generate_internal_jwt

        with app.app_context():
            user = User(email="norole@iqoqo.local", display_name="No Role User")
            db.session.add(user)
            db.session.flush()
            token = generate_internal_jwt(user)

        response = client.post(
            "/api/sparql",
            json={"query": "SELECT ?s WHERE { ?s ?p ?o }"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
        assert response.get_json()["missing_permission"] == "read:metadata"

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

    def test_post_select_query_xml(self, client, sparql_user):
        response = client.post(
            "/api/sparql",
            json={"query": "SELECT ?title WHERE { ?s <https://schema.org/name> ?title }"},
            headers={**sparql_user, "Accept": "application/sparql-results+xml"},
        )
        assert response.status_code == 200
        assert "application/sparql-results+xml" in response.content_type
        assert b"<?xml" in response.data or b"<sparql" in response.data

    def test_post_select_query_csv(self, client, sparql_user):
        response = client.post(
            "/api/sparql",
            json={"query": "SELECT ?title WHERE { ?s <https://schema.org/name> ?title }"},
            headers={**sparql_user, "Accept": "text/csv"},
        )
        assert response.status_code == 200
        assert "text/csv" in response.content_type
        assert b"title" in response.data

    def test_post_construct_rdf_xml(self, client, sparql_user):
        response = client.post(
            "/api/sparql",
            json={"query": "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o } LIMIT 10"},
            headers={**sparql_user, "Accept": "application/rdf+xml"},
        )
        assert response.status_code == 200
        assert "application/rdf+xml" in response.content_type
        assert b"<rdf:RDF" in response.data or b"<?xml" in response.data


class TestSPARQLURIEdgeCases:
    """Regression tests for URI construction with reserved characters."""

    def test_cover_url_with_spaces_does_not_crash(self):
        """Cover filenames containing spaces must not crash graph serialization."""
        items = [
            {
                "id": "item-1",
                "manifestation_id": "m-1",
                "expression_id": "e-1",
                "work_id": "w-1",
                "title": "Test Book",
                "cover_url": "/covers/My Book Cover (2024).jpg",
                "authors": [],
                "tags": [],
                "status": "read",
            }
        ]
        graph = build_graph(items, "http://localhost:5000")
        # Must serialize without exception
        nt = graph.serialize(format="nt")
        assert nt is not None
        # Spaces must be percent-encoded
        assert "%20" in nt or "My%20Book" in nt

    def test_cover_url_with_unicode(self):
        """Cover filenames containing Unicode characters must be safely encoded."""
        items = [
            {
                "id": "item-1",
                "manifestation_id": "m-1",
                "title": "Książka",
                "cover_url": "/covers/książka_okładka.png",
                "authors": [],
                "tags": [],
                "status": "read",
            }
        ]
        graph = build_graph(items, "http://localhost:5000")
        nt = graph.serialize(format="nt")
        assert nt is not None

    def test_cover_url_absolute_with_spaces(self):
        """Absolute cover URLs with spaces must be percent-encoded."""
        items = [
            {
                "id": "item-1",
                "manifestation_id": "m-1",
                "title": "Test",
                "cover_url": "https://example.com/covers/my cover.jpg",
                "authors": [],
                "tags": [],
                "status": None,
            }
        ]
        graph = build_graph(items, "http://localhost:5000")
        nt = graph.serialize(format="nt")
        assert nt is not None
        assert "%20" in nt

    def test_malformed_cover_url_skipped_gracefully(self):
        """Completely malformed cover URLs should be skipped, not crash."""
        from app.core.frbr_service import _safe_iri

        # _safe_iri should return None for empty/None
        assert _safe_iri("") is None
        assert _safe_iri(None) is None  # type: ignore[arg-type]

    def test_example_queries_do_not_return_500(self, client, sparql_user):
        """SPARQL Explorer example queries must return 200, not 500."""
        example_queries = [
            "SELECT ?title WHERE { ?s <https://schema.org/name> ?title } LIMIT 10",
            "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 5",
            "ASK { ?s a <http://iflastandards.info/ns/frbr/frbrer/Work> }",
            "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o } LIMIT 10",
            "DESCRIBE <http://iflastandards.info/ns/frbr/frbrer/Work>",
        ]
        for query in example_queries:
            response = client.post(
                "/api/sparql",
                json={"query": query},
                headers=sparql_user,
            )
            assert response.status_code != 500, f"Query returned 500: {query}"
            assert response.status_code in (200, 400, 413, 504), f"Unexpected status {response.status_code} for: {query}"


class TestSPARQLIPCAndLimits:
    """Tests for IPC reliability and resource limit enforcement."""

    def test_child_crash_returns_structured_error(self):
        """If the child process crashes, the parent returns a structured error."""
        from unittest.mock import patch

        from app.core.sparql_service import _MP_CONTEXT, SPARQLChildProcessError, _execute_query_in_process

        items = [{"id": "1", "manifestation_id": "m1", "title": "T", "authors": [], "tags": [], "status": None}]
        graph = build_graph(items, "http://localhost:5000")

        # Patch the child function to simulate a crash (exit without sending)
        def crashing_child(graph_data, query, conn):
            import os

            os._exit(1)

        with patch("app.core.sparql_service._execute_query_in_process", side_effect=crashing_child):
            with pytest.raises((SPARQLChildProcessError, Exception)):
                execute_sparql(graph, "SELECT ?s WHERE { ?s ?p ?o }", timeout=5.0)

    def test_graph_build_error_returns_structured_response(self, client, sparql_user):
        """Graph build failures must return structured JSON error, not uncaught 500."""
        from unittest.mock import patch

        with patch("app.api.sparql.build_graph", side_effect=Exception("graph build boom")):
            response = client.post(
                "/api/sparql",
                json={"query": "SELECT ?s WHERE { ?s ?p ?o }"},
                headers=sparql_user,
            )
            # Should be a structured error, not an uncaught 500
            assert response.status_code in (413, 500, 502)
            data = response.get_json()
            assert "error" in data

    def test_result_row_limit_enforced(self):
        """SELECT results must be capped at MAX_RESULT_ROWS."""
        from app.core.sparql_service import MAX_RESULT_ROWS

        items = [
            {"id": f"i-{i}", "manifestation_id": f"m-{i}", "title": f"Book {i}", "authors": [], "tags": [], "status": None}
            for i in range(20)
        ]
        graph = build_graph(items, "http://localhost:5000")
        result = execute_sparql(graph, "SELECT ?s WHERE { ?s ?p ?o }")
        formatted = format_select_results(result)
        assert len(formatted["results"]["bindings"]) <= MAX_RESULT_ROWS

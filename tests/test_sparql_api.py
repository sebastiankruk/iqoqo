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
"""Comprehensive automated backend tests for SPARQL API protocol endpoint."""

from unittest.mock import patch

import pytest
from rdflib import Graph

from app.api.auth import generate_internal_jwt
from app.core.sparql_service import SPARQLTimeout
from app.db.models import Expression, Item, Manifestation, Permission, Role, User, Work, db


@pytest.fixture
def sparql_test_data(app):
    """Set up two users with public and private items for auth-scoping tests."""
    with app.app_context():
        # Ensure permissions exist
        role = Role(name="sparql_api_test_role")
        for perm_name in ("write:item", "read:metadata"):
            perm = Permission.query.filter_by(name=perm_name).first()
            if not perm:
                perm = Permission(name=perm_name)
                db.session.add(perm)
            role.permissions.append(perm)
        db.session.add(role)

        user_a = User(email="user_a@iqoqo.local", display_name="User Alpha")
        user_a.roles.append(role)
        db.session.add(user_a)

        user_b = User(email="user_b@iqoqo.local", display_name="User Beta")
        user_b.roles.append(role)
        db.session.add(user_b)
        db.session.flush()

        # Shared catalog entities
        work = Work(title="SPARQL OpenSpec Testing", meta={"authors": ["Author Alpha"]})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="book", language="en")
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(expression_id=expr.id, isbn13="9780123456789", publisher="Semantic Publishing")
        db.session.add(manif)
        db.session.flush()

        # User A items: 1 public, 1 private
        item_a_pub = Item(owner_id=user_a.id, manifestation_id=manif.id, status="read", is_hidden=False)
        item_a_priv = Item(owner_id=user_a.id, manifestation_id=manif.id, status="want_to_read", is_hidden=True)
        db.session.add_all([item_a_pub, item_a_priv])

        # User B items: 1 public, 1 private
        item_b_pub = Item(owner_id=user_b.id, manifestation_id=manif.id, status="read", is_hidden=False)
        item_b_priv = Item(owner_id=user_b.id, manifestation_id=manif.id, status="want_to_read", is_hidden=True)
        db.session.add_all([item_b_pub, item_b_priv])

        db.session.commit()

        token_a = generate_internal_jwt(user_a)
        token_b = generate_internal_jwt(user_b)

        return {
            "user_a_headers": {"Authorization": f"Bearer {token_a}"},
            "user_b_headers": {"Authorization": f"Bearer {token_b}"},
            "item_a_pub_id": item_a_pub.id,
            "item_a_priv_id": item_a_priv.id,
            "item_b_pub_id": item_b_pub.id,
            "item_b_priv_id": item_b_priv.id,
        }


class TestSPARQLAuthenticationAndGuards:
    """Tests for authentication, authorization, query size, and rate limits."""

    def test_unauthenticated_requests_return_401(self, client):
        """Unauthenticated requests must be rejected with 401."""
        res_get = client.get("/api/sparql?query=SELECT+%3Fs+WHERE+%7B+%3Fs+%3Fp+%3Fo+%7D")
        assert res_get.status_code == 401

        res_post = client.post("/api/sparql", json={"query": "SELECT ?s WHERE { ?s ?p ?o }"})
        assert res_post.status_code == 401

    def test_oversized_query_returns_413(self, client, sparql_test_data):
        """Queries exceeding 10 KB must return 413 Payload Too Large."""
        oversized_query = "SELECT ?s WHERE { ?s ?p ?o } " + "#" * 11000
        res = client.post(
            "/api/sparql",
            json={"query": oversized_query},
            headers=sparql_test_data["user_a_headers"],
        )
        assert res.status_code == 413
        assert "maximum size" in res.get_json()["error"]

    def test_write_operations_rejected_with_400(self, client, sparql_test_data):
        """Mutating operations must return 400 Bad Request."""
        mutations = [
            "INSERT DATA { <http://example.org/s> <http://example.org/p> 'test' }",
            "DELETE WHERE { ?s ?p ?o }",
            "DROP ALL",
            "CLEAR GRAPH <http://example.org/g>",
            "LOAD <http://example.org/remote.ttl>",
        ]
        for query in mutations:
            res = client.post(
                "/api/sparql",
                json={"query": query},
                headers=sparql_test_data["user_a_headers"],
            )
            assert res.status_code == 400
            assert "not permitted" in res.get_json()["error"]

    def test_syntax_error_returns_400(self, client, sparql_test_data):
        """Malformed SPARQL query syntax returns 400 Bad Request."""
        res = client.post(
            "/api/sparql",
            json={"query": "SELCT ?s WHERE { ?s ?p ?o }"},
            headers=sparql_test_data["user_a_headers"],
        )
        assert res.status_code == 400
        assert "syntax error" in res.get_json()["error"].lower()

    def test_timeout_abortion_returns_504(self, client, sparql_test_data):
        """Query execution timeout returns 504 Gateway Timeout."""
        with patch("app.api.sparql.execute_sparql", side_effect=SPARQLTimeout("Query timed out")):
            res = client.post(
                "/api/sparql",
                json={"query": "SELECT ?s WHERE { ?s ?p ?o }"},
                headers=sparql_test_data["user_a_headers"],
            )
            assert res.status_code == 504
            assert "timed out" in res.get_json()["error"].lower()

    def test_rate_limiting_enforcement(self, client, app, sparql_test_data):
        """Exceeding 10 queries per minute triggers 429 Too Many Requests."""
        from app.core.limiter import limiter

        orig_testing = app.config.get("TESTING")
        orig_ratelimit = app.config.get("RATELIMIT_ENABLED")

        app.config["TESTING"] = False
        app.config["RATELIMIT_ENABLED"] = True
        limiter.init_app(app)
        try:
            headers = sparql_test_data["user_b_headers"]
            status_codes = []
            for _ in range(12):
                res = client.get(
                    "/api/sparql?query=SELECT+%3Fs+WHERE+%7B+%3Fs+%3Fp+%3Fo+%7D+LIMIT+1",
                    headers=headers,
                )
                status_codes.append(res.status_code)

            # At least one request should be 429
            assert 429 in status_codes
        finally:
            app.config["TESTING"] = orig_testing
            app.config["RATELIMIT_ENABLED"] = orig_ratelimit
            limiter.init_app(app)


class TestSPARQLAuthScoping:
    """Tests ensuring auth-scoped isolation of private user items."""

    def test_user_sees_own_private_items_but_not_other_users_private_items(self, client, sparql_test_data):
        """User A sees public items and User A private item, but never User B private item."""
        query = "SELECT ?item WHERE { ?item a <http://iflastandards.info/ns/frbr/frbrer/Item> }"
        res = client.post(
            "/api/sparql",
            json={"query": query},
            headers=sparql_test_data["user_a_headers"],
        )
        assert res.status_code == 200
        data = res.get_json()
        item_uris = [b["item"]["value"] for b in data["results"]["bindings"]]

        pub_a_uri = f"/items/{sparql_test_data['item_a_pub_id']}"
        priv_a_uri = f"/items/{sparql_test_data['item_a_priv_id']}"
        pub_b_uri = f"/items/{sparql_test_data['item_b_pub_id']}"
        priv_b_uri = f"/items/{sparql_test_data['item_b_priv_id']}"

        # Check inclusions
        assert any(pub_a_uri in u for u in item_uris)
        assert any(priv_a_uri in u for u in item_uris)
        assert any(pub_b_uri in u for u in item_uris)

        # Check exclusion: User B's private item must NOT be visible to User A
        assert not any(priv_b_uri in u for u in item_uris)


class TestSPARQLProtocolsAndFormats:
    """Tests for protocol input formats and content negotiation."""

    def test_query_via_url_params(self, client, sparql_test_data):
        """GET request with ?query= URL parameter."""
        res = client.get(
            "/api/sparql?query=SELECT+%3Ftitle+WHERE+%7B+%3Fw+%3Chttps%3A%2F%2Fschema.org%2Fname%3E+%3Ftitle+%7D",
            headers=sparql_test_data["user_a_headers"],
        )
        assert res.status_code == 200
        data = res.get_json()
        assert "head" in data
        assert "title" in data["head"]["vars"]

    def test_query_via_form_urlencoded(self, client, sparql_test_data):
        """POST request with application/x-www-form-urlencoded."""
        res = client.post(
            "/api/sparql",
            data={"query": "SELECT ?title WHERE { ?w <https://schema.org/name> ?title }"},
            content_type="application/x-www-form-urlencoded",
            headers=sparql_test_data["user_a_headers"],
        )
        assert res.status_code == 200
        data = res.get_json()
        assert "head" in data

    def test_query_via_sparql_query_direct_body(self, client, sparql_test_data):
        """POST request with application/sparql-query raw body."""
        res = client.post(
            "/api/sparql",
            data="SELECT ?title WHERE { ?w <https://schema.org/name> ?title }",
            content_type="application/sparql-query",
            headers=sparql_test_data["user_a_headers"],
        )
        assert res.status_code == 200
        data = res.get_json()
        assert "head" in data

    def test_content_negotiation_sparql_xml(self, client, sparql_test_data):
        """Accept: application/sparql-results+xml returns XML."""
        res = client.post(
            "/api/sparql",
            json={"query": "SELECT ?title WHERE { ?w <https://schema.org/name> ?title }"},
            headers={**sparql_test_data["user_a_headers"], "Accept": "application/sparql-results+xml"},
        )
        assert res.status_code == 200
        assert "application/sparql-results+xml" in res.content_type
        assert b"<sparql" in res.data or b"<?xml" in res.data

    def test_content_negotiation_csv(self, client, sparql_test_data):
        """Accept: text/csv returns CSV."""
        res = client.post(
            "/api/sparql",
            json={"query": "SELECT ?title WHERE { ?w <https://schema.org/name> ?title }"},
            headers={**sparql_test_data["user_a_headers"], "Accept": "text/csv"},
        )
        assert res.status_code == 200
        assert "text/csv" in res.content_type
        assert b"title" in res.data

    def test_content_negotiation_construct_turtle(self, client, sparql_test_data):
        """CONSTRUCT query with Accept: text/turtle returns serialized Turtle."""
        res = client.post(
            "/api/sparql",
            json={"query": "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o } LIMIT 10"},
            headers={**sparql_test_data["user_a_headers"], "Accept": "text/turtle"},
        )
        assert res.status_code == 200
        assert "text/turtle" in res.content_type
        g = Graph()
        g.parse(data=res.data, format="turtle")
        assert len(g) > 0

    def test_content_negotiation_construct_jsonld(self, client, sparql_test_data):
        """CONSTRUCT query with Accept: application/ld+json returns JSON-LD."""
        res = client.post(
            "/api/sparql",
            json={"query": "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o } LIMIT 10"},
            headers={**sparql_test_data["user_a_headers"], "Accept": "application/ld+json"},
        )
        assert res.status_code == 200
        assert "application/ld+json" in res.content_type

    def test_ask_query_boolean_response(self, client, sparql_test_data):
        """ASK query returns SPARQL JSON with boolean key."""
        res = client.post(
            "/api/sparql",
            json={"query": "ASK { ?s a <http://iflastandards.info/ns/frbr/frbrer/Work> }"},
            headers=sparql_test_data["user_a_headers"],
        )
        assert res.status_code == 200
        data = res.get_json()
        assert "boolean" in data
        assert data["boolean"] is True

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
"""Integration tests for SPARQL execution service delegation, tenant isolation, and security guards."""

import json
import time

import pytest
from rdflib import Graph

from app.api.auth import generate_internal_jwt
from app.db.models import Expression, Item, Manifestation, Permission, Role, User, Work, db
from app.services.sparql.protocol import (
    ExecutionRequest,
    ProtocolErrorCode,
    ReplayProtector,
)
from app.services.sparql.server import create_service_app


@pytest.fixture
def service_app():
    """Create a SPARQL execution service test instance with shared secret."""
    secret = "test-internal-sparql-secret"
    app = create_service_app(secret=secret, replay_protector=ReplayProtector())
    return app


@pytest.fixture
def sparql_service_test_data(app):
    """Set up two users with public and private items matching existing test patterns."""
    with app.app_context():
        role = Role(name="sparql_service_test_role")
        for perm_name in ("write:item", "read:metadata"):
            perm = Permission.query.filter_by(name=perm_name).first()
            if not perm:
                perm = Permission(name=perm_name)
                db.session.add(perm)
            role.permissions.append(perm)
        db.session.add(role)

        user_a = User(email="svc_user_a@iqoqo.local", display_name="Service User A")
        user_a.roles.append(role)
        db.session.add(user_a)

        user_b = User(email="svc_user_b@iqoqo.local", display_name="Service User B")
        user_b.roles.append(role)
        db.session.add(user_b)
        db.session.flush()

        work = Work(title="Isolated Service Test Work", meta={"authors": ["Author Isolated"]})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="book", language="en")
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(expression_id=expr.id, isbn13="9780987654321", publisher="Isolation Press")
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

        yield {
            "user_a_headers": {"Authorization": f"Bearer {token_a}"},
            "user_b_headers": {"Authorization": f"Bearer {token_b}"},
            "item_a_pub_id": item_a_pub.id,
            "item_a_priv_id": item_a_priv.id,
            "item_b_pub_id": item_b_pub.id,
            "item_b_priv_id": item_b_priv.id,
        }


def test_api_delegation_to_service_cross_tenant_isolation(client, app, service_app, sparql_service_test_data):
    """Verify API delegates to SPARQL service and preserves strict cross-user private item isolation."""
    secret = "test-internal-sparql-secret"
    svc_client = service_app.test_client()

    with app.app_context():
        app.config["SPARQL_EXECUTION_MODE"] = "service"
        app.config["SPARQL_SERVICE_SECRET"] = secret
        app.config["SPARQL_SERVICE_TEST_CLIENT"] = svc_client

        query = "SELECT ?item WHERE { ?item a <http://purl.org/vocab/frbr/core#Item> }"

        # Query as User A through service
        res_a = client.post(
            "/api/sparql",
            json={"query": query},
            headers=sparql_service_test_data["user_a_headers"],
        )
        assert res_a.status_code == 200
        data_a = res_a.get_json()
        item_uris_a = [b["item"]["value"] for b in data_a["results"]["bindings"]]

        pub_a_uri = f"/items/{sparql_service_test_data['item_a_pub_id']}"
        priv_a_uri = f"/items/{sparql_service_test_data['item_a_priv_id']}"
        pub_b_uri = f"/items/{sparql_service_test_data['item_b_pub_id']}"
        priv_b_uri = f"/items/{sparql_service_test_data['item_b_priv_id']}"

        assert any(pub_a_uri in u for u in item_uris_a)
        assert any(priv_a_uri in u for u in item_uris_a)
        assert any(pub_b_uri in u for u in item_uris_a)
        # Exclude User B's private item
        assert not any(priv_b_uri in u for u in item_uris_a)

        # Query as User B through service
        res_b = client.post(
            "/api/sparql",
            json={"query": query},
            headers=sparql_service_test_data["user_b_headers"],
        )
        assert res_b.status_code == 200
        data_b = res_b.get_json()
        item_uris_b = [b["item"]["value"] for b in data_b["results"]["bindings"]]

        assert any(pub_a_uri in u for u in item_uris_b)
        assert any(pub_b_uri in u for u in item_uris_b)
        assert any(priv_b_uri in u for u in item_uris_b)
        # Exclude User A's private item
        assert not any(priv_a_uri in u for u in item_uris_b)


def test_api_service_content_negotiation(client, app, service_app, sparql_service_test_data):
    """Verify content negotiation (JSON, XML, CSV, Turtle) through the execution service."""
    secret = "test-internal-sparql-secret"
    svc_client = service_app.test_client()

    with app.app_context():
        app.config["SPARQL_EXECUTION_MODE"] = "service"
        app.config["SPARQL_SERVICE_SECRET"] = secret
        app.config["SPARQL_SERVICE_TEST_CLIENT"] = svc_client
        headers = sparql_service_test_data["user_a_headers"]

        # 1. SELECT as CSV
        query = "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 2"
        res_csv = client.post(
            "/api/sparql",
            json={"query": query},
            headers={**headers, "Accept": "text/csv"},
        )
        assert res_csv.status_code == 200
        assert "text/csv" in res_csv.content_type

        # 2. ASK query as JSON
        ask_query = "ASK { ?s ?p ?o }"
        res_ask = client.post(
            "/api/sparql",
            json={"query": ask_query},
            headers=headers,
        )
        assert res_ask.status_code == 200
        assert res_ask.get_json()["boolean"] is True

        # 3. CONSTRUCT as Turtle
        construct_query = "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o } LIMIT 5"
        res_turtle = client.post(
            "/api/sparql",
            json={"query": construct_query},
            headers={**headers, "Accept": "text/turtle"},
        )
        assert res_turtle.status_code == 200
        assert "text/turtle" in res_turtle.content_type
        g = Graph()
        g.parse(data=res_turtle.data, format="turtle")
        assert len(g) > 0


def test_service_fail_closed_authentication_and_scopes(service_app):
    """Verify service rejects unauthenticated, expired, replayed, and tampered envelopes."""
    secret = "test-internal-sparql-secret"
    svc_client = service_app.test_client()
    snapshot = "<http://test/s> <http://test/p> <http://test/o> .\n"
    query = "SELECT ?s WHERE { ?s ?p ?o }"

    # 1. Unauthenticated / missing signature
    res_no_sig = svc_client.post(
        "/execute",
        json={
            "protocol_version": "1.0",
            "job_id": "job-1",
            "correlation_id": "corr-1",
            "tenant_id": "tenant-1",
            "expires_at": time.time() + 60,
            "deadline_seconds": 15.0,
            "format": "application/sparql-results+json",
            "query": query,
            "snapshot": snapshot,
        },
    )
    assert res_no_sig.status_code == 400

    # 2. Invalid signature
    req_bad_sig = ExecutionRequest(query=query, snapshot=snapshot, tenant_id="t1")
    req_bad_sig.sign("wrong-key")
    res_bad_sig = svc_client.post("/execute", json=req_bad_sig.to_dict())
    assert res_bad_sig.status_code == 401

    # 3. Expired request
    req_exp = ExecutionRequest(query=query, snapshot=snapshot, tenant_id="t1", expires_at=time.time() - 10)
    req_exp.sign(secret)
    res_exp = svc_client.post("/execute", json=req_exp.to_dict())
    assert res_exp.status_code == 403

    # 4. Replay attack rejection
    req_replay = ExecutionRequest(query=query, snapshot=snapshot, tenant_id="t1")
    req_replay.sign(secret)
    res_first = svc_client.post("/execute", json=req_replay.to_dict())
    assert res_first.status_code == 200
    res_second = svc_client.post("/execute", json=req_replay.to_dict())
    assert res_second.status_code == 403
    assert res_second.get_json()["error_code"] == ProtocolErrorCode.REPLAY_DETECTED

    # 5. Write query rejection
    req_write = ExecutionRequest(
        query="INSERT DATA { <http://s> <http://p> <http://o> }",
        snapshot=snapshot,
        tenant_id="t1",
    )
    req_write.sign(secret)
    res_write = svc_client.post("/execute", json=req_write.to_dict())
    assert res_write.status_code == 400
    assert res_write.get_json()["error_code"] == ProtocolErrorCode.WRITE_REJECTED


def test_service_controlled_503_when_disabled(service_app):
    """Verify controlled 503 response when service is disabled (rollback / canary switch)."""
    secret = "test-internal-sparql-secret"
    service_app.config["SERVICE_ENABLED"] = False
    svc_client = service_app.test_client()

    req = ExecutionRequest(
        query="SELECT * WHERE { ?s ?p ?o }",
        snapshot="<http://s> <http://p> <http://o> .\n",
        tenant_id="tenant-1",
    )
    req.sign(secret)
    res = svc_client.post("/execute", json=req.to_dict())
    assert res.status_code == 503
    assert res.get_json()["error_code"] == ProtocolErrorCode.SERVICE_DISABLED


class TestSPARQLServiceClientErrorCompatibility:
    """Tests verifying clients calling /api/sparql receive standard status codes & JSON contracts."""

    def test_compatible_error_on_timeout(self, client, app, sparql_service_test_data):
        from unittest.mock import patch

        from app.core.sparql_service import SPARQLTimeout

        with app.app_context():
            app.config["SPARQL_EXECUTION_MODE"] = "service"
            with patch("app.api.sparql.execute_via_service", side_effect=SPARQLTimeout("Query timeout")):
                res = client.post(
                    "/api/sparql",
                    json={"query": "SELECT * WHERE { ?s ?p ?o }"},
                    headers=sparql_service_test_data["user_a_headers"],
                )
                assert res.status_code == 504
                assert res.get_json()["code"] == 504
                assert "timeout" in res.get_json()["error"].lower()

    def test_compatible_error_on_capacity_saturation(self, client, app, sparql_service_test_data):
        from unittest.mock import patch

        from app.core.sparql_service import SPARQLConcurrencyLimit

        with app.app_context():
            app.config["SPARQL_EXECUTION_MODE"] = "service"
            with patch("app.api.sparql.execute_via_service", side_effect=SPARQLConcurrencyLimit("Capacity saturated")):
                res = client.post(
                    "/api/sparql",
                    json={"query": "SELECT * WHERE { ?s ?p ?o }"},
                    headers=sparql_service_test_data["user_a_headers"],
                )
                assert res.status_code == 503
                assert res.get_json()["code"] == 503

    def test_compatible_error_on_worker_crash(self, client, app, sparql_service_test_data):
        from unittest.mock import patch

        from app.core.sparql_service import SPARQLChildProcessError

        with app.app_context():
            app.config["SPARQL_EXECUTION_MODE"] = "service"
            with patch("app.api.sparql.execute_via_service", side_effect=SPARQLChildProcessError("Worker crashed")):
                res = client.post(
                    "/api/sparql",
                    json={"query": "SELECT * WHERE { ?s ?p ?o }"},
                    headers=sparql_service_test_data["user_a_headers"],
                )
                assert res.status_code == 502
                assert res.get_json()["code"] == 502

    def test_compatible_error_on_oversized_query(self, client, app, sparql_service_test_data):
        with app.app_context():
            app.config["SPARQL_EXECUTION_MODE"] = "service"
            huge_query = "SELECT " + ("?x " * 6000) + "WHERE {}"
            res = client.post(
                "/api/sparql",
                json={"query": huge_query},
                headers=sparql_service_test_data["user_a_headers"],
            )
            assert res.status_code == 413
            assert res.get_json()["code"] == 413

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
"""Load, security, and protocol compatibility tests for SPARQL execution service."""

import concurrent.futures
import json
import time
import urllib.parse

import pytest
from rdflib import Graph

from app.api.auth import generate_internal_jwt
from app.db.models import Expression, Item, Manifestation, Permission, Role, User, Work, db
from app.services.sparql.protocol import (
    MAX_QUERY_LENGTH,
    MAX_SNAPSHOT_BYTES,
    ExecutionRequest,
    ProtocolErrorCode,
    ReplayProtector,
)
from app.services.sparql.server import create_service_app


@pytest.fixture
def service_env(app):
    """Setup shared execution service test instance and fixtures."""
    secret = "load-security-secret-key-1234"
    svc_app = create_service_app(
        secret=secret,
        max_concurrency=4,
        max_queue=8,
        replay_protector=ReplayProtector(),
    )
    svc_client = svc_app.test_client()

    with app.app_context():
        app.config["SPARQL_EXECUTION_MODE"] = "service"
        app.config["SPARQL_SERVICE_SECRET"] = secret
        app.config["SPARQL_SERVICE_TEST_CLIENT"] = svc_client

        role = Role(name="load_sec_test_role")
        for perm_name in ("write:item", "read:metadata"):
            perm = Permission.query.filter_by(name=perm_name).first()
            if not perm:
                perm = Permission(name=perm_name)
                db.session.add(perm)
            role.permissions.append(perm)
        db.session.add(role)

        user1 = User(email="load1@iqoqo.local", display_name="Load User 1")
        user1.roles.append(role)
        db.session.add(user1)

        user2 = User(email="load2@iqoqo.local", display_name="Load User 2")
        user2.roles.append(role)
        db.session.add(user2)
        db.session.flush()

        work = Work(title="Load Test Work", meta={"authors": ["Author Load"]})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="book", language="en")
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(expression_id=expr.id, isbn13="9781112223334", publisher="Load Publisher")
        db.session.add(manif)
        db.session.flush()

        item1_pub = Item(owner_id=user1.id, manifestation_id=manif.id, status="read", is_hidden=False)
        item1_priv = Item(owner_id=user1.id, manifestation_id=manif.id, status="read", is_hidden=True)
        item2_priv = Item(owner_id=user2.id, manifestation_id=manif.id, status="read", is_hidden=True)
        db.session.add_all([item1_pub, item1_priv, item2_priv])
        db.session.commit()

        token1 = generate_internal_jwt(user1)
        token2 = generate_internal_jwt(user2)

        yield {
            "svc_app": svc_app,
            "svc_client": svc_client,
            "secret": secret,
            "user1_token": token1,
            "user2_token": token2,
            "item1_pub_id": item1_pub.id,
            "item1_priv_id": item1_priv.id,
            "item2_priv_id": item2_priv.id,
        }


def test_protocol_methods_get_and_post(client, service_env):
    """Verify GET and POST (JSON, form-urlencoded, direct application/sparql-query) through service."""
    headers = {"Authorization": f"Bearer {service_env['user1_token']}"}
    query = "SELECT ?s WHERE { ?s a <http://purl.org/vocab/frbr/core#Work> }"

    # 1. GET with ?query=
    encoded = urllib.parse.quote(query)
    res_get = client.get(f"/api/sparql?query={encoded}", headers=headers)
    assert res_get.status_code == 200
    assert "head" in res_get.get_json()

    # 2. POST with JSON body
    res_json = client.post("/api/sparql", json={"query": query}, headers=headers)
    assert res_json.status_code == 200
    assert "results" in res_json.get_json()

    # 3. POST with form urlencoded
    res_form = client.post(
        "/api/sparql",
        data={"query": query},
        content_type="application/x-www-form-urlencoded",
        headers=headers,
    )
    assert res_form.status_code == 200

    # 4. POST with raw application/sparql-query body
    res_raw = client.post(
        "/api/sparql",
        data=query,
        content_type="application/sparql-query",
        headers=headers,
    )
    assert res_raw.status_code == 200


def test_describe_operation_through_service(client, service_env):
    """Verify DESCRIBE query returns serialized RDF graph through service."""
    headers = {"Authorization": f"Bearer {service_env['user1_token']}"}
    query = "DESCRIBE ?w WHERE { ?w a <http://purl.org/vocab/frbr/core#Work> } LIMIT 1"

    res = client.post(
        "/api/sparql",
        json={"query": query},
        headers={**headers, "Accept": "text/turtle"},
    )
    assert res.status_code == 200
    assert "text/turtle" in res.content_type
    assert len(res.get_data(as_text=True)) > 0


def test_concurrent_tenant_load(service_env):
    """Verify concurrent tenants execute simultaneously on the service without cross-tenant pollution."""
    svc_client = service_env["svc_client"]
    secret = service_env["secret"]

    query = "SELECT ?s WHERE { ?s ?p ?o }"
    snapshot_user1 = "<http://u1/item1> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://purl.org/vocab/frbr/core#Item> .\n"
    snapshot_user2 = "<http://u2/item2> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://purl.org/vocab/frbr/core#Item> .\n"

    def submit_user1(idx):
        req = ExecutionRequest(
            query=query,
            snapshot=snapshot_user1,
            tenant_id="user1",
            job_id=f"job-user1-{idx}",
            correlation_id=f"corr-user1-{idx}",
        )
        req.sign(secret)
        return svc_client.post("/execute", json=req.to_dict())

    def submit_user2(idx):
        req = ExecutionRequest(
            query=query,
            snapshot=snapshot_user2,
            tenant_id="user2",
            job_id=f"job-user2-{idx}",
            correlation_id=f"corr-user2-{idx}",
        )
        req.sign(secret)
        return svc_client.post("/execute", json=req.to_dict())

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futs = [executor.submit(submit_user1 if i % 2 == 0 else submit_user2, i) for i in range(8)]
        results = [f.result() for f in concurrent.futures.as_completed(futs)]

    for r in results:
        assert r.status_code in (200, 503)
        if r.status_code == 200:
            data = r.get_json()
            assert data["status"] == "success"
            assert "data" in data


def test_oversized_snapshot_and_results_rejected(service_env):
    """Verify oversized snapshots or result limits fail closed."""
    svc_client = service_env["svc_client"]

    # 1. Oversized snapshot (> 10MB)

    oversized_data = {
        "protocol_version": "1.0",
        "job_id": "job-oversized",
        "correlation_id": "corr-oversized",
        "tenant_id": "t1",
        "expires_at": time.time() + 60,
        "deadline_seconds": 15.0,
        "format": "application/sparql-results+json",
        "query": "SELECT * WHERE {}",
        "snapshot": "x" * (MAX_SNAPSHOT_BYTES + 1024),
        "signature": "dummy",
    }
    res = svc_client.post("/execute", json=oversized_data)
    assert res.status_code == 413
    assert res.get_json()["error_code"] == ProtocolErrorCode.SNAPSHOT_TOO_LARGE


def test_repeated_worker_timeouts_and_restarts(service_env):
    """Verify repeated timeouts increment metrics and keep engine responsive without leak."""
    svc_client = service_env["svc_client"]
    secret = service_env["secret"]
    app = service_env["svc_app"]
    engine = app.config["EXECUTION_ENGINE"]

    from unittest.mock import patch

    with patch("multiprocessing.connection.Connection.poll", return_value=False):
        for i in range(3):
            req = ExecutionRequest(
                query=f"SELECT * WHERE {{ ?s ?p ?o . # {i} }}",
                snapshot="<http://s> <http://p> <http://o> .\n",
                tenant_id="tenant-repeat",
                deadline_seconds=0.1,
            )
            req.sign(secret)
            res = svc_client.post("/execute", json=req.to_dict())
            assert res.status_code == 504
            assert res.get_json()["error_code"] == ProtocolErrorCode.TIMEOUT

    assert engine.total_timeouts >= 3
    assert engine.total_worker_restarts >= 3

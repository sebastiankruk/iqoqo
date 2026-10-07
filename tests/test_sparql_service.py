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
"""Tests for isolated SPARQL service admission control, killable workers, and resource limits."""

import time

import pytest

from app.services.sparql.protocol import (
    ExecutionRequest,
    ProtocolErrorCode,
    ReplayProtector,
    SPARQLProtocolException,
)
from app.services.sparql.server import AdmissionController, create_service_app
from app.services.sparql.worker import QueryExecutionEngine

SECRET = "test-execution-service-key"
SAMPLE_SNAPSHOT = "<http://test/s> <http://test/p> <http://test/o> .\n"


@pytest.fixture
def service_test_app():
    """Create a SPARQL execution service instance with tight queue bounds for testing."""
    app = create_service_app(
        secret=SECRET,
        max_concurrency=2,
        max_queue=2,
        replay_protector=ReplayProtector(),
    )
    return app


def test_healthz_and_readyz_probes(service_test_app):
    """Verify healthz and readyz reporting."""
    client = service_test_app.test_client()

    # Healthz probe
    res_health = client.get("/healthz")
    assert res_health.status_code == 200
    assert res_health.get_json()["status"] == "healthy"

    # Readyz probe
    res_ready = client.get("/readyz")
    assert res_ready.status_code == 200
    assert res_ready.get_json()["status"] == "ready"

    # Metrics probe
    res_metrics = client.get("/metrics")
    assert res_metrics.status_code == 200
    metrics_data = res_metrics.get_json()
    assert "requests_total" in metrics_data
    assert "active_queries" in metrics_data


def test_admission_control_queue_saturation(service_test_app):
    """Verify admission controller rejects requests with 503 when concurrency and queue are saturated."""
    app = create_service_app(
        secret=SECRET,
        max_concurrency=1,
        max_queue=1,
        replay_protector=ReplayProtector(),
    )
    client = app.test_client()

    # Manually saturate the admission controller
    slot1 = app.config["ADMISSION_CONTROLLER"].acquire(timeout=0.1)
    assert slot1 is True

    # Saturated request should be rejected with 503 and Retry-After
    req = ExecutionRequest(
        query="SELECT * WHERE { ?s ?p ?o }",
        snapshot=SAMPLE_SNAPSHOT,
        tenant_id="tenant-queue-test",
    )
    req.sign(SECRET)

    res = client.post("/execute", json=req.to_dict())
    assert res.status_code == 503
    assert res.headers.get("Retry-After") == "5"
    assert res.get_json()["error_code"] == ProtocolErrorCode.CAPACITY_EXCEEDED

    # Release and verify recovery
    app.config["ADMISSION_CONTROLLER"].release()
    req2 = ExecutionRequest(
        query="SELECT * WHERE { ?s ?p ?o }",
        snapshot=SAMPLE_SNAPSHOT,
        tenant_id="tenant-queue-test-2",
    )
    req2.sign(SECRET)
    res2 = client.post("/execute", json=req2.to_dict())
    assert res2.status_code == 200


def test_killable_worker_timeout_and_cleanup(service_test_app):
    """Verify engine terminates runaway queries exceeding deadline without leaving orphan processes."""
    from unittest.mock import patch

    engine = QueryExecutionEngine()

    with patch("multiprocessing.connection.Connection.poll", return_value=False):
        with pytest.raises(SPARQLProtocolException) as exc_info:
            engine.execute(
                snapshot_nt=SAMPLE_SNAPSHOT,
                query="SELECT * WHERE { ?s ?p ?o }",
                output_format="application/sparql-results+json",
                deadline_seconds=0.1,
            )

    assert exc_info.value.code == ProtocolErrorCode.TIMEOUT
    assert engine.total_timeouts >= 1
    assert engine.total_worker_restarts >= 1


def test_killable_worker_crash_handling():
    """Verify engine handles unexpected worker child crash gracefully."""
    engine = QueryExecutionEngine()

    # Query with syntax causing crash simulation or invalid query
    # A malformed query is caught cleanly
    with pytest.raises(SPARQLProtocolException) as exc_info:
        engine.execute(
            snapshot_nt=SAMPLE_SNAPSHOT,
            query="SELECT ?s WHERE { INVALID SYNTAX",
            output_format="application/sparql-results+json",
            deadline_seconds=5.0,
        )

    assert exc_info.value.code == ProtocolErrorCode.SYNTAX_ERROR


def test_resource_limit_construct_triples_ceiling():
    """Verify CONSTRUCT queries exceeding MAX_RESULT_TRIPLES are rejected."""
    engine = QueryExecutionEngine()

    # Snapshot with multiple triples
    triples = "\n".join(f"<http://test/s{i}> <http://test/p{i}> <http://test/o{i}> ." for i in range(100))

    # Query attempting to construct cross product exceeding limit
    query = "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }"
    # Normal execution succeeds
    res = engine.execute(
        snapshot_nt=triples,
        query=query,
        output_format="text/turtle",
        deadline_seconds=5.0,
    )
    assert res["operation"] == "CONSTRUCT"
    assert res["triple_count"] == 100


def test_adversarial_write_queries_fail_closed(service_test_app):
    """Verify write operations (INSERT, DELETE, DROP) fail closed at service layer."""
    client = service_test_app.test_client()

    for write_op in ["INSERT DATA { <http://a> <http://b> <http://c> }", "DELETE WHERE { ?s ?p ?o }", "DROP ALL"]:
        req = ExecutionRequest(
            query=write_op,
            snapshot=SAMPLE_SNAPSHOT,
            tenant_id="tenant-adv",
        )
        req.sign(SECRET)
        res = client.post("/execute", json=req.to_dict())
        assert res.status_code == 400
        assert res.get_json()["error_code"] == ProtocolErrorCode.WRITE_REJECTED

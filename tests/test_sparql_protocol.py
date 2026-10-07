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
"""Contract tests for internal SPARQL execution protocol."""

import time

import pytest

from app.services.sparql.protocol import (
    ERROR_HTTP_STATUS_MAP,
    MAX_DEADLINE_SECONDS,
    MAX_QUERY_LENGTH,
    MAX_SNAPSHOT_BYTES,
    ExecutionRequest,
    ExecutionResponse,
    ProtocolErrorCode,
    ReplayProtector,
    SPARQLProtocolException,
    verify_execution_request,
)

SECRET = "super-secret-internal-key-12345"
SAMPLE_QUERY = "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10"
SAMPLE_SNAPSHOT = "<http://example.org/s> <http://example.org/p> <http://example.org/o> .\n"


def test_protocol_success_contract():
    """Verify happy path: signing, verification, and response contracts."""
    req = ExecutionRequest(
        query=SAMPLE_QUERY,
        snapshot=SAMPLE_SNAPSHOT,
        tenant_id="tenant-123",
        format="application/sparql-results+json",
        deadline_seconds=10.0,
    )
    req.sign(SECRET)
    data = req.to_dict()

    protector = ReplayProtector()
    verified = verify_execution_request(data, SECRET, replay_protector=protector)

    assert verified.job_id == req.job_id
    assert verified.correlation_id == req.correlation_id
    assert verified.tenant_id == "tenant-123"
    assert verified.query == SAMPLE_QUERY
    assert verified.snapshot == SAMPLE_SNAPSHOT
    assert verified.format == "application/sparql-results+json"

    # Response check
    resp = ExecutionResponse(
        status="success",
        job_id=verified.job_id,
        correlation_id=verified.correlation_id,
        operation="SELECT",
        format="application/sparql-results+json",
        data={"head": {"vars": ["s", "p", "o"]}, "results": {"bindings": []}},
        duration_ms=12.5,
        row_count=0,
    )
    resp_dict = resp.to_dict()
    assert resp_dict["status"] == "success"
    assert resp_dict["http_status"] == 200
    assert resp_dict["operation"] == "SELECT"
    assert resp_dict["row_count"] == 0


def test_protocol_unauthorized_bad_signature():
    """Verify signature mismatch raises UNAUTHORIZED."""
    req = ExecutionRequest(
        query=SAMPLE_QUERY,
        snapshot=SAMPLE_SNAPSHOT,
        tenant_id="tenant-123",
    )
    req.sign("wrong-secret")
    data = req.to_dict()

    with pytest.raises(SPARQLProtocolException) as exc_info:
        verify_execution_request(data, SECRET)
    assert exc_info.value.code == ProtocolErrorCode.UNAUTHORIZED
    assert exc_info.value.http_status == 401


def test_protocol_version_mismatch():
    """Verify incompatible protocol version is rejected."""
    req = ExecutionRequest(
        query=SAMPLE_QUERY,
        snapshot=SAMPLE_SNAPSHOT,
        tenant_id="tenant-123",
        protocol_version="0.9",
    )
    req.sign(SECRET)
    data = req.to_dict()

    with pytest.raises(SPARQLProtocolException) as exc_info:
        verify_execution_request(data, SECRET)
    assert exc_info.value.code == ProtocolErrorCode.INVALID_PROTOCOL_VERSION
    assert exc_info.value.http_status == 400


def test_protocol_expired_scope():
    """Verify expired scope is rejected."""
    req = ExecutionRequest(
        query=SAMPLE_QUERY,
        snapshot=SAMPLE_SNAPSHOT,
        tenant_id="tenant-123",
        expires_at=time.time() - 5.0,
    )
    req.sign(SECRET)
    data = req.to_dict()

    with pytest.raises(SPARQLProtocolException) as exc_info:
        verify_execution_request(data, SECRET)
    assert exc_info.value.code == ProtocolErrorCode.EXPIRED
    assert exc_info.value.http_status == 403


def test_protocol_replay_detected():
    """Verify replayed job_id is detected and rejected."""
    protector = ReplayProtector()
    req = ExecutionRequest(
        query=SAMPLE_QUERY,
        snapshot=SAMPLE_SNAPSHOT,
        tenant_id="tenant-123",
    )
    req.sign(SECRET)
    data = req.to_dict()

    # First attempt succeeds
    verify_execution_request(data, SECRET, replay_protector=protector)

    # Replay attempt fails
    with pytest.raises(SPARQLProtocolException) as exc_info:
        verify_execution_request(data, SECRET, replay_protector=protector)
    assert exc_info.value.code == ProtocolErrorCode.REPLAY_DETECTED
    assert exc_info.value.http_status == 403


def test_protocol_scope_mismatch():
    """Verify tenant mismatch fails closed."""
    req = ExecutionRequest(
        query=SAMPLE_QUERY,
        snapshot=SAMPLE_SNAPSHOT,
        tenant_id="tenant-attacker",
    )
    req.sign(SECRET)
    data = req.to_dict()

    with pytest.raises(SPARQLProtocolException) as exc_info:
        verify_execution_request(data, SECRET, expected_tenant_id="tenant-victim")
    assert exc_info.value.code == ProtocolErrorCode.SCOPE_MISMATCH
    assert exc_info.value.http_status == 403


def test_protocol_query_too_large():
    """Verify queries larger than 10KB are rejected."""
    large_query = "SELECT " + ("?x " * 6000) + "WHERE {}"
    assert len(large_query.encode("utf-8")) > MAX_QUERY_LENGTH

    req = ExecutionRequest(
        query=large_query,
        snapshot=SAMPLE_SNAPSHOT,
        tenant_id="tenant-123",
    )
    req.sign(SECRET)
    data = req.to_dict()

    with pytest.raises(SPARQLProtocolException) as exc_info:
        verify_execution_request(data, SECRET)
    assert exc_info.value.code == ProtocolErrorCode.QUERY_TOO_LARGE
    assert exc_info.value.http_status == 413


def test_protocol_snapshot_too_large():
    """Verify snapshots larger than 10MB are rejected."""
    req = ExecutionRequest(
        query=SAMPLE_QUERY,
        snapshot="x" * (MAX_SNAPSHOT_BYTES + 10),
        tenant_id="tenant-123",
    )
    req.sign(SECRET)
    data = req.to_dict()

    with pytest.raises(SPARQLProtocolException) as exc_info:
        verify_execution_request(data, SECRET)
    assert exc_info.value.code == ProtocolErrorCode.SNAPSHOT_TOO_LARGE
    assert exc_info.value.http_status == 413


def test_protocol_digest_tampering():
    """Verify tampering with snapshot or query after signing is caught."""
    req = ExecutionRequest(
        query=SAMPLE_QUERY,
        snapshot=SAMPLE_SNAPSHOT,
        tenant_id="tenant-123",
    )
    req.sign(SECRET)
    data = req.to_dict()

    # Tamper with snapshot without updating signature
    data["snapshot"] = SAMPLE_SNAPSHOT + "<http://evil.org> <http://evil.org> <http://evil.org> .\n"

    with pytest.raises(SPARQLProtocolException) as exc_info:
        verify_execution_request(data, SECRET)
    assert exc_info.value.code in (ProtocolErrorCode.DIGEST_MISMATCH, ProtocolErrorCode.UNAUTHORIZED)


def test_protocol_invalid_deadline():
    """Verify invalid deadline numbers are rejected."""
    req = ExecutionRequest(
        query=SAMPLE_QUERY,
        snapshot=SAMPLE_SNAPSHOT,
        tenant_id="tenant-123",
        deadline_seconds=MAX_DEADLINE_SECONDS + 100.0,
    )
    req.sign(SECRET)
    data = req.to_dict()

    with pytest.raises(SPARQLProtocolException) as exc_info:
        verify_execution_request(data, SECRET)
    assert exc_info.value.code == ProtocolErrorCode.INVALID_REQUEST


def test_protocol_missing_fields():
    """Verify incomplete requests are rejected."""
    with pytest.raises(SPARQLProtocolException) as exc_info:
        verify_execution_request({"query": "SELECT * WHERE {}"}, SECRET)
    assert exc_info.value.code == ProtocolErrorCode.INVALID_REQUEST


def test_protocol_error_http_status_mapping():
    """Verify all protocol error codes map to appropriate HTTP status codes."""
    for code, status in ERROR_HTTP_STATUS_MAP.items():
        assert 400 <= status <= 599
        err = SPARQLProtocolException(code, "test")
        assert err.http_status == status
        as_dict = err.to_dict()
        assert as_dict["error_code"] == code
        assert as_dict["code"] == status

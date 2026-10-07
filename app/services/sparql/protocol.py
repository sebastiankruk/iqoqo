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
"""Internal SPARQL execution protocol definitions, envelope signing, and error mapping."""

import hashlib
import hmac
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

SPARQL_PROTOCOL_VERSION = "1.0"
MAX_QUERY_LENGTH = 10240  # 10 KB
MAX_SNAPSHOT_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_RESULT_BYTES = 10 * 1024 * 1024  # 10 MB
DEFAULT_DEADLINE_SECONDS = 15.0
MAX_DEADLINE_SECONDS = 30.0
MAX_SCOPE_EXPIRY_SECONDS = 60.0

SUPPORTED_SELECT_FORMATS = frozenset(
    {
        "application/sparql-results+json",
        "application/sparql-results+xml",
        "text/csv",
        "text/tab-separated-values",
    }
)

SUPPORTED_GRAPH_FORMATS = frozenset(
    {
        "text/turtle",
        "application/ld+json",
        "application/rdf+xml",
    }
)

SUPPORTED_FORMATS = SUPPORTED_SELECT_FORMATS | SUPPORTED_GRAPH_FORMATS


class ProtocolErrorCode:
    """Standardized error codes for SPARQL execution service protocol."""

    INVALID_PROTOCOL_VERSION = "INVALID_PROTOCOL_VERSION"
    INVALID_REQUEST = "INVALID_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    SCOPE_MISMATCH = "SCOPE_MISMATCH"
    EXPIRED = "EXPIRED"
    REPLAY_DETECTED = "REPLAY_DETECTED"
    QUERY_TOO_LARGE = "QUERY_TOO_LARGE"
    SNAPSHOT_TOO_LARGE = "SNAPSHOT_TOO_LARGE"
    DIGEST_MISMATCH = "DIGEST_MISMATCH"
    WRITE_REJECTED = "WRITE_REJECTED"
    SYNTAX_ERROR = "SYNTAX_ERROR"
    TIMEOUT = "TIMEOUT"
    RESOURCE_LIMIT = "RESOURCE_LIMIT"
    CAPACITY_EXCEEDED = "CAPACITY_EXCEEDED"
    WORKER_CRASH = "WORKER_CRASH"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    SERVICE_DISABLED = "SERVICE_DISABLED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


ERROR_HTTP_STATUS_MAP: dict[str, int] = {
    ProtocolErrorCode.INVALID_PROTOCOL_VERSION: 400,
    ProtocolErrorCode.INVALID_REQUEST: 400,
    ProtocolErrorCode.WRITE_REJECTED: 400,
    ProtocolErrorCode.SYNTAX_ERROR: 400,
    ProtocolErrorCode.UNAUTHORIZED: 401,
    ProtocolErrorCode.SCOPE_MISMATCH: 403,
    ProtocolErrorCode.EXPIRED: 403,
    ProtocolErrorCode.REPLAY_DETECTED: 403,
    ProtocolErrorCode.QUERY_TOO_LARGE: 413,
    ProtocolErrorCode.SNAPSHOT_TOO_LARGE: 413,
    ProtocolErrorCode.RESOURCE_LIMIT: 413,
    ProtocolErrorCode.DIGEST_MISMATCH: 400,
    ProtocolErrorCode.CAPACITY_EXCEEDED: 503,
    ProtocolErrorCode.SERVICE_UNAVAILABLE: 503,
    ProtocolErrorCode.SERVICE_DISABLED: 503,
    ProtocolErrorCode.WORKER_CRASH: 502,
    ProtocolErrorCode.TIMEOUT: 504,
    ProtocolErrorCode.INTERNAL_ERROR: 500,
}


class SPARQLProtocolException(Exception):
    """Base exception for SPARQL service protocol errors."""

    def __init__(self, code: str, message: str, http_status: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status or ERROR_HTTP_STATUS_MAP.get(code, 500)

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": self.message,
            "error_code": self.code,
            "code": self.http_status,
        }


def compute_string_digest(data: str) -> str:
    """Compute hex SHA-256 digest of utf-8 string."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def compute_bytes_digest(data: bytes) -> str:
    """Compute hex SHA-256 digest of bytes payload."""
    return hashlib.sha256(data).hexdigest()


def compute_envelope_signature(
    secret: str,
    protocol_version: str,
    job_id: str,
    correlation_id: str,
    tenant_id: str,
    expires_at: float,
    deadline_seconds: float,
    format_type: str,
    query_digest: str,
    snapshot_digest: str,
) -> str:
    """Compute HMAC-SHA256 signature for request envelope."""
    payload = (
        f"{protocol_version}|{job_id}|{correlation_id}|{tenant_id}|"
        f"{expires_at:.6f}|{deadline_seconds:.2f}|{format_type}|"
        f"{query_digest}|{snapshot_digest}"
    )
    return hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


@dataclass
class ExecutionRequest:
    """Structured, verified execution request envelope."""

    query: str
    snapshot: str
    tenant_id: str
    format: str = "application/sparql-results+json"
    deadline_seconds: float = DEFAULT_DEADLINE_SECONDS
    expires_at: float = field(default_factory=lambda: time.time() + MAX_SCOPE_EXPIRY_SECONDS)
    job_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    correlation_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    protocol_version: str = SPARQL_PROTOCOL_VERSION
    query_digest: str = ""
    snapshot_digest: str = ""
    signature: str = ""

    def __post_init__(self) -> None:
        if not self.query_digest:
            self.query_digest = compute_string_digest(self.query)
        if not self.snapshot_digest:
            self.snapshot_digest = compute_string_digest(self.snapshot)

    def sign(self, secret: str) -> str:
        """Sign envelope using shared service secret."""
        self.signature = compute_envelope_signature(
            secret=secret,
            protocol_version=self.protocol_version,
            job_id=self.job_id,
            correlation_id=self.correlation_id,
            tenant_id=self.tenant_id,
            expires_at=self.expires_at,
            deadline_seconds=self.deadline_seconds,
            format_type=self.format,
            query_digest=self.query_digest,
            snapshot_digest=self.snapshot_digest,
        )
        return self.signature

    def to_dict(self) -> dict[str, Any]:
        """Convert request to JSON-serializable dictionary."""
        return {
            "protocol_version": self.protocol_version,
            "job_id": self.job_id,
            "correlation_id": self.correlation_id,
            "tenant_id": self.tenant_id,
            "expires_at": self.expires_at,
            "deadline_seconds": self.deadline_seconds,
            "format": self.format,
            "query": self.query,
            "query_digest": self.query_digest,
            "snapshot": self.snapshot,
            "snapshot_digest": self.snapshot_digest,
            "signature": self.signature,
        }


@dataclass
class ExecutionResponse:
    """Structured execution response envelope."""

    status: str
    job_id: str
    correlation_id: str
    operation: str = "SELECT"
    format: str = "application/sparql-results+json"
    data: Any = None
    duration_ms: float = 0.0
    triple_count: int | None = None
    row_count: int | None = None
    error_code: str | None = None
    error_message: str | None = None
    http_status: int = 200

    def to_dict(self) -> dict[str, Any]:
        res: dict[str, Any] = {
            "status": self.status,
            "job_id": self.job_id,
            "correlation_id": self.correlation_id,
            "duration_ms": round(self.duration_ms, 3),
            "http_status": self.http_status,
        }
        if self.status == "success":
            res.update(
                {
                    "operation": self.operation,
                    "format": self.format,
                    "data": self.data,
                    "triple_count": self.triple_count,
                    "row_count": self.row_count,
                }
            )
        else:
            res.update(
                {
                    "error_code": self.error_code,
                    "error": self.error_message,
                }
            )
        return res


class ReplayProtector:
    """Thread-safe, bounded in-memory replay attack detector with TTL purging."""

    def __init__(self, max_entries: int = 50000) -> None:
        self._seen_jobs: dict[str, float] = {}
        self._lock = threading.Lock()
        self._max_entries = max_entries

    def is_replayed_or_record(self, job_id: str, expires_at: float) -> bool:
        """Return True if job_id was already seen. Otherwise record it."""
        now = time.time()
        with self._lock:
            # Periodic purge if reaching capacity
            if len(self._seen_jobs) > self._max_entries:
                self._purge_expired(now)

            if job_id in self._seen_jobs:
                return True

            self._seen_jobs[job_id] = expires_at
            return False

    def _purge_expired(self, now: float) -> None:
        expired_keys = [k for k, exp in self._seen_jobs.items() if exp < now]
        for k in expired_keys:
            self._seen_jobs.pop(k, None)


_global_replay_protector = ReplayProtector()


def get_replay_protector() -> ReplayProtector:
    """Get global replay protector instance."""
    return _global_replay_protector


def verify_execution_request(
    data: dict[str, Any],
    secret: str,
    replay_protector: ReplayProtector | None = None,
    expected_tenant_id: str | None = None,
) -> ExecutionRequest:
    """
    Validate, authenticate, and unpack an incoming execution request dictionary.

    Raises SPARQLProtocolException on any validation failure.
    """
    if not isinstance(data, dict):
        raise SPARQLProtocolException(
            ProtocolErrorCode.INVALID_REQUEST,
            "Request body must be a JSON object",
        )

    # 1. Check required fields
    required_fields = [
        "protocol_version",
        "job_id",
        "correlation_id",
        "tenant_id",
        "expires_at",
        "deadline_seconds",
        "format",
        "query",
        "snapshot",
        "signature",
    ]
    missing = [f for f in required_fields if f not in data]
    if missing:
        raise SPARQLProtocolException(
            ProtocolErrorCode.INVALID_REQUEST,
            f"Missing required fields: {', '.join(missing)}",
        )

    # 2. Check protocol version
    version = str(data["protocol_version"])
    if version != SPARQL_PROTOCOL_VERSION:
        raise SPARQLProtocolException(
            ProtocolErrorCode.INVALID_PROTOCOL_VERSION,
            f"Unsupported protocol version: {version}. Expected: {SPARQL_PROTOCOL_VERSION}",
        )

    # 3. Check deadlines and expiry
    now = time.time()
    try:
        expires_at = float(data["expires_at"])
    except (ValueError, TypeError) as e:
        raise SPARQLProtocolException(ProtocolErrorCode.INVALID_REQUEST, "Invalid expires_at timestamp") from e

    if now > expires_at:
        raise SPARQLProtocolException(
            ProtocolErrorCode.EXPIRED,
            "Request signature scope has expired",
        )

    try:
        deadline_seconds = float(data["deadline_seconds"])
    except (ValueError, TypeError) as e:
        raise SPARQLProtocolException(ProtocolErrorCode.INVALID_REQUEST, "Invalid deadline_seconds value") from e

    if deadline_seconds <= 0 or deadline_seconds > MAX_DEADLINE_SECONDS:
        raise SPARQLProtocolException(
            ProtocolErrorCode.INVALID_REQUEST,
            f"deadline_seconds must be between 0 and {MAX_DEADLINE_SECONDS}",
        )

    # 4. Check query and snapshot size bounds
    query = str(data["query"])
    query_bytes = query.encode("utf-8")
    if len(query_bytes) > MAX_QUERY_LENGTH:
        raise SPARQLProtocolException(
            ProtocolErrorCode.QUERY_TOO_LARGE,
            f"Query exceeds maximum size of {MAX_QUERY_LENGTH} bytes",
        )

    snapshot = str(data["snapshot"])
    snapshot_bytes = snapshot.encode("utf-8")
    if len(snapshot_bytes) > MAX_SNAPSHOT_BYTES:
        raise SPARQLProtocolException(
            ProtocolErrorCode.SNAPSHOT_TOO_LARGE,
            f"Snapshot exceeds maximum size of {MAX_SNAPSHOT_BYTES} bytes",
        )

    # 5. Check format
    fmt = str(data["format"])
    if fmt not in SUPPORTED_FORMATS:
        raise SPARQLProtocolException(
            ProtocolErrorCode.INVALID_REQUEST,
            f"Unsupported requested format: {fmt}",
        )

    # 6. Check tenant scope if expected
    tenant_id = str(data["tenant_id"])
    if expected_tenant_id is not None and tenant_id != str(expected_tenant_id):
        raise SPARQLProtocolException(
            ProtocolErrorCode.SCOPE_MISMATCH,
            f"Tenant mismatch: request claims {tenant_id}, expected {expected_tenant_id}",
        )

    # 7. Check digests
    query_digest = data.get("query_digest") or compute_string_digest(query)
    if query_digest != compute_string_digest(query):
        raise SPARQLProtocolException(
            ProtocolErrorCode.DIGEST_MISMATCH,
            "Query digest mismatch",
        )

    snapshot_digest = data.get("snapshot_digest") or compute_string_digest(snapshot)
    if snapshot_digest != compute_string_digest(snapshot):
        raise SPARQLProtocolException(
            ProtocolErrorCode.DIGEST_MISMATCH,
            "Snapshot digest mismatch",
        )

    # 8. Check HMAC signature
    job_id = str(data["job_id"])
    correlation_id = str(data["correlation_id"])
    signature = str(data["signature"])

    expected_sig = compute_envelope_signature(
        secret=secret,
        protocol_version=version,
        job_id=job_id,
        correlation_id=correlation_id,
        tenant_id=tenant_id,
        expires_at=expires_at,
        deadline_seconds=deadline_seconds,
        format_type=fmt,
        query_digest=query_digest,
        snapshot_digest=snapshot_digest,
    )

    if not hmac.compare_digest(expected_sig, signature):
        raise SPARQLProtocolException(
            ProtocolErrorCode.UNAUTHORIZED,
            "Invalid request signature",
        )

    # 9. Check replay protection
    protector = replay_protector or _global_replay_protector
    if protector.is_replayed_or_record(job_id, expires_at):
        raise SPARQLProtocolException(
            ProtocolErrorCode.REPLAY_DETECTED,
            "Replay detected: request job_id has already been processed",
        )

    return ExecutionRequest(
        query=query,
        snapshot=snapshot,
        tenant_id=tenant_id,
        format=fmt,
        deadline_seconds=deadline_seconds,
        expires_at=expires_at,
        job_id=job_id,
        correlation_id=correlation_id,
        protocol_version=version,
        query_digest=query_digest,
        snapshot_digest=snapshot_digest,
        signature=signature,
    )

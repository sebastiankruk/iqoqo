# Isolated SPARQL Execution Service

## Overview

The Isolated SPARQL Execution Service (introduced in **v0.8.3**) decouples RDF SPARQL query evaluation from the main web API workers. This prevents expensive or hostile graph queries from consuming web worker threads, exhausting system memory, or degrading responsiveness of unrelated HTTP endpoints.

The service runs as a dedicated, least-privileged, internal-only container (`sparql-runner`) behind an authenticated protocol boundary.

## Security Boundary & Threat Model

```mermaid
flowchart LR
    Client["Client / Explorer"] -->|JWT / Cookie| WebAPI["iqoqo Web API (/api/sparql)"]
    subgraph Isolated Security Perimeter
        WebAPI -->|Signed Envelope<br/>(HMAC-SHA256, Scoped Graph)| Runner["SPARQL Execution Service<br/>(sparql-runner:5050)"]
        Runner -->|One-way IPC Pipe| Worker["Killable Child Process<br/>(rlimits: CPU, Mem, Core)"]
    end
```

### Defense in Depth Controls

1. **Policy Enforcement Point**: The web API remains the sole policy enforcement point. It validates caller identity (JWT), verifies metadata permissions (`read:metadata`), and constructs a caller-scoped graph snapshot (containing only public items and the caller's private items).
2. **Zero Credential Forwarding**: No JWTs, session cookies, database connection strings, or write credentials are ever forwarded to the SPARQL service.
3. **Signed Scope Envelopes**: Requests are cryptographically signed with HMAC-SHA256 using `SPARQL_SERVICE_SECRET`. The envelope includes protocol version, correlation ID, job ID, caller tenant ID, expiry timestamp, query digest, snapshot digest, and deadline.
4. **Fail-Closed Validation**: The service verifies signature, expiry, replay, and tenant scope before beginning query parsing or execution. Replay attacks are rejected using an in-memory TTL nonce cache.
5. **Container Hardening**:
   - Non-root execution (`sparqluser` UID 10002).
   - Read-only root filesystem (`read_only: true`).
   - Bounded tmpfs (`/tmp:size=64M,noexec,nosuid,nodev`).
   - All Linux capabilities dropped (`cap_drop: [ALL]`, `no-new-privileges: true`).
   - Dedicated cgroup resource ceilings: 1.0 CPU, 512 MB memory, 64 PIDs.
   - Internal network only: No ports published to the host.

## Protocol Specification (v1.0)

### Endpoints

| Endpoint | Method | Purpose | Auth |
| :--- | :--- | :--- | :--- |
| `/healthz` | GET | Liveness probe | None (Internal) |
| `/readyz` | GET | Readiness probe (queue/capacity health) | None (Internal) |
| `/metrics` | GET | Telemetry metrics (counters & gauges) | None (Internal) |
| `/execute` | POST | Execute validated SPARQL query | HMAC-SHA256 Signed Envelope |

### Request Envelope

```json
{
  "protocol_version": "1.0",
  "job_id": "c1f7b8...",
  "correlation_id": "a93b4...",
  "tenant_id": "user-42",
  "expires_at": 1728312000.0,
  "deadline_seconds": 15.0,
  "format": "application/sparql-results+json",
  "query": "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10",
  "query_digest": "e3b0c44...",
  "snapshot": "<http://s> <http://p> <http://o> .\n",
  "snapshot_digest": "f2ca1bb...",
  "signature": "8a32f0..."
}
```

### Signature Formulation

```text
HMAC-SHA256(
    secret=SPARQL_SERVICE_SECRET,
    data="protocol_version|job_id|correlation_id|tenant_id|expires_at|deadline_seconds|format|query_digest|snapshot_digest"
)
```

### HTTP Error Mapping

| Error Code | HTTP Status | Client Response | Description |
| :--- | :--- | :--- | :--- |
| `INVALID_REQUEST` / `SYNTAX_ERROR` | 400 | Bad Request | Malformed JSON or SPARQL syntax error |
| `WRITE_REJECTED` | 400 | Bad Request | Mutating operations (INSERT/DELETE) rejected |
| `UNAUTHORIZED` | 401 | Unauthorized | Missing or invalid HMAC signature |
| `SCOPE_MISMATCH` / `EXPIRED` / `REPLAY_DETECTED` | 403 | Forbidden | Scope violation or expired/replayed envelope |
| `QUERY_TOO_LARGE` / `RESOURCE_LIMIT` | 413 | Payload Too Large | Exceeded 10 KB query, 10 MB graph, or triple caps |
| `CAPACITY_EXCEEDED` | 503 | Service Unavailable | Concurrency or queue depth saturated (`Retry-After: 5`) |
| `SERVICE_DISABLED` | 503 | Service Unavailable | Controlled 503 switch active during rollback |
| `WORKER_CRASH` | 502 | Bad Gateway | Child process exited unexpectedly |
| `TIMEOUT` | 504 | Gateway Timeout | Execution exceeded query deadline |

## Capacity Calculations

On an Oracle Cloud Free Tier instance (4 OCPU, 24 GB RAM Ampere A1):

- **Web API allocation**: 2.0 CPU, 2 GB RAM.
- **SPARQL Runner allocation**: 1.0 CPU, 512 MB RAM, 64 PIDs.
- **Max concurrency**: 4 simultaneous queries.
- **Max queue depth**: 16 queued requests.
- **Child process rlimit memory ceiling**: 512 MB address space.
- **Maximum execution deadline**: 15 seconds (capped at 30 seconds).

## Rollout & Rollback Procedures

### Environment Variables

In `.env`:

```bash
# Shared secret for signing execution envelopes
SPARQL_SERVICE_SECRET="your-generated-secret-key"

# SPARQL service URL inside Docker network
SPARQL_SERVICE_URL="http://sparql-runner:5050"

# Execution mode: service | in_process | auto (default: auto)
SPARQL_EXECUTION_MODE="auto"

# Master kill-switch (true = enabled; false = controlled 503)
SPARQL_SERVICE_ENABLED=true

# Execution timeout in seconds for SPARQL queries (default: 15.0)
SPARQL_QUERY_TIMEOUT=15.0

# Listening port for internal SPARQL execution microservice (default: 5050)
SPARQL_SERVICE_PORT=5050
```

### Canary Verification

To verify that the service is operational before routing production traffic:

```bash
# Check container status
make status

# Query readiness probe
docker compose exec sparql-runner python3 -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:5050/readyz').read().decode())"
```

### Emergency Rollback

If the execution service encounters critical operational issues:

1. **Option A: Controlled 503 (Immediate Backpressure)**:
   Set `SPARQL_SERVICE_ENABLED=false` in `.env` and restart web:

   ```bash
   docker compose up -d web
   ```

   All `/api/sparql` requests fail fast with controlled HTTP 503 without consuming server resources.

2. **Option B: In-Process Fallback (Revert to 0.8.0 Process Isolation)**:
   Set `SPARQL_EXECUTION_MODE=in_process` in `.env` and restart web:

   ```bash
   docker compose up -d web
   ```

   The web worker executes queries using local process boundaries until the service issue is resolved.

## Observability & Incident Runbook

### OpenObserve Diagnostics (SQL)

Query SPARQL service execution logs:

```sql

SELECT _timestamp, correlation_id, log
FROM default
WHERE service_name = 'iqoqo-sparql-service'
ORDER BY _timestamp DESC
LIMIT 50
```

Query SPARQL timeouts and rejections:

```sql
SELECT _timestamp, correlation_id, log
FROM default
WHERE service_name = 'iqoqo-sparql-service' AND log LIKE '%error%'
ORDER BY _timestamp DESC
LIMIT 20
```

### Common Incidents

1. **HTTP 503 (Capacity Saturated)**:
   - *Symptom*: High query arrival rate saturating the queue (16 requests).
   - *Action*: Inspect client traffic pattern; advise clients to honour `Retry-After: 5`; adjust `MAX_CONCURRENT_QUERIES` if CPU capacity permits.

2. **HTTP 504 (Query Timeout)**:
   - *Symptom*: Adversarial query with Cartesian products.
   - *Resolution*: The engine kills the child process automatically via SIGTERM/SIGKILL. Verify worker replacement occurred without orphan processes (`docker top <container>`).

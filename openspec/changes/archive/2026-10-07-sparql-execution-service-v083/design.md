## Context

The 0.8.0 implementation isolates query evaluation in child processes, but the web API still owns graph materialization and serialization, and concurrency is effectively multiplied by each Gunicorn worker. The 0.8.3 design creates a separate internal execution boundary while preserving the public `/api/sparql` protocol, caller authorization, and private-data isolation.

## Goals / Non-Goals

**Goals:**

- Keep expensive SPARQL work from consuming API worker capacity.
- Enforce global queue, concurrency, CPU, memory, PID, graph, result, and deadline budgets.
- Preserve caller-scoped visibility without giving the worker broad database or application-secret access.
- Provide independently deployable health, metrics, tracing, restart, and rollback behavior.
- Keep the Explorer and existing protocol clients compatible.

**Non-Goals:**

- Introducing federated SPARQL or public unauthenticated query access.
- Replacing the RDF domain model or changing catalog visibility rules.
- Making Celery's existing thread-based worker the execution boundary.
- Selecting Fuseki or another persistent triple store in this change.

## Decisions

1. **Use a dedicated internal service/container.** The API remains the policy enforcement point. The service is reachable only on an internal network and accepts authenticated requests from the API.

2. **Transfer scoped graph snapshots, not user credentials.** The API authenticates, authorizes, and constructs a bounded public-plus-owner graph snapshot. The service receives a short-lived signed scope/job envelope and snapshot, never a JWT, database session, or write credential. This avoids duplicating tenant authorization in the worker.

3. **Use a bounded synchronous execution protocol first.** The API sends a request with correlation ID, deadline, snapshot metadata, query, and negotiated format. The service returns one bounded result or a typed failure. A bounded queue and fail-fast overload response prevent hidden backlog; asynchronous jobs are out of scope.

4. **Use killable worker processes inside the service.** A service supervisor starts isolated query workers with explicit lifecycle handling and replaces workers after timeout or resource failure. Warm workers may be evaluated only if they preserve hard cancellation and tenant cleanup guarantees.

5. **Apply defense in depth at the service boundary.** Container cgroups, non-root execution, read-only filesystem, dropped capabilities, restricted egress, no application secrets, input/result byte caps, and per-user/global admission controls all remain mandatory.

6. **Version the internal protocol.** Include protocol version, scope expiry, maximum sizes, deadline, correlation ID, and result type. The API maps service failures to existing 429/503/504/5xx contracts and can disable the service with a controlled 503 during rollback.

7. **Observe without collecting private content.** Expose readiness, active jobs, queue depth, timeouts, rejections, restarts, resource use, and latency. Logs and traces carry correlation IDs and bounded metadata only; query text and RDF values are redacted.

## Risks / Trade-offs

- [Snapshot transfer adds latency and memory copies] → Bound snapshot size, measure phase latency, and consider a shared read-only snapshot only after isolation tests.
- [Authorization context could be confused across tenants] → Use short-lived signed envelopes, random job IDs, explicit scope claims, no user-selected scope, and cross-user integration tests.
- [New service can become an availability dependency] → Provide readiness checks, bounded fail-fast behavior, restart policy, protocol-compatible rollback, and controlled 503 responses.
- [A separate container does not automatically stop DoS] → Enforce cgroup limits, queue/concurrency caps, output limits, and per-query process termination inside the service.
- [Operational complexity increases] → Add Compose/preview runbooks, service dashboards, health checks, and independent image rollback before production rollout.

## Migration Plan

1. Build and test the service behind a feature flag while the existing in-process executor remains available only for controlled rollback.
2. Deploy the service with no public port, least privilege, resource limits, and internal authentication.
3. Shadow or canary representative queries using sanitized snapshots; compare status, result shape, latency, privacy, and resource metrics.
4. Route the Explorer and API to the service after acceptance criteria pass; retain a controlled 503 switch, not a thread-executor fallback.
5. Remove web-worker-local SPARQL execution after a soak period and document the protocol, limits, dashboards, and rollback procedure.

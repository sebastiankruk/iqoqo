## Why

Per-query subprocess isolation is an appropriate 0.8.0 safety boundary, but it leaves graph materialization and resource accounting inside web workers and scales its concurrency limit per worker. For 0.8.3, SPARQL execution should move to a dedicated, least-privileged service so expensive or hostile queries cannot starve the main API and can be governed by independent CPU, memory, PID, queue, and observability controls.

## What Changes

- Introduce an internally authenticated SPARQL execution service with a bounded queue and explicit backpressure.
- Keep authentication and authorization in the main API and transfer only a bounded, caller-scoped graph snapshot or equivalent scoped execution request.
- Move graph materialization, query execution, cancellation, result limits, and worker replacement into the service.
- Apply dedicated container cgroup limits, non-root execution, restricted filesystem/network access, and no application-secret mounts.
- Define signed request scope, job lifecycle, timeout, cleanup, retry, and tenant-isolation contracts.
- Add service health, metrics, traces, structured failure responses, and production-like load/security tests.
- Preserve the `/api/sparql` protocol and SPARQL Explorer behavior for existing clients.

## Capabilities

### New Capabilities
- `semantic/sparql-execution-service`: Provides isolated, resource-governed SPARQL execution behind the authenticated API.

### Modified Capabilities
- `semantic/sparql-api`: Changes execution from web-worker-local processing to an internal isolated execution service while preserving protocol, authorization, privacy, and user-visible error contracts.
- `container-hardening`: Extends hardening requirements to the SPARQL worker/service container and its internal communication boundary.

## Impact

- New service image, deployment configuration, internal authentication, queue/IPC protocol, health checks, and observability.
- API adapter changes in `app/api/sparql.py` and removal or deprecation of web-worker-local query execution.
- Graph snapshot construction and privacy enforcement across API/service boundaries.
- CI, Compose, preview deployment, load testing, and operational runbooks.

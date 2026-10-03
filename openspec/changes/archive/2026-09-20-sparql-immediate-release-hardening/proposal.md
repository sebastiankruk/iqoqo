## Why

The 0.8.0 security review identified SPARQL runaway-query execution as a critical issue, so subprocess isolation must be retained. The current preview regression still returns HTTP 500 because graph serialization fails on unescaped cover URLs, while the process/IPC path has additional reliability and resource-boundary gaps that must be fixed before this release ships.

## What Changes

- Encode cover paths and other user-controlled URI components before RDF graph serialization.
- Convert graph-building and serialization failures into controlled SPARQL API responses rather than uncaught 500 errors.
- Retain killable subprocess execution; do not restore thread-based timeout handling.
- Replace unreliable queue-presence checks with deadline-aware IPC and explicit child exit/lifecycle handling.
- Enforce graph, result-row, result-triple, serialized-byte, concurrency, and complete-deadline limits.
- Add conservative Gunicorn and container resource limits without using deployment timeouts as query cancellation.
- Add regression, adversarial, multi-worker, and preview smoke tests for the SPARQL Explorer examples.

## Capabilities

### New Capabilities
- `semantic/sparql-release-hardening`: Provides bounded, cancellable, reliable SPARQL execution for the 0.8.0 release.

### Modified Capabilities
- `semantic/sparql-api`: Strengthens existing SPARQL reliability, timeout, resource-limit, error, and result-format requirements.

## Impact

- Backend RDF URI construction and graph serialization in `app/core/frbr_service.py` and `app/core/sparql_service.py`.
- SPARQL API error handling, IPC, process lifecycle, and output formatting.
- Gunicorn/Docker deployment resource configuration and operational telemetry.
- Backend, frontend, integration, adversarial, and preview smoke tests.

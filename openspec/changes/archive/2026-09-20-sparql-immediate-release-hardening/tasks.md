## 1. RDF Serialization Regression

- [x] 1.1 Normalize and encode cover URL/path components at every RDF URI construction site, then verify spaces, Unicode, reserved characters, relative paths, and malformed URLs are handled without graph serialization failure.
- [x] 1.2 Convert graph construction and serialization failures into stable SPARQL API error responses, then verify no uncaught Flask traceback is returned to clients.

## 2. Isolated Execution and Limits

- [x] 2.1 Introduce one explicit multiprocessing context and create matching IPC primitives, then verify valid queries execute under the production Python image and Gunicorn entrypoint.
- [x] 2.2 Replace `Queue.empty()` result detection with deadline-aware IPC, child exit-status handling, and terminate/join/kill cleanup, then verify successful, failed, timed-out, and child-crash cases leave no zombie processes.
- [x] 2.3 Enforce graph construction budgets, complete request deadlines, per-query concurrency admission, and result limits during SELECT/CONSTRUCT/DESCRIBE production, then verify adversarial queries remain bounded.
- [x] 2.4 Enforce serialized-byte limits for JSON, XML, CSV, Turtle, and other supported result formats, then verify each format returns a controlled limit response rather than accumulating unbounded output.

## 3. Deployment and Observability

- [x] 3.1 Configure conservative Gunicorn worker settings without preload or unnecessary threads and add web-container CPU, memory, and PID limits, then verify `docker compose config` and container startup succeed.
- [x] 3.2 Add structured SPARQL lifecycle metrics/logs for phase timing, graph/result sizes, child exit reasons, timeouts, and capacity rejection without query/private-data logging, then verify telemetry appears in preview-like execution.

## 4. Regression and Release Validation

- [x] 4.1 Add backend tests for all example queries, URI edge cases, IPC races, auth-scoped privacy, output formats, and limit enforcement, then verify the targeted SPARQL suite passes.
- [x] 4.2 Add frontend/E2E coverage for the custodian Administration menu and SPARQL Explorer example execution, then verify authorized users see the menu and receive results without 500 errors.
- [x] 4.3 Run full lint, backend, frontend, type-check, and production-like Compose tests, then verify zero unexpected SPARQL 500s and stable worker/child resource usage during the preview canary.

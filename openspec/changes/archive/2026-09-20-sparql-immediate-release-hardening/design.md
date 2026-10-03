## Context

The existing `/api/sparql` path authenticates the caller and builds a scoped in-memory RDF graph, but graph construction and serialization occur in the web worker before isolated query execution. The 0.8.0 review requires killable query work; therefore the design must retain subprocess isolation while correcting the preview failure and closing IPC, result-accumulation, and deployment-boundary gaps.

## Goals / Non-Goals

**Goals:**

- Make all valid SPARQL Explorer example queries work with real catalog data, including cover filenames containing reserved characters.
- Preserve cancellation and process isolation for runaway `rdflib` work.
- Bound every major memory, CPU, result, concurrency, and time budget.
- Return stable JSON errors for graph, child, IPC, timeout, and limit failures.
- Validate behavior in the preview-like Gunicorn/Docker deployment.

**Non-Goals:**

- Replacing rdflib or introducing a separate service in this release.
- Increasing Gunicorn concurrency as a substitute for query cancellation.
- Restoring `ThreadPoolExecutor` timeouts.
- Solving all future SPARQL query-planner limitations.

## Decisions

1. **Fix URI construction at the RDF boundary.** Encode URL path components before creating URI terms, while preserving already valid absolute URLs. Optional malformed cover relations are skipped with telemetry rather than aborting the whole graph.

2. **Use explicit, context-consistent process IPC.** Select and document the tested multiprocessing context for the deployment image, construct all IPC primitives from that context, and use a one-way pipe or deadline-aware receive instead of `Queue.empty()`. The parent will inspect child exit status and perform terminate, join, then kill cleanup.

3. **Apply limits during production.** Enforce item/triple/byte budgets while building the graph, cap SELECT bindings and graph results in the child before serialization, and apply output byte limits to every negotiated format. A post-hoc formatter cap is insufficient.

4. **Keep Gunicorn conservative.** Use explicit worker/resource settings, avoid preload and unnecessary worker threads, and configure container CPU, memory, and PID ceilings. Gunicorn's request timeout remains an outer watchdog, not the SPARQL cancellation mechanism.

5. **Fail closed and avoid sensitive logs.** Authentication and graph scoping remain in the API. Errors expose safe codes and messages; logs contain correlation IDs, phase durations, sizes, exit status, and reason, but not query text or private RDF values.

6. **Test the real failure boundary.** Add unit tests for URI normalization and IPC lifecycle, integration tests for all result formats and adversarial limits, and a Docker/Gunicorn smoke test that runs every Explorer example query.

## Risks / Trade-offs

- [Process startup latency] → Measure startup separately, retain a bounded five-second budget, and validate the selected context in the deployment image.
- [Parent-side graph work can still consume resources] → Add construction-time item/triple/byte budgets and a complete deadline; track dedicated-service migration in the 0.8.3 plan.
- [Multiple Gunicorn workers multiply child capacity] → Calculate the total budget across workers/replicas and use explicit admission limits plus container cgroups.
- [Malformed legacy cover URLs may lose an optional image triple] → Prefer a valid query response over failing the entire graph; emit a metric for data repair.
- [Changed error behavior may affect clients] → Preserve existing success content types and document stable 4xx/5xx error codes, then run frontend and API regression suites.

## Migration Plan

1. Deploy the URI and IPC/resource-limit changes behind the existing endpoint.
2. Run targeted tests, full backend/frontend tests, and preview-like Compose validation.
3. Canary on preview with normal, malformed, timeout, and concurrent queries while monitoring worker restarts, child PIDs, RSS, CPU, and 5xx responses.
4. Roll back the application image if validation fails; if necessary disable SPARQL with a controlled 503. Do not roll back to thread-based execution.

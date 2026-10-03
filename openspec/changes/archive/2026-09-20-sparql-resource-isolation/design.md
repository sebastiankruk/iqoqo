## Context

The current implementation materializes all visible catalog items into an in-memory graph and runs `rdflib` in a `ThreadPoolExecutor`. Python cannot preemptively kill a running thread, so `future.result(timeout=...)` is not a hard resource boundary.

## Goals / Non-Goals

**Goals:**

- Make timeout and memory limits enforceable under adversarial queries.
- Preserve authenticated graph scoping and existing SPARQL response formats.
- Keep the endpoint deployable in the current Flask/Gunicorn architecture.

**Non-Goals:**

- Introducing Fuseki or a persistent triple store in 0.8.x.
- Expanding query language features or enabling SPARQL Update.
- Changing permission names or private-item visibility semantics.

## Decisions

1. **Use an isolatable execution boundary.** Prefer a short-lived worker process or an equivalent cancellable backend over a thread timeout. The boundary must be killable when the deadline or resource budget is exceeded.
2. **Bound graph construction separately from query execution.** Apply a maximum item/triple budget and fail predictably when the authenticated graph cannot be materialized safely. Do not start the query deadline only after an unbounded graph build.
3. **Use parsed operation classification.** Parse the query into a read-operation representation before execution; retain regex only as a cheap early guard or remove it. Literals/comments must not affect operation classification.
4. **Make limits observable.** Return stable structured errors for timeout, graph-size, result-size, and concurrency rejection; log duration and limit reason without logging query contents or private data.
5. **Test the boundary as a process/resource contract.** Unit tests cover classification; integration tests cover repeated timeouts, concurrent requests, graph bounds, and worker survival.

## Risks / Trade-offs

- [Risk] A subprocess adds serialization and startup cost → reuse a bounded worker pool only if workers can still be terminated and reset safely.
- [Risk] Graph-size rejection may surprise large-library users → expose a clear error and document the supported query scope.
- [Risk] Parser behavior differs between read and update syntax → pin supported syntax through tests and preserve current client examples.

## Migration Plan

Deploy behind the existing endpoint and rate limiter. Roll back by disabling the new executor path, but do not restore the unbounded thread timeout in production; retain a conservative hard rejection fallback until the fix is redeployed.

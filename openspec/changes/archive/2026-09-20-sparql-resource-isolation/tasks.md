## 1. Execution boundary

- [x] 1.1 Choose and implement a killable query execution boundary with deadline propagation and cleanup, and verify a timed-out worker is terminated/reset.
- [x] 1.2 Add bounded graph-materialization budgets and bounded concurrent execution, and verify concurrent requests cannot exceed the configured budget.
- [x] 1.3 Enforce result/intermediate cardinality limits before unbounded materialization, and verify Cartesian queries are rejected or bounded.
- [x] 1.4 Preserve existing response formats and structured error status codes, and verify current protocol tests pass.

## 2. Query validation

- [x] 2.1 Replace regex-only update detection with operation-aware parsing and preserve safe literal/comment handling, and verify read queries containing update words remain accepted.
- [x] 2.2 Add tests for SELECT/ASK/CONSTRUCT/DESCRIBE, Update syntax, comments, literals, malformed queries, and encoded request input, and verify all classifications.

## 3. Verification and operations

- [x] 3.1 Add adversarial tests for Cartesian joins, repeated timeouts, concurrent requests, graph-size rejection, and result limits, and verify no leaked work remains.
- [x] 3.2 Add metrics/logging for query duration and rejection reason without query/private-data logging, and verify sensitive query text is absent from logs.
- [x] 3.3 Run SPARQL backend tests, full backend tests, and a worker-survival smoke test, and record successful results.

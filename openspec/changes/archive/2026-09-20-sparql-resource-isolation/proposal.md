## Why

The new SPARQL endpoint builds an unbounded in-memory graph for each request and uses a thread timeout that cannot stop an already-running `rdflib` query. A permitted user can therefore exhaust worker CPU or memory with expensive queries, making this a release-blocking availability risk.

## What Changes

- Replace non-cancellable in-process timeout handling with an execution boundary that can terminate runaway work.
- Bound graph materialization, query/result cardinality, intermediate resource use, and concurrent expensive executions.
- Keep authentication, owner/private-item isolation, read-only behavior, content negotiation, and existing API error contracts.
- Replace or strengthen regex-only update rejection with parsed operation validation and explicit tests for literals, comments, malformed updates, and read queries.
- Add adversarial tests for timeout termination, Cartesian joins, repeated timeouts, concurrency, and result truncation.

## Capabilities

### New Capabilities

### Modified Capabilities

- `semantic/sparql-api`: Strengthen read-only query execution so resource limits are enforceable and timeout handling cannot leave unbounded background work.

## Impact

- `app/core/sparql_service.py`, `app/api/sparql.py`, rate-limit/concurrency configuration, and SPARQL tests.
- Possible worker/process or bounded-store deployment configuration.
- API clients retain the current successful response formats and status-code semantics.

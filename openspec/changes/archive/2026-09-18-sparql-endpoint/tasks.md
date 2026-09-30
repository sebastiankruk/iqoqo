## 1. Core SPARQL Service

- [x] 1.1 Implement `build_graph()` in `app/core/sparql_service.py` to materialize an in-memory `rdflib.Graph` from catalog models, strictly filtering Item entities to public records and items owned by `user_id`. Verify with unit tests ensuring private items of other users are excluded from the graph.
- [x] 1.2 Implement `validate_query()` in `app/core/sparql_service.py` enforcing 10 KB maximum query length and rejecting SPARQL Update operations (such as INSERT, DELETE, LOAD, CLEAR, DROP, CREATE). Verify with unit tests rejecting mutating queries and oversized payloads with ValueError.
- [x] 1.3 Implement `execute_sparql()` in `app/core/sparql_service.py` with a 5-second execution timeout using a worker thread/future, returning serialized or structured query results. Verify with unit tests covering SELECT/ASK executions and timeout error handling.

## 2. SPARQL API Endpoint & Protocol Compliance

- [x] 2.1 Implement `app/api/sparql.py` handling GET and POST requests to `/api/sparql` supporting URL query parameters, `application/x-www-form-urlencoded`, and `application/sparql-query` request bodies. Verify endpoint accepts and parses all three input formats.
- [x] 2.2 Decorate `/api/sparql` with `@require_auth` and `@limiter.limit("10 per minute")`. Verify unauthenticated requests return 401 and rate limit exhaustion returns 429.
- [x] 2.3 Implement content negotiation in `app/api/sparql.py` returning SPARQL JSON (`application/sparql-results+json`), XML, CSV, and RDF Turtle according to the request `Accept` header. Verify responses match requested MIME types.
- [x] 2.4 Register the SPARQL router in `app/api/__init__.py` and verify endpoint URL mapping is present in Flask application routes.

## 3. Frontend Admin SPARQL Explorer

- [x] 3.1 Create `frontend/app/admin/sparql/page.tsx` with admin route protection, query textarea editor, execution status indicators, execution latency display, and preset query templates (e.g. all Works, Manifestations by format, recent Items). Verify page loads and renders in browser.
- [x] 3.2 Build dynamic tabular result view for SELECT queries with column headers, row counts, pagination, and raw format display for graph outputs. Verify table binds variables and values accurately.
- [x] 3.3 Implement client-side export utility allowing administrators to download SPARQL results as JSON or CSV files. Verify download button triggers file creation.

## 4. End-to-End Verification & Test Suite

- [x] 4.1 Implement automated backend test suite in `tests/test_sparql_api.py` validating authentication, rate limiting, query size guardrails, timeout abortion, auth scoping, and query formats. Verify all tests pass with `pytest tests/test_sparql_api.py`.
- [x] 4.2 Verify frontend types and linting for the admin SPARQL page pass without errors.

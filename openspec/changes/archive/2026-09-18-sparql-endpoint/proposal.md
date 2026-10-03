## Why

As part of milestone v0.8.0 (Linked Open Data & Semantic Web, deliverable C5), iqoqo requires a standardized, read-only SPARQL Protocol endpoint and an administrative query explorer. This enables programmatic semantic querying over the FRBR catalog graph while strictly preserving user privacy and preventing resource exhaustion.

## What Changes

- Expose a read-only SPARQL 1.1 Protocol endpoint at `/api/sparql` supporting both GET and POST requests.
- Protect the endpoint with `@require_auth` and rate limiting (10 queries per minute per user).
- Create `app/core/sparql_service.py` to manage auth-scoped RDF graph generation (`build_graph()`), query validation (`validate_query()`), and execution (`execute_sparql()`).
- Enforce strict guardrails: 5-second execution timeout, 10 KB maximum query string size, and read-only query enforcement (rejecting SPARQL UPDATE, LOAD, DROP, etc.).
- Build an auth-scoped graph excluding private user items, ensuring multi-tenant data privacy.
- Support standard SPARQL result formats (SPARQL JSON `application/sparql-results+json`, SPARQL XML, and CSV/TSV) as well as RDF serialization formats (Turtle, JSON-LD) for CONSTRUCT/DESCRIBE queries.
- Build an admin SPARQL explorer UI at `frontend/app/admin/sparql/page.tsx` featuring preset example queries, syntax-highlighted editor, tabular result viewer with pagination, and CSV/JSON download capabilities.

## Capabilities

### New Capabilities
- `semantic/sparql-api`: Expose read-only SPARQL Protocol endpoint (`/api/sparql`) with auth-scoped graph generation, execution timeouts, size limits, and interactive admin query explorer UI.

### Modified Capabilities

## Impact

- **Backend APIs**: New blueprint / router `app/api/sparql.py` registered under `/api/sparql`.
- **Backend Services**: New core module `app/core/sparql_service.py` encapsulating RDF graph generation and `rdflib` query execution.
- **Frontend**: New page at `frontend/app/admin/sparql/page.tsx` with query interface, example templates, result tables, and export features.
- **Security & Performance**: In-memory graph generation scoped to public and authorized user entities, 10 req/min rate limit, 5s query timeout, 10 KB query size ceiling.
- **Dependencies**: Uses existing `rdflib` dependency (no external triplestore infrastructure required for v0.8.x).

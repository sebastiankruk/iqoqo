## Context

See `proposal.md` for motivation and background.

iqoqo catalogs books, board games, vinyl records, and digital media using the FRBR hierarchy (Work → Expression → Manifestation → Item) stored in PostgreSQL schemas (`catalog`, `inventory`, `auth`). As part of v0.8.0 deliverable C5, iqoqo needs a standardized, read-only SPARQL 1.1 Protocol endpoint at `/api/sparql` and an administrative query explorer UI at `frontend/app/admin/sparql/page.tsx`.

The system already uses `rdflib` for ontology parsing and SHACL validation. This design defines the architecture for graph materialization, SPARQL query validation, execution with execution guardrails, rate limiting, and the frontend admin interface.

## Goals / Non-Goals

**Goals:**
- Implement `app/core/sparql_service.py` providing `build_graph()`, `validate_query()`, and `execute_sparql()`.
- Expose a read-only SPARQL 1.1 Protocol endpoint in `app/api/sparql.py` supporting GET and POST requests.
- Protect `/api/sparql` with `@require_auth` and `@limiter.limit("10 per minute")`.
- Enforce strict guardrails: reject mutating operations, enforce 10 KB query size limit, and terminate queries exceeding a 5-second timeout.
- Ensure data privacy by building auth-scoped graphs that exclude other users' private items and custody records.
- Support standard content negotiation: SPARQL JSON (`application/sparql-results+json`), XML, CSV, TSV for SELECT/ASK; Turtle and JSON-LD for CONSTRUCT/DESCRIBE.
- Implement `frontend/app/admin/sparql/page.tsx` with preset example queries, query editor, tabular results display, execution latency, and CSV/JSON download capabilities.

**Non-Goals:**
- External triplestore deployment (e.g. Apache Jena Fuseki, OpenLink Virtuoso, Blazegraph) — deferred beyond v0.8.x.
- SPARQL 1.1 Update operations (`INSERT`, `DELETE`, `LOAD`, `CLEAR`, `DROP`) — the endpoint is strictly read-only.
- Public unauthenticated SPARQL access — authentication is mandatory to prevent denial of service and resource exhaustion.
- Federated SPARQL queries (`SERVICE <iri> { ... }`) querying external semantic endpoints.

## Decisions

### 1. In-Memory `rdflib.Graph` over External Triplestore (ADR)
- **Decision**: Use in-memory `rdflib.Graph` constructed from the relational database for v0.8.x instead of deploying or requiring an external triplestore service.
- **Rationale**: iqoqo is designed as a lightweight, local-first personal and small-institution digital library. Requiring a separate triplestore daemon (such as Fuseki or Virtuoso) would substantially increase memory consumption (>1GB RAM) and operational overhead for self-hosters. In-memory `rdflib.Graph` materialization easily handles collections of tens of thousands of triples with sub-second response times.
- **Alternatives considered**:
  - *External Triplestore Sidecar (Fuseki / Virtuoso)*: Rejected due to resource footprint and synchronization complexity with PostgreSQL.
  - *SPARQL-to-SQL Transpilation (e.g. Ontop)*: Rejected due to extreme implementation complexity and tight coupling to SQL dialects.

### 2. Auth-Scoped Graph Construction (`build_graph`)
- **Decision**: Construct RDF graphs dynamically scoped to the authenticated caller's permissions. Public Works, Expressions, and Manifestations are included, while Item and Custody nodes are filtered to `(item.is_public == True) | (item.owner_id == user_id)`.
- **Rationale**: Filtering at graph construction guarantees that unauthorized data never enters the query evaluation space, eliminating any risk of inference or timing attacks against private items.
- **Alternatives considered**:
  - *Post-query result filtering*: Rejected because callers could deduce private data presence via boolean ASK queries or SPARQL FILTER clauses.

### 3. Read-Only Validation & Query Guardrails (`validate_query`)
- **Decision**: Validate query strings prior to execution:
  - Check query string length against a 10 KB ceiling (10,240 bytes).
  - Inspect query type and reject any SPARQL 1.1 Update keywords (`INSERT`, `DELETE`, `LOAD`, `CLEAR`, `CREATE`, `DROP`, `COPY`, `MOVE`, `ADD`, `WITH`).
  - Verify query parseability with `rdflib.plugins.sparql.parser.parseQuery`.
- **Rationale**: Prevents arbitrary mutations, catches syntax errors early, and prevents oversized payload attacks before graph evaluation.
- **Alternatives considered**:
  - *Regex-only keyword filtering*: Rejected as insufficient because keyword tokens could appear in string literals or comments. Combining keyword checks with parser validation ensures accurate rejection.

### 4. Query Execution Timeout (`execute_sparql`)
- **Decision**: Wrap `graph.query()` execution in a `concurrent.futures.ThreadPoolExecutor` with a strict 5-second timeout (`future.result(timeout=5)`). If the timeout expires, the thread is abandoned and an HTTP 504 Gateway Timeout error is returned.
- **Rationale**: SPARQL queries with complex joins or unbound graph patterns can trigger combinatorial explosions. A future-based timeout works consistently across platforms without signal limitations.
- **Alternatives considered**:
  - *UNIX `signal.alarm`*: Rejected because it only works on the main thread in POSIX environments and causes issues in multi-threaded WSGI workers.

### 5. Native Admin UI Explorer without Heavy External IDE Bundles
- **Decision**: Build `frontend/app/admin/sparql/page.tsx` using native React, Tailwind CSS, Lucide icons, and existing shadcn UI components (`Card`, `Button`, `Table`, `Select`), rather than importing Yasgui.
- **Rationale**: Yasgui adds >3MB to client bundles and frequently has SSR hydration conflicts with Next.js App Router. A tailored explorer provides clean UI consistency, preset query selection, responsive table rendering, and client-side CSV/JSON export with minimal code.
- **Alternatives considered**:
  - *Embedding YASGUI*: Rejected due to bundle size, styling mismatches, and SSR incompatibilities.

## Risks / Trade-offs

- **[Risk: Graph materialization latency on larger catalogs]** → **Mitigation**: Query SQLAlchemy models with eager loading (`selectinload`/`joinedload`) on core relations, and support optional in-memory caching of the public graph with TTL/invalidation on catalog writes.
- **[Risk: Runaway CPU consumption from malicious complex queries]** → **Mitigation**: Enforce 5-second execution timeout, 10 KB query length limit, and 10 queries/minute rate limiting per authenticated user.
- **[Risk: Sensitive error leakage in SPARQL exceptions]** → **Mitigation**: Catch RDFLib parsing and query execution exceptions and map them to clean HTTP 400/500 JSON error responses without stack traces.

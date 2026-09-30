## Context

See `proposal.md` and `specs/performance/optimizations-v082/spec.md` for business motivation and behavioral specifications.

As iqoqo catalogs scale toward tens of thousands of FRBR entities, several architectural and query patterns create database connection bottlenecks, query timeouts, and high server memory consumption:
1. **Manifestation offset pagination**: SQL `OFFSET` requires scanning and discarding $(N \times \text{limit})$ rows, and accompanying `.count()` calls trigger full-table sequential scans.
2. **Collection cycle detection**: Python `while`-loops traverse parent hierarchy chains with synchronous single-record queries ($N$ round trips per update).
3. **Faceted navigation ownership filters**: Multi-facet stats endpoints execute correlated `EXISTS` subqueries joining through `Item -> Manifestation -> Expression -> Work` repeatedly for each facet category.
4. **Admin export buffering**: Full catalog exports fetch all entities into Python memory before encoding via `BytesIO`, creating memory spikes proportional to catalog size.
5. **Filter fragmentation**: Dispersed filter assembly in `manifestations.py`, `items.py`, and `search_service.py` duplicates join tracking and creates query plan discrepancies.
6. **GET endpoint side effects**: `GET /api/isbn/<isbn>` persists new FRBR entities and spawns asynchronous Celery tasks on read requests, violating HTTP idempotency.

## Goals / Non-Goals

**Goals:**
- Provide stable, fast keyset cursor pagination on `GET /api/manifestations` while maintaining full backward compatibility for page/offset clients.
- Reduce collection hierarchy validation latency from $O(N)$ round-trips to $O(1)$ single-query execution using recursive CTEs.
- Accelerate ownership facet filtering via Redis caching and optimized set-based query construction.
- Bound memory consumption of `/admin/export` to $O(1)$ constant memory via chunked HTTP streaming.
- Unify multi-entity catalog filtering logic into an extensible `CatalogFilterBuilder`.
- Ensure `GET /api/isbn/<isbn>` is strictly read-only and idempotent.

**Non-Goals:**
- Replacing Elasticsearch/FTS full-text search indexes.
- Altering core FRBR entity schema relations (Work → Expression → Manifestation → Item).
- Modifying frontend state management architecture beyond consuming cursor tokens when present.

## Decisions

### Decision 1: Keyset Cursor Pagination for Manifestations
- **Approach**: Implement keyset cursor pagination using `(Manifestation.id)` as the monotonic sequence key. When `cursor` is provided, query adds `WHERE Manifestation.id < :cursor_id ORDER BY Manifestation.id DESC LIMIT :limit + 1`. The extra row determines `has_more` and provides `next_cursor` (opaque base64-encoded token containing `id`).
- **Rationale**: Keyset pagination eliminates offset row scans, executing with constant $O(1)$ index lookup latency regardless of page depth.
- **Alternatives Considered**:
  - *Standard OFFSET/LIMIT*: Scans all preceding rows, causing linear performance degradation.
  - *Window functions*: Adds execution overhead and still scans large table partitions.

### Decision 2: Recursive CTE for Hierarchy Cycle Detection
- **Approach**: Replace the iterative Python `while`-loop in `_validate_parent_hierarchy` with an ANSI-compliant recursive Common Table Expression (CTE) via SQLAlchemy `select().cte(recursive=True)` with a max depth guard (e.g. 50 levels).
- **Rationale**: A single recursive CTE evaluates the entire ancestor path inside the database engine in one query round trip, compatible with both PostgreSQL and SQLite.
- **Alternatives Considered**:
  - *Materialized Path / Closure Tables*: Requires new database tables and schema migrations, complicating collection updates.
  - *In-memory Python graph traversal*: Requires loading all user collections into memory.

### Decision 3: Redis Ownership Facet Query Optimization & Caching
- **Approach**:
  - Pre-filter owned manifestation IDs for authenticated users using efficient set queries rather than repeating correlated `EXISTS` subqueries across each facet group.
  - Cache computed facet stats in Redis with deterministic parameter ordering and automated invalidation on item mutations (`Item` create/delete/transfer).
- **Rationale**: Correlated subqueries across multi-level FRBR joins in 7 parallel facet calculations create severe database CPU load. Set-based pre-filtering and Redis caching reduce facet calculation time by >80%.
- **Alternatives Considered**:
  - *PostgreSQL Materialized View*: Requires background refresh cron/triggers and does not support SQLite in testing environments.

### Decision 4: Chunked Streaming for `/admin/export`
- **Approach**: Refactor `DataManager.export_all` into a chunked generator function that queries entities in batches using SQLAlchemy `yield_per(1000)`. Expose via Flask `Response(stream_with_context(generator), mimetype="application/json")` emitting formatted JSON structure incrementally.
- **Rationale**: Replaces in-memory list construction and `BytesIO` buffering with bounded constant memory usage ($O(1)$), allowing exports of arbitrary catalog size without out-of-memory worker crashes.
- **Alternatives Considered**:
  - *Asynchronous background file export*: Requires persistent storage management, download token lifecycle, and polling UI.

### Decision 5: Unified `CatalogFilterBuilder`
- **Approach**: Create `CatalogFilterBuilder` in `app/api/filters.py` that encapsulates query building and tracks joined tables (`joined_expression`, `joined_manifestation`, `joined_item`, `joined_tags`, etc.) across FRBR entities.
- **Rationale**: Prevents duplicate table joins, centralizes dialect-specific operations (PostgreSQL JSONB containment vs SQLite ILIKE fallback), and guarantees filter behavior consistency between listing and counting endpoints.
- **Alternatives Considered**:
  - *Ad-hoc filter helper functions*: Do not track join state, causing duplicate JOIN errors when combining multiple user facets.

### Decision 6: Pure Read-Only `GET /api/isbn/<isbn>`
- **Approach**:
  - Make `GET /api/isbn/<isbn>` strictly read-only: return existing manifestation metadata if present, or fetch external provider metadata and return JSON without saving to the database.
  - Remove entity creation (`Work`, `Expression`, `Manifestation`) and Celery cover task dispatching from `GET` handler.
  - Update internal callers (such as `POST /item/<isbn>` in `app/api/items.py`) to explicitly invoke `frbr_service` ingestion functions when saving is requested.
- **Rationale**: Enforces REST idempotency (RFC 9110), avoids unexpected database writes on crawler/read traffic, and prevents denial-of-service via arbitrary ISBN queries.
- **Alternatives Considered**:
  - *Query parameter flag (`?persist=false`)*: Violates HTTP GET specification guidelines regarding side effects.

## Risks / Trade-offs

- **[Risk] Keyset pagination does not provide arbitrary page jumping** → Keyset pagination allows next/prev traversal; keep existing offset pagination as a supported fallback when `page` query parameter is explicitly passed.
- **[Risk] Large user libraries could exceed Redis facet cache memory limits** → Apply strict TTLs (300 seconds), compress cached payloads, and scope keys to active user query combinations.
- **[Risk] Client disconnects during streaming export could leave hanging database cursors** → Use generator cleanup blocks (`finally:` clauses) within `stream_with_context` to guarantee database cursor closure upon client connection termination.
- **[Risk] Existing frontend callers expecting `GET /api/isbn/<isbn>` to auto-create manifestations** → Frontend item creation flows already post to `/item/<isbn>` or `/manifestations`; verify all frontend intake forms invoke explicit creation POST endpoints.

## Migration Plan

1. Deploy shared `CatalogFilterBuilder` and recursive CTE collection validation (zero schema changes, backward-compatible).
2. Deploy keyset cursor pagination to `app/api/manifestations.py` with backward-compatible offset fallback.
3. Deploy streaming export to `app/core/data_manager.py` and `app/api/system.py`.
4. Deploy pure read-only ISBN lookup, ensuring all ingestion endpoints explicitly perform persistence via `POST`.
5. Deploy Redis ownership facet optimization and verify facet response accuracy against test suite.

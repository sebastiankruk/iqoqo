## Why

Large catalog growth in iqoqo has exposed critical query bottlenecks, database connection contention, and memory exhaustion risks across FRBR hierarchy operations and catalog APIs (C16: Performance Optimizations in v0.8.2 addressing 20 MOD-API + 20 MOD-FRBR tech debt items). Deep offset pagination on manifestations causes high-latency table scans, iterative Python loops for hierarchy validation cause N-round-trip latency, correlated ownership subqueries degrade faceted navigation stats, full-dataset buffering in `/admin/export` threatens out-of-memory crashes, duplicated query-building logic increases maintenance overhead, and HTTP GET requests mutating entity state violate REST architectural principles.

## What Changes

- **Cursor-based pagination for manifestations**: Introduce keyset cursor pagination (`cursor`, `limit`, `next_cursor`) on `GET /api/manifestations` as a high-performance alternative to deep SQL `OFFSET` pagination, maintaining backward-compatible page/limit support.
- **Recursive CTE for hierarchy traversal**: Replace Python `while`-loop sequential queries in collection hierarchy validation (`_validate_parent_hierarchy`) and lineage lookups with single recursive Common Table Expressions (CTE) compatible with PostgreSQL and SQLite.
- **Ownership facet query caching**: Introduce caching and optimized query generation in Redis for user collection ownership facets (`owned`, `not_owned`) within `GET /api/stats/facets` and catalog filters.
- **Streaming `/admin/export`**: Refactor `DataManager.export_all()` and `GET /admin/export` from full in-memory list construction and `BytesIO` serialization to chunked generator streaming (`stream_with_context`) with bounded memory footprint ($O(1)$ space complexity).
- **Extract shared filter builder**: Extract catalog filtering logic (format, content-type, tags, collections, genres, publishers, statuses, missing flags, ownership) from `app/api/manifestations.py`, `app/api/items.py`, and `app/core/search_service.py` into a reusable, dialect-aware `CatalogFilterBuilder`.
- **Fix REST violation (GET with side effects)**: Refactor `GET /api/isbn/<isbn>` to be strictly idempotent and read-only; eliminate automatic creation and mutation of `Work`, `Expression`, and `Manifestation` records on GET requests, reserving mutations for explicit `POST` endpoints.

## Capabilities

### New Capabilities
- `performance/optimizations-v082`: Comprehensive performance optimizations covering cursor pagination, recursive CTE hierarchy traversal, ownership facet query caching, streaming data export, unified catalog filter construction, and idempotent read-only REST APIs.

### Modified Capabilities
<!-- None: core FRBR ontology entity models and existing API contracts remain compatible; this introduces the dedicated v0.8.2 performance optimization capability -->

## Impact

- **Database**: Lower query count and latency via recursive CTEs, eliminated deep offset scans via keyset cursor pagination, and reduced correlated subquery overhead on facet calculation.
- **Backend APIs & Core Modules**:
  - `app/api/manifestations.py`: Keyset cursor pagination support; removal of side effects in `lookup_isbn`; integration of shared filter builder.
  - `app/api/collections.py`: Recursive CTE hierarchy validation.
  - `app/api/system.py` & `app/core/data_manager.py`: Generator-based streaming export for `/admin/export`; cached ownership facet calculation.
  - `app/api/filters.py`: Shared `CatalogFilterBuilder` extracting duplicate filter construction across endpoints.
  - `app/api/items.py`: Adoption of shared filter builder and adjustment of ISBN creation invocation to avoid side-effect reliance.
- **Dependencies**: No external dependency additions required; leverages existing SQLAlchemy recursive CTE constructs, Redis cache infrastructure, and Flask streaming utilities.

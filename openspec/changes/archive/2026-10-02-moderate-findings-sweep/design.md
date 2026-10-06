## Context

See `proposal.md` for problem motivation and scope.

The repository accumulated ~99 moderate findings during the v0.7.18 architectural review across four distinct technical areas:
- **MOD-DBM**: Database schema definition and Alembic migration integrity, including non-indexed foreign keys, unvalidated hierarchical collections, fragile migration scripts, and missing idempotency guards.
- **MOD-EXT**: External integration resilience, including unconstrained subprocess executions (rclone), DNS thread leaks, stale User-Agents, slow local LLM vision inference timeouts, and N+1 query patterns in maintenance scripts.
- **MOD-FE_UI**: Frontend user interface architecture, accessibility, state synchronization, client-side rendering bottlenecks on entity pages, unescaped JSON-LD structured data, and layout shifts.
- **MOD-TEST**: Testing infrastructure, notably slow test runs caused by per-test table recreation in `conftest.py`, repeated disk I/O for SHACL shape parsing, regex-based TypeScript parsing, ambiguous assertions, and exposed test state reset routes.

Prior changes (C12 Security, C13 Frontend Architecture, C16 Performance, C17 DevOps) handled major targeted initiatives. This change (C18) systematically sweeps the remaining moderate findings to ensure release v0.8.2 stability.

## Goals / Non-Goals

**Goals:**
- Resolve all remaining `MOD-DBM` (21 items), `MOD-EXT` (19 items), `MOD-FE_UI` (25 items), and `MOD-TEST` (20 items) findings.
- Introduce application-layer cycle detection for hierarchical collections (`UserCollection.parent_id`).
- Ensure all foreign keys are explicitly indexed (`Item.manifestation_id`, `ReadingRoadmap.user_id`).
- Guarantee idempotent execution across historical and maintenance Alembic migrations.
- Wrap external subprocesses and HTTP integrations in strict timeout and pool-bounded boundaries.
- Introduce a centralized external metadata key normalizer mapping vendor responses to canonical snake_case.
- Optimize batch maintenance scripts by introducing eager loading (`joinedload`/`selectinload`) and chunked commits.
- Migrate entity detail routes (`manifestation/[id]`, `item/[id]`) to Server Components with safely escaped JSON-LD structured data.
- Transition test suites from per-test `create_all`/`drop_all` schema churn to session-level schema creation with savepoint/nested transaction rollbacks.
- Cache SHACL validation shapes and tighten ambiguous test assertions across backend and frontend suites.

**Non-Goals:**
- Modifying core FRBR hierarchy invariants (Work → Expression → Manifestation → Item).
- Introducing ActivityPub federation or Apache Fuseki (explicitly deferred to v0.9.0+).
- Rewriting the entire frontend into Server Components beyond the targeted entity detail pages and public profile routes.
- Migrating to new third-party testing frameworks (pytest and Vitest remain standard).

## Decisions

### 1. Hierarchical Collection Cycle Detection (`MOD-DBM-01`)
- **Choice**: Implement validation hook on `UserCollection` in `app/db/core.py` (via `@validates("parent_id")`) and verify against an iterative ancestor lookup or recursive CTE query.
- **Rationale**: Prevents infinite loops during collection tree traversals at write time rather than relying on query-time recursion depth limits.
- **Alternatives Considered**: Database-level recursive check constraint or trigger. Rejected because triggers introduce cross-dialect divergence between PostgreSQL and SQLite.

### 2. Foreign Key Indexing and Schema Constraints (`MOD-DBM-02, 04, 05`)
- **Choice**:
  - Add explicit `index=True` to `Item.manifestation_id` in `app/db/core.py` and `ReadingRoadmap.user_id` in `app/db/roadmap.py`.
  - Add `nullable=False` to `ContainerAggregation.quantity` in `app/db/games.py`.
  - Document and verify `extend_existing=True` in `LoanRequest.__table_args__` (`app/db/lending.py`), removing it if table redefinition is no longer needed.
- **Rationale**: Foreign key columns without explicit indexes degrade JOIN and CASCADE DELETE performance in PostgreSQL.

### 3. Alembic Migration Idempotency and Schema Discipline (`MOD-DBM-08..23`)
- **Choice**:
  - Update `alembic/env.py` to derive `allowed_schemas` dynamically from `target_metadata` / app configuration.
  - Wrap constraint drops and table operations in `op.get_bind()` dialect checks and `sa.engine.reflection.Inspector` existence checks (`has_table`, `get_foreign_keys`).
  - Add deduplication checks to bulk insert operations (`20260818`).
  - Split large migrations (e.g. `52b02a37b16b`) where feasible into atomic migration operations or sequential functions.
  - Fix Polish stop-word regex in `e3f891ab45c2` (remove `ten|ta|to` demonstrative pronouns from the article strip list).
  - Verify data presence in partitioned schemas before executing drop statements in `drop_stale_public_tables.py`.
- **Rationale**: Migrations must run predictably on fresh dev instances, SQLite test fixtures, and production PostgreSQL without manual hotfixes.

### 4. Subprocess Isolation and HTTP Client Resiliency (`MOD-EXT-01, 04, 06, 09`)
- **Choice**:
  - Enforce `timeout=30` and `capture_output=True` on all `subprocess.run(["rclone", ...])` calls in `app/api/feedback.py` and `app/utils/images.py`.
  - In `app/utils/http_client.py`, replace dynamic per-request DNS resolver threads with a module-level bounded thread pool (`ThreadPoolExecutor(max_workers=8)`).
  - Increase Ollama vision model timeout in `app/utils/vision.py` to 90 seconds and relax response JSON regex to `re.search(r"\{.*\}", raw, re.DOTALL)`.
  - Update HTTP User-Agents in `app/utils/musicbrainz.py` and `app/utils/bgg.py` to use dynamic `Config.VERSION`.
- **Rationale**: Eliminates zombie threads, prevents API worker starvation on network stalls, and accommodates local LLM vision inference latencies.

### 5. Strategy Ingestion Normalization & Maintenance Script Optimization (`MOD-EXT-11..19`)
- **Choice**:
  - Introduce `normalize_metadata_keys()` in `app/utils/normalizer.py` (or `app/strategies/`) converting provider-specific camelCase or custom keys (TMDB, Discogs, BGG, IGDB, Google Books) to uniform snake_case.
  - Decompose `process_cover_pipeline` in `app/utils/covers.py` into discrete tier strategies (`LocalDiskStrategy`, `CloudRcloneStrategy`, `AIImageStrategy`).
  - Refactor scripts (`fetch_covers.py`, `generate_ai_covers.py`, `retry_missing_covers.py`, `update_bgg_mechanics.py`) with `selectinload` / `joinedload` on relationships and commit transactions in chunks of 100 rows.
  - Add archive file integrity validation (`tar -tzf` or `zipfile.is_zipfile`) in `scripts/import_covers.sh`.
- **Rationale**: Eliminates N+1 database roundtrips that cause script timeouts on large libraries and provides unified data shapes to the frontend scanner.

### 6. Server Components and Entity Route Sanitization (`MOD-FE_UI-30, 31, 32, 34`)
- **Choice**:
  - Refactor `manifestation/[id]/page.tsx` and `item/[id]/page.tsx` to Server Components fetching data server-side via direct backend service or server-side fetch.
  - Sanitize JSON-LD structured data by escaping `<script>` and `</script>` tags (replacing `<` with `\u003c`) inside the JSON string before rendering.
  - Update `u/[username]/page.tsx` to parallelize user profile and items queries with `Promise.all` and implement cursor-based pagination.
  - Implement atomic item + cover creation in `scan/page.tsx` using `multipart/form-data` submitted to a unified endpoint.
- **Rationale**: Accelerates First Contentful Paint (FCP), improves SEO indexing for public entities, eliminates XSS attack vectors in structured data, and avoids orphaned images on item creation failures.

### 7. Frontend UI De-clutter and State Synchronization (`MOD-FE_UI-03..29, 35..37`)
- **Choice**:
  - Decompose `item-sidebar.tsx` into modular child components (`LendingDialog`, `CollectionManager`, `StatusSelects`).
  - Extract collection URL query parameters synchronization into `useCollectionURLSync` custom hook (`collection/page.tsx`).
  - Replace `return null` with skeleton layouts in `GlobalStats` (`global-stats.tsx`) to prevent Cumulative Layout Shift (CLS).
  - Add `AbortController` signal cancellation to search inputs in user management (`user-management.tsx`).
  - Replace native `fetch` with `apiClient` in `check-inventory.tsx`.
  - Fix hydration mismatch in `admin/settings/page.tsx` by using `NEXT_PUBLIC_APP_URL` rather than `window.location.host`.
- **Rationale**: Improves UI responsiveness, avoids layout instability, and eliminates duplicate or stale asynchronous requests.

### 8. Session-Scoped Database Rollbacks & SHACL Caching (`MOD-TEST-04, 05, 06, 10..20`)
- **Choice**:
  - Refactor `tests/conftest.py`: run `db.create_all()` once at session startup; each test function runs inside a nested transaction (savepoint) that rolls back after test completion (`session.rollback()`).
  - Cache parsed SHACL shapes in `tests/test_ontology_shacl.py` across test functions.
  - In `tests/test_ontology.py`, extract TypeScript interface properties using code generation / AST parsing rather than line-based regexes.
  - Tighten test assertions: change status assertions from `in (400, 404)` to `== 400`, verify exact boolean set logic in multi-tag facet tests (`test_api_facets.py`), and fix lint safeguard regexes.
  - Guard `reset_lending_test_state` in `app/api/lending.py` with an explicit test environment check (`Config.TESTING is True` and mandatory secret token).
- **Rationale**: Decreases backend test execution time by 5-10x, eliminates flaky test interdependencies, and prevents accidental test resets in staging/production.

## Risks / Trade-offs

- **[Risk] Migration changes could conflict with existing deployed database heads**  
  → *Mitigation:* Ensure migration modifications are purely additive idempotency checks (`IF NOT EXISTS`, inspection checks) and do not alter existing revision identifiers or linear chains.

- **[Risk] Session-scoped test fixtures could leak state across tests if transactions commit**  
  → *Mitigation:* Wrap test sessions in a connection-level transaction that intercepts `commit()` calls using SQLAlchemy's nested transaction savepoints (`connection.begin_nested()`).

- **[Risk] Converting Next.js pages to Server Components may break client-side interactive widgets**  
  → *Mitigation:* Keep interactive sections (edit buttons, modals, dropdowns) as client components (`"use client"`) embedded within the server-rendered page skeleton.

- **[Risk] Normalizing external metadata to snake_case could break existing client consumers expecting camelCase**  
  → *Mitigation:* Provide bidirectional compatibility mapping in the serializer layer during the transition window.

## Migration Plan

1. **Database & Schema Updates**:
   - Run Alembic migration check: verify all historical migrations execute cleanly on empty SQLite and PostgreSQL databases.
   - Deploy model changes (`UserCollection`, `Item`, `ReadingRoadmap`, `ContainerAggregation`).
2. **Backend Services & Scripts**:
   - Update `http_client.py`, `covers.py`, `images.py`, `normalizer.py`.
   - Update maintenance scripts and verify performance with sample catalog data.
3. **Frontend Components**:
   - Deploy Server Components updates, unescaped JSON-LD fixes, and UI refactorings.
   - Verify zero hydration errors in browser console.
4. **Test Infrastructure**:
   - Update `conftest.py` transaction rollback fixtures.
   - Run complete test suite (`make test`) verifying execution time improvements and assertion pass rate.
5. **Rollback Strategy**:
   - All schema additions are backward-compatible; reverting backend application code restores previous behavior without requiring database downgrades.

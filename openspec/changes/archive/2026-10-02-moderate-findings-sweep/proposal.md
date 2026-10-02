## Why

Following core semantic web deliverables and major targeted refactorings (C12, C13, C16, C17), the repository contains ~99 remaining moderate findings from the v0.7.18 architectural review across database migrations, external integrations, frontend user experience, and test fixtures. Addressing these remaining findings in v0.8.2 stabilizes the platform, prevents data integrity issues, optimizes background scripts and test execution speed, and hardens user interfaces before the v0.9.0 release.

## What Changes

- **Database & Migrations (`MOD-DBM`, 21 items)**:
  - Add cycle detection for hierarchical collections (`UserCollection.parent_id`) to prevent infinite recursion.
  - Verify and add explicit indexing on foreign keys (`Item.manifestation_id`, `ReadingRoadmap.user_id`).
  - Strengthen schema integrity: enforce non-null quantities (`ContainerAggregation.quantity`), document/remove `extend_existing` on `LoanRequest`, optimize `update_frbr_type()` cascade updates, and validate incoming data structures in `import_data()`.
  - Fix migration bugs and externalize schema discovery: derive `allowed_schemas` dynamically in `alembic/env.py`, fix SQLite execution branch in `20260331_frbr_catalog_schema.py`, eliminate swallowed errors in identity fix downgrades, and make schema migrations idempotent (`b7ad7843fb4a`, `20260818`, `23db780ad6d1`).
  - Prune redundant migration steps (`27a510181d97`, `20260814`), ensure deterministic column ordering in `consolidate_schemas.py`, verify pre-migration data preservation in `drop_stale_public_tables.py`, split monolithic lending migrations, correct Polish article stop-word regex, and document schema relocation breaking changes (`f65648a6aaf4`).

- **External Integrations & Script Hardening (`MOD-EXT`, 19 items)**:
  - Add execution timeouts and subprocess capture hardening across rclone invocations (`app/api/feedback.py`, `app/utils/images.py`).
  - Fix DNS thread leaks via a bounded module-level thread pool in `http_client.py`.
  - Resilient external provider handling: update stale User-Agents with `Config.VERSION`, relax fragile regexes and expand timeouts (90s+) for local Ollama vision inference, and eliminate circular imports in boardgame strategies.
  - Decompose image pipeline utilities: deduplicate text overlay helpers, shared watermark logic, and decompose `process_cover_pipeline` into distinct tier strategies.
  - Standardize external ingestion payload schemas via snake_case normalization across TMDB, Discogs, BGG, IGDB, and Google Books.
  - Eliminate N+1 query loops and batch database commits in maintenance scripts (`fetch_covers.py`, `generate_ai_covers.py`, `retry_missing_covers.py`, `update_bgg_mechanics.py`, `restore_covers.py`) and validate archive payloads in `import_covers.sh`.

- **Frontend UI & Accessibility (`MOD-FE_UI`, 25 items)**:
  - Migrate entity detail routes (`manifestation/[id]`, `item/[id]`) toward Next.js Server Components with structured SEO and HTML entity escaping for JSON-LD.
  - Add cursor-based pagination and parallel data fetching (`Promise.all`) to public user profiles (`u/[username]`).
  - Improve form and state UX: atomic item + cover creation using multipart form submission, prevent duplicate escalation submissions, add AbortController cancellation to user search, fix modal state synchronization, and replace ad-hoc fetch with standardized `apiClient`.
  - Fix UI layout shifts and error messaging: replace `return null` with skeleton states in `GlobalStats`, add toast notifications to catch blocks in roadmap views, and eliminate dead dialog state.
  - Decompose large complex UI components: extract `item-sidebar.tsx` into modular sub-dialogs, extract media classification logic into hooks, and clean up inline JSON formatting.
  - Resolve hydration mismatches in settings and remove aggressive search auto-selection in content editors.

- **Test Harness Hardening & Coverage (`MOD-TEST`, 20 items)**:
  - Optimize test fixture performance: replace per-test `db.create_all()` / `db.drop_all()` teardowns in `conftest.py` with session-scoped schema initialization and transaction rollback savepoints.
  - Session-cache parsed SHACL shapes and RDF graphs in `test_ontology_shacl.py` to eliminate redundant disk I/O.
  - Replace brittle regex-based TypeScript file parsing in `test_ontology.py` with AST or code-generation extraction.
  - Strengthen assertions: eliminate ambiguous status codes (e.g., `in (400, 404)` -> `400`), tighten multi-tag AND/OR filter assertions, harden dynamic status scans, and fix regex suppression bypasses in lint safeguard tests.
  - Replace source inspection (`inspect.getsource`) with behavioral tests, simplify multi-assert permission tests in `test_covers.py`, tighten frontend ARIA live region assertions, and use direct module imports instead of inline mocking.
  - Secure testing endpoints: harden the test reset endpoint guard (`reset_lending_test_state`) against accidental execution in production configurations.

## Capabilities

### New Capabilities
- `operations/findings-sweep-v082`: Comprehensive sweep addressing the remaining ~99 moderate findings across database schemas and migrations (MOD-DBM), external integration scripts and timeouts (MOD-EXT), frontend UX and Server Components (MOD-FE_UI), and test suite performance and assertions (MOD-TEST).

### Modified Capabilities
<!-- None: addresses accumulated technical debt across existing implementations without redefining core functional capabilities. -->

## Impact

- **Database & Models**: `app/db/` models updated with cycle detection validation, explicit foreign key indexes, non-null constraints, and sanitized migration scripts under `migrations/versions/`.
- **Backend Integrations & Scripts**: `app/utils/` (HTTP client, image pipeline, LLM covers), `app/strategies/`, and `scripts/` updated with timeout limits, batched queries, and payload normalizers.
- **Frontend**: `frontend/app/` (entity pages, user profiles, settings) and `frontend/components/` (sidebar, modals, collection views) updated for Server Components, toast alerts, and responsive accessibility.
- **Testing**: `tests/conftest.py` and unit/integration test suites significantly accelerated through session-scoped schema rollback fixtures, hardened assertions, and cached SHACL shapes.

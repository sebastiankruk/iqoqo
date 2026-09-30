## 1. Database Schema, Models & Migration Idempotency (MOD-DBM)

- [ ] 1.1 Implement application-layer cycle detection in `app/db/core.py` for `UserCollection.parent_id` (MOD-DBM-01), verifying with unit test preventing cyclical parent assignment
- [ ] 1.2 Add explicit `index=True` on `Item.manifestation_id` in `app/db/core.py` and `ReadingRoadmap.user_id` in `app/db/roadmap.py` (MOD-DBM-02, MOD-DBM-04), verifying indexes in model metadata
- [ ] 1.3 Audit and document/remove `extend_existing=True` in `LoanRequest.__table_args__` (`app/db/lending.py:63-68`) and set `nullable=False` on `ContainerAggregation.quantity` (`app/db/games.py:59`) (MOD-DBM-03, MOD-DBM-05), verifying model definitions
- [ ] 1.4 Optimize `update_frbr_type()` cascade updates in `app/core/frbr_service.py:1075` using bulk UPDATE query (MOD-DBM-06), verifying with FRBR type update unit tests
- [ ] 1.5 Add validation for field lengths, enum values, types, and foreign key references in `data_manager.py:146` `import_data()` (MOD-DBM-07), verifying with invalid import payload test
- [ ] 1.6 Fix out-of-band schema mutation in `scripts/fix_alembic.py:88` and externalize `allowed_schemas` in `alembic/env.py` dynamically from metadata (MOD-DBM-08, MOD-DBM-09), verifying script and env execution
- [ ] 1.7 Fix `20260331_frbr_catalog_schema.py` SQLite execution branch and remove swallowed errors (`except Exception`) in identity downgrades (`9ed9e764c2b0`, `ca691f79cb37`) (MOD-DBM-10, MOD-DBM-11), verifying migration upgrade and downgrade on SQLite
- [ ] 1.8 Refactor `52b02a37b16b_add_lending_tables.py` into discrete atomic sub-operations and make downgrades deterministic for `51a5cbb508f8` and `9f5598cf6467` (MOD-DBM-12, MOD-DBM-13), verifying migration execution
- [ ] 1.9 Fix column ordering non-determinism in `consolidate_schemas.py` and add pre-drop data verification check to `drop_stale_public_tables.py` (MOD-DBM-14, MOD-DBM-15), verifying script output
- [ ] 1.10 Prune redundant migrations `27a510181d97` and `20260814`, and add idempotency guards to constraint drops in `b7ad7843fb4a` and bulk inserts in `20260818` (MOD-DBM-16, MOD-DBM-17, MOD-DBM-18, MOD-DBM-19), verifying re-running migration on seeded DB succeeds
- [ ] 1.11 Fix schema placement and add idempotency to `23db780ad6d1` (`reading_roadmaps` in `inventory`), fix Polish article stop-word regex in `e3f891ab45c2`, and document schema relocation in `f65648a6aaf4` (MOD-DBM-20, MOD-DBM-21, MOD-DBM-22, MOD-DBM-23), verifying migration execution and Polish title indexing

## 2. External Integration, Subprocess & Maintenance Script Resilience (MOD-EXT)

- [ ] 2.1 Add 30-second timeout and capture_output to all `subprocess.run(["rclone", ...])` invocations in `app/api/feedback.py:160` and `app/utils/images.py:128` (MOD-EXT-01, MOD-EXT-06), verifying with subprocess mock tests
- [ ] 2.2 Eliminate circular imports in `app/strategies/boardgame.py:44,63` and flatten nested conditionals in `app/strategies/default.py:60-89` (MOD-EXT-02, MOD-EXT-03), verifying strategy imports and UPC fallback tests
- [ ] 2.3 Fix DNS thread leak in `app/utils/http_client.py:59` using a bounded module-level ThreadPoolExecutor (MOD-EXT-04), verifying client connection cleanup under concurrency
- [ ] 2.4 Deduplicate text overlay helper functions (`images.py:136-386`) and watermark helpers (`llm_covers.py:394-483`) (MOD-EXT-05, MOD-EXT-10), verifying image generation and watermark tests
- [ ] 2.5 Update User-Agents in `app/utils/musicbrainz.py:65` and `app/utils/bgg.py:41` to include `Config.VERSION` (MOD-EXT-07), verifying outgoing headers
- [ ] 2.6 Increase Ollama timeout to 90s in `app/utils/vision.py:192` and replace brittle JSON regex with `re.search(r"\{.*\}", raw, re.DOTALL)` at line 262 (MOD-EXT-08, MOD-EXT-09), verifying vision response parsing tests
- [ ] 2.7 Decompose `process_cover_pipeline` in `app/utils/covers.py:401-546` into distinct strategy tiers (MOD-EXT-11), verifying cover processing pipeline tests
- [ ] 2.8 Create centralized external API metadata key normalizer mapping TMDB, Discogs, BGG, IGDB, Google Books keys to consistent snake_case (MOD-EXT-12), verifying normalizer unit tests
- [ ] 2.9 Fix N+1 query patterns and add batched commits to maintenance scripts: `fetch_covers.py:56`, `generate_ai_covers.py:89,111,148,160`, `retry_missing_covers.py:74`, `update_bgg_mechanics.py:62`, and multi-attribute matching in `restore_covers.py:57` (MOD-EXT-13, MOD-EXT-14, MOD-EXT-15, MOD-EXT-16, MOD-EXT-18, MOD-EXT-19), verifying scripts with mock database queries
- [ ] 2.10 Add archive content validation before extraction in `scripts/import_covers.sh:40` (MOD-EXT-17), verifying error handling on corrupt archives

## 3. Frontend Server Components, Accessibility & State (MOD-FE_UI)

- [ ] 3.1 Migrate entity detail pages `manifestation/[id]/page.tsx` and `item/[id]/page.tsx` to Next.js Server Components with server-side data fetching and metadata generation (MOD-FE_UI-34), verifying SSR page load and SEO tags
- [ ] 3.2 Sanitize and escape JSON-LD output in `manifestation/[id]/page.tsx:141` to prevent script tag breakout (MOD-FE_UI-30), verifying script tag escaping test
- [ ] 3.3 Add cursor-based pagination and parallelize profile + items data fetching with `Promise.all` in `u/[username]/page.tsx` (MOD-FE_UI-31, MOD-FE_UI-32), verifying profile rendering and page navigation
- [ ] 3.4 Implement atomic item + cover creation using multipart form submission in `scan/page.tsx:153-175` (MOD-FE_UI-33), verifying single-transaction item upload
- [ ] 3.5 Extract `useCollectionURLSync` hook in `collection/page.tsx:236-278` and replace native `confirm()` with shadcn AlertDialog in `manage-collections-modal.tsx:217` (MOD-FE_UI-35, MOD-FE_UI-07), verifying collection URL filtering and modal behavior
- [ ] 3.6 Fix hydration mismatch in `admin/settings/page.tsx:360` by replacing `window.location.host` with environment variable, and remove search auto-selection in `admin/content/page.tsx:350-355` (MOD-FE_UI-36, MOD-FE_UI-37), verifying hydration clean console
- [ ] 3.7 Replace `return null` with skeleton layout in `global-stats.tsx:32` to prevent layout shift, and clean up dead modal state and logout error handling in `navbar.tsx` (MOD-FE_UI-03, MOD-FE_UI-04, MOD-FE_UI-05), verifying visual skeleton rendering
- [ ] 3.8 Fix multi-status data loss and state reset in `share-collection-dialog.tsx`, and add persistence/clarify display in `reading-roadmap.tsx` with error toasts in `roadmap-view.tsx` (MOD-FE_UI-08, MOD-FE_UI-09, MOD-FE_UI-10, MOD-FE_UI-11), verifying dialog state and roadmap toast alerts
- [ ] 3.9 Extract `useMediaClassification` hook from `item-card.tsx` and decompose `item-sidebar.tsx` into modular sub-dialogs (MOD-FE_UI-12, MOD-FE_UI-18), verifying item card and sidebar rendering
- [ ] 3.10 Remove case-variant fallback chains across item display components, clean up object stringification in `item-header.tsx:200`, and replace hiddenKeys blacklist in `extended-metadata.tsx` with backend-provided metadata separation (MOD-FE_UI-14, MOD-FE_UI-19, MOD-FE_UI-20), verifying component rendering
- [ ] 3.11 Add exponential backoff to polling in `item-actions.tsx` and `camera-capture.tsx`, escape HTML in `qrcode-dialog.tsx`, and use `apiClient` in `check-inventory.tsx` (MOD-FE_UI-15, MOD-FE_UI-16, MOD-FE_UI-17, MOD-FE_UI-29), verifying polling backoff and sanitized QR print
- [ ] 3.12 Add toast notifications, shadcn Dialog conversions, AbortController search cancellation, and PNG preservation in admin components (`group-management.tsx`, `rbac-sheet.tsx`, `user-management.tsx`, `cover-editor/info-sidebar.tsx`) and prevent duplicate escalation submissions (MOD-FE_UI-22, MOD-FE_UI-23, MOD-FE_UI-24, MOD-FE_UI-25, MOD-FE_UI-26, MOD-FE_UI-27, MOD-FE_UI-28), verifying admin management interactions

## 4. Testing Infrastructure Performance & Assertion Hardening (MOD-TEST)

- [ ] 4.1 Harden test reset endpoint guard in `app/api/lending.py:241` by enforcing testing-only configuration and shared secret verification (MOD-TEST-01), verifying unauthenticated / production requests are rejected
- [ ] 4.2 Add test coverage for `expression_id` in escalation link generators (`frontend/__tests__/lib/escalation-utils.test.tsx`) (MOD-TEST-02), verifying Vitest test execution
- [ ] 4.3 Refactor `tests/conftest.py` to use session-scoped `db.create_all()` with per-test transaction rollback savepoints instead of per-test schema recreation (MOD-TEST-04), verifying test suite execution speedup
- [ ] 4.4 Session-cache parsed SHACL shapes and RDF graphs in `tests/test_ontology_shacl.py` (MOD-TEST-06), verifying fast repeated SHACL test execution
- [ ] 4.5 Replace regex TypeScript parsing in `tests/test_ontology.py` with code generation / AST inspection (MOD-TEST-05), verifying ontology parity test pass
- [ ] 4.6 Add negative auth tests in `tests/test_auth.py` for password complexity, brute-force rate-limiting, and timing attack resistance (MOD-TEST-07), verifying auth security test passes
- [ ] 4.7 Tighten assertions across backend suites: explicit user email in `test_search.py`, Item-level type propagation in `test_frbr_type_change.py`, real config parsing in `test_db_pool_config.py`, and exact status `== 400` in `test_expression_kind.py` (MOD-TEST-08, MOD-TEST-09, MOD-TEST-10, MOD-TEST-11), verifying backend test passes
- [ ] 4.8 Consolidate conflicting multi-tag filter logic between `tests/test_api_facets.py` and `tests/test_api_status_filters.py` to assert strict AND logic (MOD-TEST-12, MOD-TEST-13), verifying facet test pass
- [ ] 4.9 Tighten weak status assertion in `test_payload_validation.py:226` and fix regex bypass in `test_lint_safeguards.py` for comma-separated directives (MOD-TEST-14, MOD-TEST-15), verifying security test passes
- [ ] 4.10 Replace `inspect.getsource` checks and no-ops in `test_cover_cleanup.py` with behavioral tests, and simplify permission tests in `test_covers.py` (MOD-TEST-16, MOD-TEST-17, MOD-TEST-18), verifying cover test passes
- [ ] 4.11 Tighten frontend test assertions: hard ARIA live region assertions in `facet-a11y-live-region.test.tsx` and import actual masking function in `mask.test.ts` (MOD-TEST-19, MOD-TEST-20), verifying Vitest suite passes
- [ ] 4.12 Deprecate `scripts/test_docker_builds.sh` by aliasing to `build_docker_images.sh` (MOD-TEST-03), verifying script execution

## 5. Verification & Quality Gates

- [ ] 5.1 Run complete backend linting and test suite with `IQOQO_AI_MODE=1 make lint && make test` to verify zero regressions
- [ ] 5.2 Run complete frontend test and typecheck suite with `npm --prefix frontend run test && npm --prefix frontend run typecheck`
- [ ] 5.3 Verify database migration chain from clean base to head on both SQLite and PostgreSQL

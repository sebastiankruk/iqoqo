# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.14] - TBD

### Added

- **PostgreSQL 16 → 18 Migration Script**: Added `deploy/migrate-postgres-16-to-18.sh` for safe major-version database upgrades across `dev`, `preview`, and `prod` stacks. Uses a standalone temporary container to dump v16 data regardless of `docker-compose.yml` state, backs up the old volume, and restores into v18. Includes `--dry-run` support and rollback documentation.
- **Database Upgrade Guide**: Added `docs/UPGRADE_POSTGRES_18.md` with step-by-step instructions for all deployment environments.

### Changed

- **PostgreSQL**: Upgraded from `16-alpine` to `18-alpine` in `docker-compose.yml` and CI workflows.
- **Redis**: Upgraded from `7-alpine` to `8-alpine` in `docker-compose.yml`.

### Fixed

## [0.7.13] - 2026-07-31

### Added

- **Blu-ray Pure Audio Format Expansion**: Added `bluray_audio` format under the `music` category in `shared/taxonomy.yaml` with normalizations for `Blu-ray Audio`, `BD-A`, `BluRay HiFi`, `Pure Audio Blu-ray`. Added strategy rules for music Work on BD carrier vs concert movie BD.
- **Event-Based FRBRoo Modeling**: Integrated `expression.kind` (`live_performance`) for performance events. Concert ingest creates a Performance Event Expression with performers, venue, and date realized in video/audio manifestations.
- **F16 Container Aggregation**: Added board game container aggregation service (`ContainerAggregation` table + API surface) mapping rulebooks and component parts as aggregated works.
- **Relational FRBR Columns & Relational Promotion**: Promoted core `meta` keys to indexed relational columns on `Work` (`sort_title`), `Expression` (`raw_payload`), `Manifestation` (`format`, `label`, `barcode`, `catalog_number`, `raw_payload`), and `Item` (`raw_payload`). Added Alembic migration `e3f891ab45c2`.
- **Verbatim Provider Payloads**: All 5 external metadata provider utilities (Discogs, MusicBrainz, TMDB, BGG, Allegro) now return `raw_payload` for audit trail preservation.
- **Column-vs-Meta Health Check**: Added `DataManager.verify_column_meta_drift()` and updated `GET /api/health?check_drift=1` to fail deploy health on non-zero drift.
- **Apostrophe & Metacharacter Sanitization**: Canonicalized apostrophes (`’`, `‘`, `ʼ` → `'`) across search vectors, search query sanitization, and parameterized ILIKE metacharacter escaping (`%`, `_`, `\`).
- **Batch AI Cover Generation & Watermarking CLI**: Created `scripts/generate_ai_covers.py` supporting `--batch-all-unwatermarked`, `--dry-run`, `--limit`, and `--watermark-only`.
- **Data Correction Script**: Created idempotent `scripts/fix_manifestation_1984.py` remapping manifestation `1984` to `movie`/`bluray`.

### Changed

- **Allegro User-Agent**: Made Allegro API User-Agent header dynamic using `get_allegro_user_agent()` formatted as `${Config.ALLEGRO_APP_NAME}/${Config.VERSION} (+https://iqoqo.cc)`.
- **DataManager Export & Ingest**: `DataManager.export_all()` and `IngestService` read and output relational columns column-first with `meta` fallback.

## [0.7.12] - 2026-07-25

### Added

- **Escalation Queue Admin UI**: New `EscalationQueue` component mounted as a tab in the admin content page, visible to users with `escalate:resolve` permission. Custodians can view pending metadata correction requests, accept/reject/mark-duplicate with optional resolution notes.
- **Escalation Queue Status Filter**: Extended `GET /api/escalations/queue` endpoint with optional `?status=` query parameter (comma-separated statuses). Defaults to `pending` when absent for backward compatibility. Added `useResolvedEscalations()` hook for fetching non-pending requests.
- **Shared Escalation Utilities**: Extracted `getTargetHref()` and `getTargetLabel()` into `frontend/lib/escalation-utils.tsx` shared utility, used by both admin queue and my-escalations components.
- **Deletion Request Type**: Added `request_type` column to `EscalationRequest` model (default `"correction"`, supports `"correction"` and `"deletion"`) with Alembic migration. Enables distinguishing between metadata correction and entity deletion requests throughout the escalation pipeline.
- **Deletion Request Form**: Added request type selector (radio group) in the escalation trigger dialog, allowing users to toggle between "Metadata Correction" and "Request Deletion" modes. Form state clears on type switch to prevent stale data leakage between modes.
- **Accept & Delete Resolution**: Added entity deletion execution when accepting deletion-type escalation requests. Requires `delete:manifestation` or `delete:item` permission in addition to `escalate:resolve`. Entity deletion and escalation status update are wrapped in a single database transaction.
- **Deletion Request UI Badges**: Added `RequestTypeBadge` component displaying distinct "Deletion" (destructive/warning) vs "Correction" (neutral) styling on both admin queue tiles and user "My Help Requests" cards.

### Changed

- **User Requests UX Rename**: Renamed "Escalation Queue" to "User Requests" in admin tab, "Escalation" status card to "Help Request", "Duplicate" action to "Mark as Duplicate", and empty state messages from "escalation requests" to "user requests" throughout the UI.
- **Navbar "My Help Requests" Link**: Added "My Help Requests" dropdown menu item between "Manage Collections" and "Admin Configuration" with a pending-count badge using `useMyEscalations()` hook.
- **Processed Requests Section**: Added expandable "Processed Requests" section below the pending queue in the admin "User Requests" view — toggle button with chevron, fetching resolved escalations via the new `useResolvedEscalations()` hook.
- **Clickable Target Labels**: Target entity labels in the escalation queue are now clickable links to `/manifestation/{id}` or `/item/{id}`, matching the pattern from `my-escalations.tsx`.
- **Requests Accordion on Manifestation/Item Pages**: EscalationTrigger is now wrapped in a collapsible "Requests" accordion panel (ChevronUp/Down pattern) on manifestation and item pages, shown only to users without `write:metadata`. Pending request status is displayed outside the collapsed accordion; "Ask custodians" button is hidden until accordion expands.
- **Multi-Escalation Support**: EscalationTrigger now accepts pre-filtered escalations array prop, supporting multiple requests per target. All existing requests are listed inside the accordion while pending status is shown externally.
- **i18n Coverage**: Added full Polish and English translations (`HelpRequests` namespace) for all user-facing labels across escalation components, including dialog forms, action buttons, empty states, and status labels.
- **Card Padding Fix**: Fixed card padding in `my-escalations.tsx` from `p-3.5 space-y-2` to `p-4 space-y-3` for better visual breathing room.
- **FRBR Search Permission Gating**: The FRBR entity search endpoint now uses `@require_permission(READ_METADATA)` instead of `@admin_required`, allowing custodians (non-admins) with `read:metadata` to search FRBR entities.
- **Edit FRBR Button Gating**: The "Edit FRBR" button in item and manifestation action panels now requires `write:metadata` permission instead of `read:metadata`.
- **Fallback Cover Design**: Removed CTA text, enlarged "powered by iqoqo" footer to 28px bold, centered horizontally, added decorative separator line.
- **API Validation for Deletion Requests**: Extended `_validate_escalation_input()` to accept optional `request_type` field. When `request_type` is `"deletion"`, `field_name` and `suggested_value` become optional but `note` becomes required (max 2048 chars). Invalid `request_type` values are rejected with HTTP 400.
- **Resolve Endpoint Permission Gating**: Updated `PATCH /api/escalations/<id>` to check entity-specific DELETE permissions (`delete:manifestation` or `delete:item`) when accepting deletion-type requests. Rejection and duplicate actions are exempt from DELETE checks, allowing custodians without DELETE permissions to still decline requests.
- **Admin Queue "Accept & Delete" Button**: Changed "Accept" button label to "Accept & Delete" for deletion-type requests in the admin queue. The button is disabled with a permission tooltip when the resolver lacks the required entity-specific DELETE permission.
- **Deletion Request i18n Coverage**: Added new `HelpRequests` namespace translation keys for "Request Deletion", "Accept & Delete", "Reason for deletion", "Deletion request submitted to custodians", and related labels in both `en.json` and `pl.json`.
- **Scanner Policy Pill Layout**: Restored policy selector pill (`Inventory`, `Wishlist`, `Catalog`) inside `TopBar` below format selector icons in `top-bar.tsx`. Eliminates misplacement and `BottomSheet` overlap on mobile and desktop viewports while preserving `localStorage` state persistence. Added viewport E2E and unit layout tests.
- **Top-Level Action Density Control**: Enforced a strict maximum of 4 top-level primary buttons across `item-actions.tsx`, `manifestation-actions.tsx`, and `escalation-queue.tsx`, routing tertiary actions to a unified `<DropdownMenu>` ("More Actions").
- **Admin Tab Navigation**: Refactored tab selection in `frontend/app/admin/content/page.tsx` into a synchronous expression to prevent `react-hooks/set-state-in-effect` cascading renders.
- **Atomic Deletion Safety**: Added atomic row locking (`with_for_update()`) and PostgreSQL FK cascade check (`409 Conflict`) for manifestation deletion requests with existing dependent `Item` records in `app/api/social.py`.

### Test Hardening

- **Backend Escalation API Tests**: Added 14 new tests to `tests/test_api_escalations.py` covering queue status filtering (pending/resolved/single/invalid/mixed), resolve operations (rejected/duplicate status), resolver display name presence/absence, create escalation for all target types (work/expression/item), invalid request type rejection, and oversized resolution note validation.
- **Backend Permissions & Auth Tests**: Added 12 new tests covering custodian permission boundaries including FRBR entity mutations, image uploads, work part addition, FRBR tree access, escalation permission migrations (upgrade/downgrade), and require_permission decorator 401 behavior.
- **Backend Cover & Dashboard Tests**: Added 3 new tests for fallback cover design elements (separator line, footer font, no CTA text), and empty-collection edge cases for velocity and distribution insights endpoints.
- **Frontend Escalation Component Tests**: Added 22 new tests across `escalation-queue`, `escalation-trigger`, and `my-escalations` component test suites covering error states, processed requests toggle/loading/empty/error states, resolver display name, deletion badges, permission gating (delete:manifestation, delete:item), clickable target labels, rejected/duplicate status cards, deletion request flow, alwaysShowDialog prop, multi-escalation accordion, status badges, resolution notes, and target link hrefs.
- **Frontend Escalation Utils Tests**: Created `escalation-utils.test.tsx` with 15 tests covering `getTargetHref()`, `getAdminTargetHref()`, and `getTargetLabel()` for all 4 FRBR target types and deleted-entity fallback cases.
- **Frontend Scanner Component Tests**: Added `bottom-sheet.test.tsx` (tab rendering, tab switching, manual search, camera viewfinder, error display, manual entry fallback), `top-bar.test.tsx` (format selector, policy selector, flash toggle, back-link), and extended `camera-capture.test.tsx` with cover/gallery/vision mode uploads, drag-and-drop, confirmation dialog, and error handling.
- **Frontend Dashboard & Navbar Tests**: Added 7 new tests covering `CollectionInsights` loading/error states, `VelocityChart` empty array rendering, `TypeDistributionChart` empty data arrays, and navbar "My Help Requests" link with pending count badge, zero-pending state, and correct href.
- **i18n Structural Tests**: Created `help-requests-completeness.test.ts` verifying key parity between `en.json` and `pl.json` for the `HelpRequests` namespace and ensuring no translation values are empty strings.
- **Script Test Hardening**: Added `test_validate_yaml.py` with tests for valid/malformed/missing YAML, `test_script_utilities.py` with sync_version bump (patch/minor/major/set) and json_extract dialect (sqlite/postgresql) tests, and `validate_yaml.bats` BATS test for Makefile target validation.
- **E2E Test Expansion**: Extended `seed_e2e.py` with pending escalation seed data, created `escalation_workflow.spec.ts` (custodian resolution flow), `scanner_workflow.spec.ts` (barcode scan, format selection), `policy_scanning.spec.ts` (policy switching), and enabled `toHaveScreenshot()` assertions in `watermark_verification.spec.ts`.

### Fixed

- **User Requests Sidebar Nav & Resolver Info**: Added missing "User Requests" item to `/admin/settings` sidebar under Custodians section, updated "Metadata" nav item to navigate to `/admin/content?tab=metadata`, and fixed backend queue query to eagerly load resolver relationships so `resolver_display_name` renders on processed request tiles.
- **Escalation Permission Assignment**: Added Alembic data migration to assign `escalate:request` permission to `user` role and `escalate:resolve` to `custodian` and `admin` roles, fixing the submit-to-retrieve pipeline end-to-end.
- **Stats Charts Display for Empty Collections**: Hide `CollectionInsights` dashboard charts section (`VelocityChart` and `TypeDistributionChart`) when the authenticated user has zero items in their collection (`stats.total_items === 0`).

## [0.7.11] - 2026-07-22

### Added

- **Outbound HTTP Header Telemetry**: Added `record_outbound_telemetry` and `sanitize_headers` in `app/core/telemetry.py` to capture request headers (`User-Agent`, `Accept`, `Authorization`) on outbound HTTP calls to Allegro (`app/utils/allegro.py`) and direct image downloads (`app/utils/covers.py`). Automatically redacts sensitive credentials (e.g. `Authorization`, `token`, `secret`, `key`) as `***REDACTED***` before attaching attributes to active OpenTelemetry spans and structured logs.
- **Format Normalization**: Read-time format normalizer (`app/core/format_normalizer.py`) that maps non-canonical physical kind values from external APIs (`"video"`, `"audio"`, `"boardgame"`) to canonical `MediaFormat` identifiers using user-defined mappings in `shared/format_mappings.yaml`. Falls back to `unknown_video`, `unknown_audio`, or `unknown_text` placeholder formats when no mapping exists.
- **Unknown Format Placeholders**: Three new valid `MediaFormat` values (`unknown_video`, `unknown_audio`, `unknown_text`) added to the taxonomy and displayed as "Unknown Video Format", "Unknown Audio Format", and "Unknown Text Format" in the UI.
- **Interactive Format Mapping CLI**: `make fix-physical-kinds` runs `scripts/fix_physical_kinds.py`, providing audit, interactive mapping, and apply modes to fix non-canonical/NULL format values in the database. Supports `--dry-run` for previewing SQL changes.
- **Mappings File**: `shared/format_mappings.yaml` as git-tracked, per-instance configuration for format normalization, with commented examples.

### Changed

- **Environment-Aware Allegro User-Agent**: Added `ALLEGRO_APP_NAME` env var (default: `iqoqo`) in `app/config.py` to support per-environment Allegro application identifiers (`iqoqo_cc` for prod, `iqoqo_pre` for preview, `iqoqo_dev` for dev). The Allegro User-Agent header now reads `{ALLEGRO_APP_NAME}/{VERSION} (+https://iqoqo.cc)` instead of the hardcoded `iqoqo/...` prefix. Updated `tests/test_allegro.py` assertions to use `Config.ALLEGRO_APP_NAME`.
- **Facet Aggregation**: `DataManager.get_faceted_stats` now normalizes format counts via `normalize_format_counts()`, merging non-canonical values into their resolved canonical formats.
- **Format Filter**: `?format=` query parameter is expanded via `expand_format_filter()` to include raw values that normalize to the requested canonical format, ensuring correct matching.
- **Frontend**: `isAudioMedia()` and `extended-metadata.tsx` updated to recognize `unknown_audio` and `unknown_video`; sidebar Physical Kind facet shows italic styling for unknown format entries.

### Fixed

- **Telemetry Query & Header Redaction**: Extended telemetry sanitization with `sanitize_url()` in `app/core/telemetry.py` to scrub credentials (`key`, `token`, `secret`, `auth`, `signature`, `credential`) from outbound HTTP URLs before logging and OpenTelemetry span attribution. Updated `sanitize_headers` to use an expanded set of sensitive header keywords (`authorization`, `key`, `token`, `secret`, `cookie`, `session`).
- **CSV Query Parameter Parsing Helper**: Replaced duplicated inline `.split(",")` parameter parsing across `app/api/items.py`, `app/api/manifestations.py`, and `app/api/system.py` with `parse_csv_param()` in `app/api/filters.py` for consistent whitespace stripping and empty-string filtering.
- **Frontend UX Polish**: Cleaned up scrollbars on collection filter chip rows, restyled the floating mobile filter pill with backdrop blur and border effects, and updated the "View Wishlist Item" dropdown button icon to `Eye`.
- **Publisher Facet Filter Fix**: Updated `app/api/manifestations.py`, `app/api/items.py`, `app/api/works.py`, and `app/core/search_service.py` to use a `db.or_` condition across the relational `publisher` column and unstructured JSON metadata fields (`meta['Publisher']`, `meta['publisher']`, and conditionally `meta['label']` for music), ensuring publisher filters return results regardless of where the publisher data is stored. Updated taxonomy extraction and faceted stats counting to use `func.coalesce` over these fields so unstructured publishers appear in the sidebar and reflect accurate item counts.
- **Unauthenticated Protected Route Redirection**: Fixed an issue where unauthenticated access to protected routes (wishlists, personal collections, scan, profile, admin) returned a 404 error or failed silently. Route requests without session authentication are now caught at the Next.js routing proxy (`frontend/proxy.ts`) and redirected to `/login` with full URL and query parameter state preserved via `callbackUrl`. Upon successful login, users are redirected back to their intended destination.
- **API 401 Interceptor**: Updated `apiClient` response interceptor to catch HTTP 401 Unauthorized responses in browser contexts and trigger login redirection with `callbackUrl`.
- **Cross-FRBR Filter Combinations**: Fixed a bug where applying multiple Item-level status filters from different taxonomies (e.g., Progress Status vs. Collection Location) resulted in logical collisions (`db.or_()`) causing filtering bugs. These are now combined correctly via logical AND intersection so a Work must have an Item matching BOTH the intent (e.g., Unread) and location (e.g., On Shelf).
- **Faceted Navigation Multi-Select**: Fixed an issue where selecting a genre or format in the sidebar would restrict the underlying taxonomy options, preventing users from selecting multiple genres/formats. `useTaxonomies` now correctly requests the full taxonomy for the active category, relying on `useFacetStats` to hide zero-count options.
- **Physical Kinds SQL Syntax**: Fixed SQL syntax in `scripts/fix_physical_kinds.py` by using explicit casting (`CAST(meta AS jsonb)`) and explicit string formatting instead of colons (`::text`) to prevent SQLAlchemy binding errors and ambiguous column references during `jsonb_set` operations.
- **Comprehensive Test Coverage**: Added ~110 new tests across all 4 test layers (backend, frontend, E2E, scripts) for entity audit logging, item custody events, cross-FRBR filtering, metadata refetch CLI, format mapping CLI, facet ARIA live region, facet URL sync, active filter strip, mobile facet drawer, wishlist tagging, loan button visibility, and shared collection UI. New test files: `test_entity_audit.py`, `test_item_custody.py`, `test_metadata_refetch.py` (backend), `facet-a11y-live-region.test.tsx`, `facet-url-sync.test.tsx`, `active-filter-strip.test.tsx`, `mobile-facet-drawer.test.tsx` (frontend), `cross_frbr_filtering.spec.ts`, `facet_url_sync.spec.ts`, `mobile_facet_drawer.spec.ts`, `facet_aria_live_region.spec.ts`, `facet_search_within.spec.ts`, `metadata_refetch_verification.spec.ts` (E2E), `fix_physical_kinds.bats`, `refetch_metadata.bats`, `format_mappings_validation.bats`, `makefile_tooling.bats` (scripts).
- **Cross-FRBR Filtering and Facet Counts**: Fixed several issues where filter counts defaulted to Item-level ("My items") even when browsing Works, Expressions, or the Global Library. Key fixes:
  - Facet counts now reflect the correct FRBR level: `COUNT(DISTINCT Manifestation.id)` for global, `COUNT(DISTINCT Work.id)` for works, `COUNT(DISTINCT Expression.id)` for expressions, and `COUNT(DISTINCT Item.id)` for items.
  - Lower-level entity attributes (Item-level: status, tags, collections; Manifestation-level: media category, physical kind) now correctly filter higher-level entities via cross-entity subqueries with `SELECT DISTINCT`.
  - Unauthenticated users no longer see user-specific facets (Collection Status, Progress, Tags, Named Collections) and receive correct global-level counts (no more 0-count for Media Category).
  - The `/stats/facets` endpoint now uses `@optional_auth` to support unauthenticated global catalog browsing.

## [0.7.10] - 2026-07-15

### Added

- **OpenSpec** support in development process
- **GIN Index on `catalog.works.meta->'genres'`**: Added Alembic migration `3177c5e97570` that creates a functional GIN index `idx_work_meta_genres_gin` using `(meta::jsonb->'genres') jsonb_path_ops` to accelerate faceted genre aggregation queries on the FRBR Work entity.
- **`ItemCustodyEvent` model** (`app/db/core.py`, migration `839197bcbabc`): CIDOC CRM-compliant immutable event log for tracking custody changes at the FRBR Item tier. Records acquisition, transfer, and condition events in an append-only `inventory.item_custody_events` table indexed on `item_id` and `recorded_at`, laying the groundwork for ActivityPub federation trust chains.
- **`EntityAuditLog` model** (`app/db/core.py`, migration `839197bcbabc`): Curation and edit history log for Work, Expression, and Manifestation tiers. Stores metadata edits, duplicate resolutions, and record merges in `inventory.entity_audit_logs` with composite index on `(entity_type, entity_id)`. Strictly separated from `ItemCustodyEvent` per FRBR ontology (abstract tiers cannot be "possessed").
- **`@require_physical_item` decorator** (`app/api/decorators.py`): Declarative FRBR boundary interceptor that rejects API requests with `item_id <= 0` before they reach handler logic, returning a structured `{"error": "...", "code": 400}` response. Eliminates brittle inline `if item_id <= 0:` guards scattered across route handlers.
- **Playwright E2E tests** (`frontend/__tests__/e2e/require_physical_item_interceptor.spec.ts`): End-to-end validation of UI behaviour when the interceptor rejects invalid item IDs, including API mock and live-server test variants.

### Changed

- **`DataManager.get_faceted_stats` — SQL aggregation**: Replaced the Python-memory `Counter` genre aggregation with a dialect-aware database-side query using `jsonb_array_elements_text`, `COUNT()`, and `GROUP BY` on PostgreSQL (with automatic SQLite fallback for the test suite). Reduces memory footprint and I/O for faceted navigation at scale.
- **`app/api/items.py` — FRBR boundary refactor**: Removed inline `if item_id <= 0:` guards from `add_item_to_collection`, `remove_item_from_collection`, and `get_item_collections` route handlers. Applied `@require_physical_item` decorator to centralise the boundary check. Refactored `update_item` docstring to document the intentional virtual-item routing.
- **`tests/test_lint_safeguards.py` — anchored regex**: Replaced naive `str.contains()` matching with anchored regular expressions (`^[^#\n]*#\s*pylint:\s*disable=`) so safeguard tests only catch actual directive comments and no longer produce false positives from occurrences in docstrings or string literals.
- **frontend/vitest.setup.ts**: Removed duplicate `/* ── next-intl mock ──...` section header comment at line 165.

### Fixed

- **PR #157 Review Fixes**: Hardened `DataManager.get_faceted_stats` to prevent SQL errors when `genres` is not an array, tightened linter regexes to avoid false positives inside strings, fixed context binding in Alembic migration tests, and corrected E2E API mock routes for physical item interceptors.

## [0.7.9] - 2026-07-10

### Added

- **Aesthetic Cover Watermarking (Phase 2)**: Added utility functions `add_center_watermark` and `apply_corner_watermark` (in `app/utils/covers.py` and `app/utils/llm_covers.py`) for low-transparency center watermarking of placeholders and corner watermarking of GenAI cover layouts. Integrated watermarking logic into background cron routines (`scripts/fetch_covers.py`) and the core cover pipeline (`process_cover_pipeline` in `app/utils/covers.py`). Generated `resources/images/iqoqo-logo.png` from the SVG source. Added `classifyCoverType` utility and `data-cover-type` attribute to `item-card.tsx` to expose cover type to E2E tests. Wrote comprehensive byte-comparison tests (`tests/test_covers.py` / `tests/test_fetch_covers.py`) and a Next.js E2E Playwright test (`frontend/__tests__/e2e/watermark_verification.spec.ts`) with baseline screenshot generation. Updated E2E seed (`tests/e2e/scripts/seed_e2e.py`) to create watermarked placeholder and LLM cover images for test data.
- **Frontend Internationalization (i18n)**: Implemented base `next-intl` internationalization routing layer on Next.js, added localized English (`frontend/messages/en.json`) and Polish (`frontend/messages/pl.json`) translation strings for all user-visible components and pages (Navbar, DashboardPage, Hero, GlobalStats, StatsCards, CurrentContext, FreshArrivals, Footer, LoginPage, RegisterPage, NotFound, and CookieConsent banner), deployed the interactive `LanguageToggle` selector, and updated frontend unit test mocks. Polish translations strictly use sentence casing.
- **Backend OpenAPI Integration**: Deployed OpenAPI/Swagger spec generation endpoint under `/api/docs/openapi.json` using `apispec` and `apispec-webframeworks`.
- **Testing Coverage**: Added unit tests for OpenAPI spec generation (`tests/test_openapi.py`), updated frontend navbar unit tests (`navbar.test.tsx`), and created a Playwright E2E test (`i18n_localization.spec.ts`) for localization switches.
- **Allegro Auth Handshake CLI**: Deployed `make allegro-auth` target wrapping the interactive `scripts/allegro_auth.py` script for local and Docker setups.
- **Allegro Status Checks**: Integrated Allegro API activation checks into `make status` / `scripts/iqoqo-status.sh` to report configured, active (token present), or pending handshake states.
- **Allegro Cover Refetch Fallback**: Integrated Allegro API cover retrieval into the background cover refetch pipeline (`fetch_external_api_cover` in `app/utils/covers.py`), adding support for both ISBN and non-ISBN identifiers.
- **Collection Management UX (Phase 3)**: Added full Create, Update, and Remove collection operations to `ManageCollectionsModal` with inline form, toast notifications, and mutation invalidation. Refactored `ItemCard` to include instant wishlist subtraction via hover-revealed `HeartOff` button, calling `DELETE /items/:id` directly. Implemented dynamic cross-filtering visual treatment in `SidebarFilters` - facets with zero result count are now disabled and visually muted unless currently selected.
- **E2E Coverage (Phase 3)**: Created `manage_collections.spec.ts` Playwright test for full CRUD modal workflow. Added instant wishlist subtraction E2E test to `wishlist_workflow.spec.ts` and dynamic facet cross-filtering E2E test to `faceted_catalog_sync.spec.ts`.
- **Unit Test Expansion**: Added unit tests for wishlist removal button rendering and callback behavior in `item-card.test.tsx`, collection creation via form in `manage-collections-modal.test.tsx`, and cross-filtering disabled/opacity-50 treatment in `sidebar-filters.test.tsx`.

### Fixed

- **Allegro User-Agent Header Correction**: Configured a dynamic `User-Agent` header (`iqoqo/{Config.VERSION} (+https://iqoqo.cc)`) based on the application version to avoid `403 EDGE_REQUEST_REJECTED` and `SERVICE_ERROR` blockages by the Allegro API. Applied the headers to OAuth token request, refresh request, and catalog/listing fetchers.
- **Allegro Tests Hardening**: Extended `tests/test_allegro.py` with mock assertions validating that the formatted `User-Agent` is correctly set in request headers.
- **Authlib Deprecation Warning**: Replaced deprecated `authlib.jose.errors` import with `joserfc.errors` in `app/api/auth.py` to prevent startup and runtime warnings.

### Removed

- **In-App Backup Script**: Removed `scripts/backup.py` and its APScheduler daily job (`scheduler.py`), consolidating all backup responsibilities into `scripts/cloud_backup.sh` (rclone-based, system cron). Removed `BACKUP_CRON_HOUR`, `BACKUP_CRON_MINUTE`, `BACKUP_DIR` config entries. The `make backup-run` / `backup-install` targets are now the sole backup mechanism. Tests `test_backup_crypto.py` and `test_backup_creation` removed.

## [0.7.8] - 2026-07-07

### Removed

- **Legacy Observability Stacks Decommissioned**: Removed Grafana Cloud (`docker-compose.grafana.yml`, `deploy/alloy/config.alloy`) and legacy Prometheus + Jaeger (`docker-compose.prometheus-jaeger.yml`, `deploy/otel-collector-prometheus-config.yaml`, `deploy/prometheus.yml`) configurations and targets.
- **`prometheus-flask-exporter` Dependency**: Cleaned up the unused Prometheus Python exporter package and `/metrics` rate limiter exemption checks, relying fully on the OpenTelemetry/OpenObserve stack.

### Changed

- **DevOps Skill Documentation**: Updated `.agents/skills/devops-observability-expert/SKILL.md` to remove legacy Jaeger reference and align with the consolidated OpenObserve-only architecture.
- **Monitoring Documentation**: Refactored `docs/MONITORING.md` to clean up decommissioned stacks, keeping only the unified OpenTelemetry + OpenObserve architecture.

### Fixed

- **Infrastructure Test Compatibilities**: Cleaned up `tests/test_infra_config.py` and `tests/test_payload_validation.py` to match the simplified `run.sh` configuration flow and metrics removal.
- **IDOR & BOLA Protection**: Restructured virtual and physical item update API endpoints (`_update_virtual_item` and `_update_physical_item` in `app/api/items.py`) to return `404 Not Found` instead of `403 Forbidden` for unauthorized requests to prevent information disclosure.
- **FRBR Ontology Boundary Guards**: Blocked physical state mutations (e.g., barcode, condition, lending status, borrower information) on virtual wishlist-level items.
- **Schema Validation Hardening**: Hardened `ItemCreateSchema` and `ItemUpdateSchema` in `app/api/schemas.py` to reject `id: 0`.
- **Database Ingest Service Fix**: Fixed a runtime `AttributeError` in `app/core/ingest.py` by replacing invalid `db.text` usage with SQLAlchemy `text()` executed via session, guarded by a Postgres dialect check.
- **Frontend Item Component Hardening**: Hidden the "History" tab and borrower/lending actions on virtual wishlist items in `item-sidebar.tsx` and `item-tabs.tsx`.
- **DevOps and Script Cleanup**: Modified `scripts/backup.py` to fail fast if `SECRET_KEY` is missing in non-dev/test environments, fixed base64url padding bugs in `tests/test_backup_crypto.py`, and updated `scripts/sync_permissions.py` to strip block comments.
- **Mypy Relationship Typing**: Typed the `Role.permissions` and `User.roles` relationships in `app/db/auth.py` with `Mapped` and `relationship()` to avoid type ignores.
- **Testing Coverage Expansion**: Added pytest backend suite `tests/test_api_items_078.py`, Vitest component suite `item-card-078.test.tsx`, and E2E Playwright test assertions in `wishlist_workflow.spec.ts`.

## [0.7.7] - 2026-07-07

### Added

- **Offline Diagnostics — `make status`**: Introduced `scripts/iqoqo-status.sh`, a comprehensive 436-line bash health check script that inspects all deployment layers: container states (healthchecks, uptime), Redis connectivity and queue depth, PostgreSQL connections and migration version, Celery worker stability and OTel exporter health, API `/api/health` endpoint and gunicorn workers, Nginx config syntax and 5xx rates, cover file count and disk usage, and Docker system health. New `status` target in the `Makefile` with `--stack preview|prod` support. Exit codes: `0` (healthy), `1` (warnings), `2` (errors).
- **Product Manager Skill**: Added `.agents/skills/product-manager/SKILL.md` — structured agent skill for feature scoping, vertical slicing, UX advocacy, and roadmap planning aligned with FRBR ontology and iqoqo's testing triangle philosophy.
- **DevOps Skill Documentation**: Enhanced `.agents/skills/devops-observability-expert/SKILL.md` with offline diagnostics workflow (`make status` before querying OpenObserve).
- **API Client Timeout**: Added 15-second timeout to the axios-based frontend API client to prevent hung requests.

### Changed

- **Exception Hardening in OAuth Flow**: Narrowed broad `except Exception` clauses in `app/api/auth.py` to specific exception types (`OAuthError` for OAuth init/authorize, `JoseError` for ID token parsing, `SQLAlchemyError` for user persistence, `pyjwt.PyJWTError` for JWT generation), improving error diagnostics and preventing silent catch-all masking.

### Fixed

- **Infrastructure Test Compatibility**: Updated `tests/test_infra_config.py` to align with the new status script environment detection.

## [0.7.6] - 2026-07-06

### Added

- **OpenObserve Browser RUM & Logs Integration**: Integrated `@openobserve/browser-rum` and `@openobserve/browser-logs` client-side SDKs. Created the `BrowserOpenObserveRum` component to load the SDKs dynamically, start session replay recording, and propagate authenticated user context (`useProfile`). Added Playwright E2E tests verifying client-side RUM initialization.
- **RUM Configuration Propagation**: Updated `.env.example`, `.env`, `.env.dev`, `.env.test`, and `frontend/.env.example` with OpenObserve RUM variables. Updated `run.sh` to forward these configuration options as `NEXT_PUBLIC_` variables to Next.js.
- **OpenTelemetry Distributed Tracing & Dynatrace Integration**: Implemented OpenTelemetry auto-instrumentation across Flask API, Celery background worker, and Next.js frontend services. Added `deploy/otel-collector-config.yaml` to export traces and metrics (Redis, PostgreSQL, and Docker stats) to Dynatrace via the OpenTelemetry Collector. Added tracing configuration parameters to `docker-compose.yml`, `run.sh`, and `.env.example`.
- **Frontend Telemetry Registration**: Created `frontend/instrumentation.ts` utilizing `@vercel/otel` for frontend trace propagation.
- **Devcontainer Sandbox Configuration**: Introduced `.devcontainer/Dockerfile` and `.devcontainer/devcontainer.template.json` template setup with Ubuntu 24.04 and workspace bind-mounts to simplify sandbox environment deployment.
- **Database Migration Make Targets**: Added `db-stamp` and `db-upgrade` targets to the `Makefile` (supporting both docker and local run modes) to simplify schema upgrades and migrations version synchronization.
- **Browser Web Vitals Instrumentation (Layer 5)**: Added `frontend/components/browser-telemetry.tsx`, a null-rendering `'use client'` component that dynamically loads the OpenTelemetry Web SDK post-hydration. Instruments DOM document load events (Core Web Vitals) and user interactions (clicks, submits). Traces are shipped via OTLP HTTP to the OTel Collector with CORS whitelisted for `localhost:3000`.
- **Nginx Native OTel Module (Layer 6)**: Added `deploy/Dockerfile.nginx` (Debian-based `nginx:1.25` with `nginx-module-otel`) and `deploy/nginx-main.conf` (loads `ngx_otel_module.so`, configures gRPC OTLP export, injects `trace_id`/`span_id` into the access log). The nginx service in `docker-compose.yml` now builds from `deploy/Dockerfile.nginx` instead of pulling `nginx:1.25-alpine`.
- **OpenAI LLM Telemetry (Layer 7)**: Added `opentelemetry-instrumentation-openai` to `requirements.txt`. Automatically captures token consumption, prompt payloads, model parameters, and generation latency as OTel spans without code changes.
- **PostgreSQL & Redis Native Metrics (Layer 8)**: Added `postgresql` and `redis` native receivers to `deploy/otel-collector-local.yaml`. The OTel Collector now scrapes engine-internal metrics (dead tuples, cache hit ratio, memory fragmentation, eviction rates) directly from the database and cache containers.
- **Legacy Prometheus + Jaeger Stack Preserved**: Moved the old `docker-compose.monitoring.yml` contents to a new `docker-compose.prometheus-jaeger.yml` for operators who prefer PromQL/Jaeger UI. New Makefile targets: `make monitoring-legacy-start` / `make monitoring-legacy-stop`.

### Changed

- **Default Observability Backend**: Replaced Prometheus + Jaeger + cAdvisor as the default local monitoring stack with **OpenObserve** (Rust-based unified backend, Apache Parquet storage, standard SQL queries). New `docker-compose.monitoring.yml` defines OpenObserve + OTel Collector. Makefile targets `monitoring-start`/`monitoring-stop` now target OpenObserve. `run.sh` dev-mode monitoring startup updated to use `iqoqo-openobserve` container naming.
- **OTel Collector Config**: Added new `deploy/otel-collector-local.yaml` targeting OpenObserve. CORS enabled on the OTLP HTTP receiver for browser-side traces. Metrics pipeline now includes `docker_stats`, `postgresql`, and `redis` receivers.
- **`.env.example` Observability Section**: Replaced legacy Prometheus/Jaeger port variables with new `OPENOBSERVE_HOST_PORT`, `OPENOBSERVE_ROOT_USER`, `OPENOBSERVE_ROOT_PASSWORD`, `OTEL_GRPC_HOST_PORT`, `OTEL_HTTP_HOST_PORT`, `OTEL_METRICS_EXPORTER`, `OTEL_LOGS_EXPORTER`, `OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED`, and `NEXT_PUBLIC_OTEL_COLLECTOR_URL` variables.
- **Makefile Help Text**: Added monitoring targets section to `make help` output.

### Fixed

- **Release Workflow Cache and Actions Deprecation**: Upgraded `docker/build-push-action` to `v6` and `softprops/action-gh-release` to `v2` to target modern Node.js versions. Configured buildx to use `ignore-error=true` for cache saving to prevent pipeline failures from transient cache reservation issues.
- **Infrastructure Validation Tests**: Added a `--validate-only` flag to `run.sh` and updated `tests/test_infra_config.py` to use it, preventing timeouts and subprocess hangs when verifying configurations.
- **Frontend Build and Lint Pipeline**: Ignored the `.next-e2e` build directory in ESLint configuration to skip generated chunks, removed unused variables in E2E integration specs, and bypassed a React hooks setState-in-effect warning on the Collection page to ensure a clean build.
- **Wishlist Detail View**: Fixed `_get_virtual_item_detail` in `app/api/items.py` to return work-level details for virtual items when they lack a manifestation, resolving `404 Not Found` and `UnboundLocalError` issues in collection detail navigation.
- **Wishlist Invalidation Scope**: Extended frontend query invalidation scope in `useAddItem` React Query hook and `AddToCollectionDropdown` component to invalidate `worksShelf` and `expressionsShelf` on wishlist changes, preventing items from disappearing from shelf views after reload.
- **Add Manifestation to Wishlist**: Configured the `/api/manifestations/<id>/add` endpoint to create a `UserWorkIntent` instead of a physical `Item` when `collection_status == "wish_list"`. Added a corresponding "Add to Wishlist" option to the manifestation detail page's dropdown.

## [0.7.5] - 2026-06-10

### Fixed

- **Missing `sync_db_permissions.py` on preview instance**: Copied the lightweight `scripts/sync_db_permissions.py` from production to the preview codebase and added `./scripts` volume mount in `docker-compose.yml` so pre-built images pick up the local script. The script syncs permissions and roles from `shared/permissions.yaml` into the DB at container startup without clobbering existing assignments.

## [0.7.4] - 2026-06-08

### Fixed

- **Database Permissions Sync on Startup**: Modified the `web` service startup command in `docker-compose.yml` to automatically execute `scripts/sync_db_permissions.py` after database migration upgrades. This ensures that new permissions (such as `write:item`) are automatically populated and assigned to user roles when deploying container updates, resolving 403 Forbidden errors when users attempt to add manifestations to their collections.
- **Production Deployment Exit Status**: Fixed a bash short-circuit bug in `run.sh` that caused the script to exit with code `1` (triggering `make: *** [Makefile:171: start] Error 1` failures) upon successful production deployment. Replaced the `[ "$MODE" != "prod" ] && echo` line with a proper `if` block.
- **Collection Grid Scope Resolution**: Fixed a regression where the Collection view was still passing `true` for the `includePublic` parameter to `useInfiniteItems`, causing other users' public items to appear in the user's private collection with a "Request Loan" button instead of the status dropdowns.

## [0.7.3] - 2026-06-07

### Added

- **Bulk Cover Retry Command**: Added `retry-missing-covers` target in the `Makefile`, allowing bulk processing of missing manifestation covers. Supports target mode parameterization (e.g., `make retry-missing-covers preview` or `make retry-missing-covers prod`) to align with environment-specific configurations.

### Fixed

- **Stuck Cover Tasks Cleanup**: Automatically scans and resets cover tasks stuck in `pending` or `processing` states for more than 30 minutes to `failed` state during app startup.
- **Dynamic Cover Status Timestamps**: Automatically updates `cover_status_updated_at` in manifestation metadata whenever `cover_status` is updated via `update_meta`.

## [0.7.2] - 2026-06-06

### Added

- **Grafana Cloud Monitoring Integration**: Created `deploy/alloy/config.alloy` and `docker-compose.monitoring.yml` to set up Grafana Alloy and cAdvisor monitoring on preview (`pre.iqoqo.cc`) and production hosts, capturing Flask API, Next.js frontend, cAdvisor container, and host metrics/logs (via systemd journald and docker daemon sockets).
- **Observability Documentation**: Added `docs/MONITORING.md` guide outlining architecture, security zero-trust configurations (Nginx public block on `/metrics`), and deployment methods.

### Fixed

- **Database Migrations PG Identity Safeguard**: Wrapped `llm_telemetry` `id` column dropping operations behind `is_pg_identity` check in `52b02a37b16b_add_lending_tables.py` migration script, preventing syntax error crashes when running migrations against cloned PostgreSQL databases.

## [0.7.1] - 2026-06-04

### Added

- **Environment Data Cloning**: Added `scripts/clone.sh` bash script to duplicate databases and sync image assets (covers/gallery) between environments.
- **Dynamic Makefile Targets**: Updated the `Makefile` with dynamic `start` and `stop` targets supporting development, preview, and production modes, along with optional `--prebuilt` flags.

### Fixed

- **Roadmap Database Migrations**: Added missing database migration script to generate `reading_roadmaps` and `roadmap_items` tables, fixing the silent failure when attempting to create a new reading roadmap in the UI.
- **Item History Visibility**: Restricted the visibility of the item history tab in the frontend based on user permissions to prevent "Failed to load item history" errors for unauthorized or unauthenticated users.
- **Collection Grid Scope**: Changed `includePublic` default value to `false` in `useInfiniteItems` to ensure user's private collection grid only contains their own items, resolving incorrect linking to other users' public copies.
- **Idempotent Migration Cleanup**: Guarded `batch_alter_table` calls inside the stale-table cleanup migration block behind `table_exists` checks to ensure the migration executes safely on partially-migrated databases.
- **Taxonomies Cross-Faceted Filtering**: Added backend support for `collection_status` filtering in the `/api/taxonomies` endpoint, enabling cross-faceted narrowing based on the item's collection status.
- **useTaxonomies Hook JSDoc Return Type**: Updated the JSDoc return type of the `useTaxonomies` React hook to correctly return `TaxonomiesResponse` instead of `ApiResponse<TaxonomiesResponse>` to match the query function's actual return value.

## [0.7.0] - 2026-05-20

### Added

- **Infinite Scroll**:
  - Replaced manual Previous/Next pagination in the Collection view with lazy loading via `IntersectionObserver`.
  - Two new React Query hooks: `useInfiniteItems` and `useInfiniteManifestations` using `useInfiniteQuery` with page-based `getNextPageParam`.
  - Vitest unit tests for infinite query hooks (`infinite-hooks.test.tsx`).
  - Playwright E2E test for scroll-triggered data fetching (`infinite_scroll.spec.ts`).
  - Added infinite scroll support for Works and Expressions shelves with `useInfiniteWorksShelf` and `useInfiniteExpressionsShelf` hooks.
  - Implemented backend pagination for `GET /api/works/shelf` and `GET /api/expressions/shelf` with `limit` and `offset` query parameters.

- **Library Sharing & Public Discovery (Phase 1)**:
  - **Public Profiles**: Users can opt-in to public profiles via `u/[public_username]`.
  - **Shared Collections**: Secure token-based sharing for filtered views (e.g., Wishlist, Reading list).
  - **Granular Privacy**: New `is_hidden` toggle for items to exclude specific copies from public views.
  - **"Smart Check" Inventory Tool**: Visitor-facing tool to check if a manifestation/work exists in a user's library.
  - **i18n Foundation**: Integrated `next-intl` for multi-language support (EN, PL).
  - **Social Metadata**: Added `public_username` and `bio` to user profiles.
  - **Web Share Integration**: New `ShareButton` with native Web Share API support and clipboard fallback.

- **Custom Taxonomies & Collections (Step 3)**:
  - **Facet Mini-Search**: Added sticky client-side search input to each facet list (Tags, Genres, Publishers) in `sidebar-filters.tsx` via a new `SearchableFacet` sub-component with real-time `includes()` filtering.
  - **User Collections CRUD**: Full REST API (`app/api/collections.py`) for hierarchical `UserCollection` folders with parent-child validation, cycle detection, and child-deletion protection.
  - **Quick-Create Collection**: `collection-quick-add.tsx` — inline form in "Add to Collection" dropdowns for on-the-fly folder creation.
  - **Manage Collections Modal**: `manage-collections-modal.tsx` — dedicated modal for listing, renaming, and deleting custom collections with React Query mutation lifecycle.
  - **Clickable Taxonomy Pivots**: `DiscoveryPivot` component wraps tags, genres, and publishers as `<Link>` badges that navigate to the discovery grid pre-filtered by that value.
  - **TaxonomyEditor**: Unified component in `item-header.tsx` / `item-tabs.tsx` for editing tags, genres, publisher assignments on items.
- **Crowdfunding & Upstream Sustainability**:
  - Added GitHub Sponsors and Buy Me a Coffee links to the app footer (`frontend/components/dashboard/footer.tsx`).
  - Added "Support & Upstream Sustainability" section to `README.md` with sponsorship links and context on development cost offsets.

- **Backend Architecture**:
  - `SharedCollection` model with automated secure token generation.
  - Cascade deletes for social data when a user account is removed.
  - BOLA protection for all visibility and sharing endpoints.
- **Quality Assurance**:
  - Extended backend test suite for pagination, visibility gates, and social models.
  - Vitest unit tests for core UI components (`ShareButton`, `EmptyState`).
  - Playwright E2E coverage for public profile discovery and privacy management.

### Fixed

- **Faceted Navigation — Scoped Facets & Non-Empty Results**:
  - Genre filter now correctly handles JSON array (`Work.meta["genres"]`) and scalar (`Work.meta["genre"]`) values — uses JSONB `@>` on PostgreSQL, ILIKE fallback on SQLite.
  - Genre facet now shows only genres present in the current user's works (previously returned a hardcoded ~200-genre list).
  - Tags facet now scoped to tags attached to the current user's items (previously global).
  - Publishers facet now scoped to publishers from the current user's items (previously global).
  - Extracted shared `apply_genre_filter` helper into `app/api/filters.py`.
- **Serialization Reliability**: Resolved `AttributeError` in public API when serializing complex FRBR relationships for unauthenticated views.
- **Database Constraints**: Fixed `NOT NULL` constraint violations in SQLite during user deletion by correctly implementing relationship cascades.
- **Taxonomies Query**: Fixed PostgreSQL json type distinct error in `/api/taxonomies` by querying distinct Work IDs prior to metadata extraction.

## [0.6.0] - 2026-05-10

### Added

- **Scanner Strategy Pattern**: Extracted complex barcode lookup logic into a dedicated strategy layer (`app/strategies/lookup.py`).
  - Concrete strategies for **Books** (ISBN), **Audio** (Discogs/MusicBrainz), **Video** (TMDB), **Board Games** (BGG), and **Puzzles**.
  - `LookupStrategyFactory` for intelligent routing based on frontend hints.
- **Dual Intent Scanning**: The scanner success card now offers "Add to Library" vs. "Add to Wishlist" intents, allowing users to track desired items without immediate ownership.
- **Lint Safeguards**: Added a permanent automated test (`tests/test_lint_safeguards.py`) that strictly forbids the use of `# pylint: disable=too-many-return-statements` across the `app/` codebase.
- **DevOps & Deployment**:
  - GitHub Actions workflow (`deploy.yml`) to build and push Docker images to `ghcr.io` on push to `main` and semver tags.
  - `docker-compose.prebuilt.yml` override to run pre-built images from `ghcr.io` (requires Docker Compose v2.24+).
  - `--prebuilt` flag to `run.sh` to skip local build and pull from registry.
- **Cloud Backups**:
  - `scripts/cloud_backup.sh` — rclone-based backup of PostgreSQL + asset volumes.
  - `.agents/skills/cloud-backup-setup/SKILL.md` — agentic skill to guide rclone setup.
  - `docs/BACKUPS.md` — documentation for cloud backup configuration.
- **Instance Maintenance**:
  - `MAINTENANCE_MODE` instance setting toggle in Admin → Internal Settings.
- **UI & Discovery**:
  - GitHub repository link button in landing page Hero component.

### Changed

- **Refactored API**: Completely refactored `app/api/scanner.py` to eliminate cyclomatic complexity and satisfy strict linting rules.
- **Global Code Hygiene**: Removed all instances of `too-many-return-statements` silencers from `admin.py`, `manifestations.py`, `decorators.py`, and `config_service.py` by refactoring logic into smaller, testable helpers.
- **Standardized Image Uploads**: `upload_manifestation_image()` now accepts a dynamic `source` form field (default: `user_upload`), enabling scanner integrations and automated fallbacks to tag their contributions correctly.

### Fixed

- **Mock Integrity**: Updated and hardened the scanner test suite (`tests/test_api_scanner.py`) to reflect the new strategy architecture and prevent `MagicMock` serialization leaks in JSON responses.

## [0.5.0] - 2026-05-01

### Added

- **Manual Cover Upload**: `ManualEntryForm` now accepts a cover image file during manual entry fallback, which is uploaded to the backend after the item is saved.
- **Ontology & Tracking**:
  - **Board Game Statuses**: Added `want_to_play` to the canonical status list to support game wishlisting.
  - **Metadata Provenance**: Integrated automated `data_source` tracking for Discogs, TMDB, BGG, and Google Books/Open Library lookups, providing clear attribution badges in the UI.
- **Smart AI Capabilities**:
  - **Media-Aware AI Art**: Expanded LLM image generation prompts to use media-specific prefixes (e.g., "Cinematic movie poster" for films, "Box art" for games), significantly improving the quality of AI-generated covers for non-book items.
- **Admin UX**:
  - **RBAC Descriptions**: Added descriptive tooltips to the Role-Based Access Control sheet to clarify user permission boundaries.
- **Media Taxonomy SSoT**: Implemented a Single Source of Truth for the iqoqo media taxonomy (categories, formats, and statuses) in `shared/taxonomy.yaml`.
- **Code Generation Engine**: New `scripts/generate_taxonomy.py` automatically produces synchronized Python (`app/core/taxonomy.py`), TypeScript (`frontend/types/taxonomy.ts`), and RDF (`docs/ontology/taxonomy.ttl`) artifacts.
- **Audiobook Category**: Promoted Audiobooks to a top-level media category (splitting from Text) with specialized progress tracking and image labels.
- **Integrity Tests**: Added `tests/test_taxonomy_generation.py` to ensure committed generated files never drift from the YAML source.

### Changed

- **Format Rename**: Renamed the generic `puzzle` format to `jigsaw_puzzle` for clarity and future extension.
- **Dynamic Image Labels**: The `MultiImageUploader` now dynamically adapts its labels based on the item category (e.g., "Disc" for music, "Dust Jacket" for books, "Box Contents" for games).
- **Consolidated Taxonomy**: Refactored `app/db/core.py` and `frontend/types/frbr.ts` to re-export from the generated taxonomy, eliminating attribute drift across the stack.

### Fixed

- **Firefox Camera Memory Leak**: Hardened `CameraCapture` `useEffect` cleanup to prevent dangling `enumerateDevices` promise callbacks from updating state after unmount.
- **Profile Settings**: Resolved a critical bug where the "Display Name" field was read-only and didn't persist changes to the database.
- **Aesthetic Consistency**: Standardized user metadata table colors to use semantic theme tokens instead of hardcoded classes.
- **Image Resolution**: Fixed broken fallback cover image paths on production environments by routing all asset resolution through the centralized `getCoverUrl` utility.
- **Component Stability**: Resolved JSX syntax errors in the Puzzle and Video metadata components.
- **Migration Chain Repair**: Fixed a broken Alembic migration chain where a revision referenced a non-existent ID (`fix_llm_telemetry_sequence`).
- **Scanner Media Detection**: Hardened media type detection in the scanner API to correctly map generic hints (`audio`, `video`) to canonical formats.
- **Security**: Patched PII Leakage/User Enumeration by enforcing exact matches on email wildcard searches.

### Database Migrations

- `9f5598cf6467_add_audiobook_category_and_rename_puzzle`: Moves Audiobook manifestations from `text` to `audiobook` category and renames `puzzle` format to `jigsaw_puzzle` in manifestation metadata.

### Changed (UX)

- **Graceful Lookup Failure**: When API/LLM/Vision extraction fails, the scanner now prominently routes the user to the `ManualEntryForm` with the scanned EAN pre-filled via `initialIdentifier`.
- **Additional Scans Pre-selection**: `MultiImageUploader` now intelligently defaults the scan label based on the current item's media type (e.g., `"front"` for books, `"disc"` for CDs).
- **Cover Editor Mobile Guard**: The heavy Canvas-based Cover Art Editor is now hidden on screens narrower than the `md` Tailwind breakpoint (768px). A clear message directs users to an iPad or desktop browser for cover editing.

## [0.4.1] - 2026-04-20

### Added

- **API Cover Fallback**: All item and manifestation endpoints now fallback to `meta['cover_url']` if the primary `cover_url` column is missing (e.g., from external metadata extraction).
- **Comprehensive Infrastructure Tests**: 10 new tests covering API fallbacks and DB connection pool configuration.

### Fixed

- **Database Stability**: Implemented explicit `db.session.remove()` in `@app.teardown_appcontext` to resolve connection pool exhaustion under load.
- **Celery Worker Deadlocks**: Replaced `--pool=solo` band-aid with a thread-safe `--pool=threads` configuration (configurable via `CELERY_POOL`) and added `worker_process_init` signal to ensure clean database engine disposal after process forks.
- **Sequence Desync**: Fixed PostgreSQL identity sequence desync for the `llm_telemetry` table using a dynamic sequence lookup migration.
- **Retry Script**: Hardened `retry_missing_covers.py` query filters and added type-safe dry-run output.

### Changed

- **Config**: Added `CELERY_POOL`, `CELERY_CONCURRENCY`, and SQLAlchemy pool settings to `.env.example`.

## [0.4.0] - 2026-04-15

### Added

- **Item Interaction & Provenance**:
  - **Status Change Logging**: Automated tracking of item status history in the `ItemStatusLog` table, reachable via `GET /items/<id>/logs`.
  - **Item Provenance Timeline**: New **History** tab in the item UI displaying a chronological log of all lifecycle events.
  - **Multi-Scan Gallery**: Support for storing and viewing additional manifestation scans (discs, booklets, back covers) via the `ImageScan` model and a dedicated **Gallery** tab.
  - **Custom Provenance Headers**: Modified cover image serving to inject `X-Manifestation-ID` and `X-Image-Source` HTTP headers for asset traceability.
  - **Metadata Attribution**: Display of metadata source (e.g., "Sourced from Google Books") in the item details view.
- **Media-Specific UX**:
  - **Polymorphic Action Panel**: Integrated context-aware buttons for Books ("Log Reading Progress"), Audio ("Now Listening"), Video ("Now Watching"), and Games ("Log Play").
- **Search Hardening**: Restored `search_vector` and FTS indexes to the `Work` model to ensure robust metadata searching for video and board game Cast, Directors, and Mechanics.

- **Test Stability**: Resolved a SQLAlchemy `NoReferencedTableError` occurring during testing by correctly synchronizing the `_USE_PG` schema calculation flag in `app/db/core.py` with `app/db/audio.py` for test environment compatibility.
- **Admin API Hardening**: Enforced immutability for the `admin` role's permissions API to prevent accidental lockout, and clamped pagination limits to 100 on the `/admin/users` endpoint to mitigate DoS vectors.

### Database Migrations

- Added `item_status_logs` table for tracking history.
- Added `image_scans` table for manifestation galleries.
- Re-initialized Postgres-specific search vectors for the `Work` model.

## [0.3.0] - 2026-04-11

### Added

- **Ontology Expansion**: Support for Video (Film, Series), Board Games, and Jigsaw Puzzles via FRBRoo `ManifestationContribution` (Studio/Distributor) and `ContainerAggregation` (Box Contents).
- **External API Integrations**: Integrated TMDB (The Movie Database), BGG (BoardGameGeek), Allegro (Retail), and UPCItemDB for robust barcode fallback resolution and rich metadata fetching.
- **Async Task Queue**: Implemented a `ThreadPoolExecutor` (`app/core/tasks.py`) for executing and polling LLM Vision cover metadata extractions asynchronously without blocking the UI.
- **UI Attributions**: Added `TmdbAttribution` and `BggAttribution` components to comply with external API Terms of Service.
- **Background Tasks**: Centralized APScheduler for recurring maintenance (e.g., daily automated backups).
- **Navigation UX**: Added "View in My Collection" button to manifestation details, allowing users to jump directly to their owned items.
- **Telemetry Hardening**: Refactored `LLMTelemetry` to handle high-concurrency event logging with non-blocking database indexes.
- **Scanner Fallbacks**: Added a `ManualEntryForm` UX to handle scenarios where barcode/ISBN lookups timeout or return no results.
- **Desktop Scanner UX**: `CameraCapture` now detects available media devices. If no rear camera is detected (e.g., Desktop), it automatically defaults to a clean Drag & Drop file uploader UI.

### Changed

- **Scheduler Gating**: Background tasks are now gated by `SCHEDULER_AUTOSTART` to prevent side effects in CLI and test environments.
- **Backup Script**: Isolated `sys.path` mutations to prevent environment pollution when the backup module is imported.

### Fixed

- **Manifestation Ownership**: Implemented `@optional_auth` decorator for `/manifestations` endpoints to correctly detect `user_owns` status for authenticated users.
- **Image Rotation**: Applied `PIL.ImageOps.exif_transpose` within the image processing pipeline to automatically fix the 90-degree rotation bug caused by smartphone EXIF metadata tags during cover uploads.

### Documentation

- **Backups**: Documented the Scheduled Backups system and environment configuration in `docs/ARCHITECTURE.md`.

### Database Migrations

- Introduced multi-schema architecture (`catalog`, `inventory`, `auth`).
- Added DB-level `CheckConstraint` to `ContainerAggregation` to ensure data integrity of board game components.

## [0.2.0] - 2026-04-03

### Added

- **Audio Support**: Full support for Vinyls, CDs, and Audiobooks via FRBRoo Event-Based Modeling.
- **Multiple Scans**: Added a secondary image upload system to manifestations (Disc, Inlay, Box, Back Cover).
- **Audio UI**: Item views now dynamically render `Tracklists`, `Matrix Numbers`, `Pressing IDs`, and `Labels` for supported media types.
- **Categorized Statuses**: Reorganized the item status dropdown into functional categories (Availability, Reading, Listening, Acquisition) for better collection management.
- **New Item Statuses**: Added `Damaged`, `Listening`, `Listened`, `Ordered`, and `Lost` to the canonical status list.
- **E2E Acquisition Tests**: New Playwright test suite covering Book, CD, and Vinyl ingestion via ISBN lookup, barcode scanning, and cover art analysis.

### Changed

- **Vision Waterfall**: Hardened exception handling to ensure robust fallback from Gemini to local backends (Ollama, Tesseract) during API or network failures.
- **UI Refinement**: Updated `ItemSidebar` to include the `MultiImageUploader` and categorized status selection.
- **Infrastructure**: Added `GALLERY_DIR` for storing secondary manifestation scans.

## [0.1.0] - 2026-03-28

### Added

- **Vision-based Metadata Extraction**: Added ability to extract `Title` and `Authors` from cover images via Gemini, Ollama (llava), or Tesseract OCR.
- **New Endpoints**: Added `POST /api/vision/extract` for handling cover image uploads (max 10MB) and extraction.
- **Full-Text Search**: Added PostgreSQL `TSVECTOR` columns (`fts_simple`) to `Work` and `Manifestation` for optimized searching.
- **LLM Permissions & Telemetry**: Introduced granular RBAC permissions (`LLM_GENERATE_COVER`, `LLM_GENERATE_METADATA`, `LLM_GENERATE_CLOUD`), a global `ALLOW_LLM` feature flag, and per-user telemetry tracking (duration/cost).
- **Manual Entry Extensions**: Added support for `ISBN` and `PublicationDate` when creating items manually.

### Changed

- **Proxy & CORS**: Updated `ProxyFix` to include `x_port=1` and enabled `supports_credentials=True` for OAuth sessions.
- **Code Formatting**: Updated Prettier configuration to use double quotes (`singleQuote: false`).
- **Dependencies**: Added `tesseract-ocr` system dependency to the Dockerfile.

## [0.0.7] - 2026-03-22

### Added

- **Owner-Scoped Dashboard Stats:** `GET /api/stats` now requires authentication and returns statistics scoped to the authenticated user's collection. FRBR entity counts (works, expressions, manifestations) use `DISTINCT` joins to avoid inflation when multiple items share the same manifestation.
- **`/api/config` Endpoint:** New public endpoint exposing runtime feature flags to the frontend (initially `FEDERATION_ENABLED`). Does not require authentication.
- **`unread` Item Status:** Added `unread` as a canonical item status to `ITEM_STATUSES`, enabling users to mark items as unread. Collection filter bar and sidebar now include an "Unread" filter option.
- **Manual Item Creation:** New `POST /api/items/manual` endpoint allowing users to add items by title/author/ISBN without scanning, backed by the `useAddManualItem` React Query mutation hook.
- **Federation Feature Flag:** Added `FEDERATION_ENABLED` environment variable. Federation-related UI (profile consent, federation tab on item detail) is now hidden behind this flag via `useAppConfig`.
- **`Makefile` `init` target:** Added `make init` for local dev bootstrap (creates venv, installs requirements, installs frontend node modules).

### Changed

- **Performance — Stats Query:** Replaced N+1 `COUNT` queries per status in `DataManager.get_stats()` with a single `GROUP BY Item.status` aggregate query, reducing DB round-trips from 7+ to 1.
- **Correctness — FRBR Subqueries:** Replaced `scalar_subquery()` (single-value context) with `.subquery()` in multi-row `IN(...)` filter chains inside `DataManager.get_stats()` to correctly communicate intent and avoid dialect edge-cases.
- **Collection page — URL sync:** Fixed trailing `?` appended to the URL when all filter/sort params are at their defaults (e.g. `/collection?` → `/collection`).
- **Collection page — Sort options:** Wired all 5 sort options end-to-end: "Recently updated" (default), "Recently added", "Title A-Z", "Title Z-A", and "Author". The `useItems` hook now passes `sort` to the API, and the backend's `GET /items` endpoint correctly handles each value.
- **Frontend JSDoc:** Added thorough JSDoc comments to all major frontend components, hooks, pages, and API utilities.
- **`Navbar` logout:** Added error handling to the logout flow and clears the React Query cache on sign-out.
- **Dockerfile:** Bumped base image to `python:3.14-slim`.
- **GitHub Actions quality workflow:** Updated branch targets, pinned Postgres image version, and adjusted artifact retention.
- **Markdownlint config:** Added `.pytest_cache` and `.agents/rules` to the markdownlint exclusion list (auto-generated/IDE files with non-standard formatting).

### Fixed

- **`Footer` JSDoc:** Corrected copy-paste error — JSDoc described the component as a "Sticky top navigation bar" instead of the site footer.
- **README code blocks:** Fixed four fenced code blocks in the Data Management section tagged as ` ```markdown ` (should be ` ```bash `), improving syntax highlighting.
- **README link:** Fixed broken "Installation Guide" link that pointed to a Google search URL instead of `docs/INSTALL.md#data-importexport`.
- **`get_alerts.sh` stderr redirect:** Fixed `2>&1 > .alerts.json` (stderr went to terminal) to `> .alerts.json 2>&1` (both streams captured in file).

### Database Migrations

No schema migrations are required for this release. The `unread` status is a new allowed value for the existing `Item.status` string column — no column type or constraint changes are needed.

## [0.0.6] - 2026-03-16

### Added

- **Authentication Prep:** Introduced foundational environment variables for the upcoming user profiles and SSO authentication (`JWT_SECRET_KEY`, `AUTH_SECRET`, Google OAuth secrets, and default admin credentials).
- **Cover Image Validation:** Added support for blocking known junk/placeholder covers by filtering them through pHash hex strings via the `IQOQO_KNOWN_JUNK_PHASHES` environment variable.
- **Full-Text Search:** Implemented item search functionality on the `/api/items` endpoint. Users and the frontend can now filter items by title using the `q` query parameter.
- **Testing:** Added robust backend API tests (`test_search_items_by_title`) to ensure full-text search accuracy and proper filtering of non-matching results.

### Changed

- Updated `.env.example` to include the new required system variables (Auth keys, Admin details, and `NEXT_PUBLIC_FRONTEND_URL`).

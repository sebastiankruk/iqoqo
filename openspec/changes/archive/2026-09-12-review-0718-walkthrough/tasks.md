# Tasks: v0.7.18 Codebase Review Walkthrough

## Phase 1: Backend Foundation (Chunks 01-04)

- [x] **Chunk 01: DB Models — Core FRBR** — Review `app/db/` core models (10 files): `__init__.py`, `core.py`, `models.py`, `auth.py`, `lending.py`, `social.py`, `contributions.py`, `search_types.py`, `settings.py`, `roadmap.py` → `.context/notes/review/0.7.18/chunk-01-db-models.md`
- [x] **Chunk 02: DB Models — Media Extensions** — Review `app/db/` media models + app factory (6 files): `audio.py`, `video.py`, `games.py`, `puzzle.py`, `app/__init__.py`, `app/config.py` → `.context/notes/review/0.7.18/chunk-02-media-models.md`
- [x] **Chunk 03: Core Services — FRBR Engine & Ingest** — Review `app/core/` FRBR services (7 files): `__init__.py`, `frbr_service.py`, `ingest.py`, `data_manager.py`, `search_service.py`, `ontology_validation.py`, `format_normalizer.py` → `.context/notes/review/0.7.18/chunk-03-core-frbr.md`
- [x] **Chunk 04: Core Services — Auth, Cache, Tasks** — Review `app/core/` infra services (10 files): `permissions.py`, `item_access.py`, `cache.py`, `celery_app.py`, `tasks.py`, `scheduler.py`, `limiter.py`, `taxonomy.py`, `config_service.py`, `telemetry.py` → `.context/notes/review/0.7.18/chunk-04-core-infra.md`

## Phase 2: API Layer (Chunks 05-06)

- [x] **Chunk 05: API Routes — Auth, Admin, System** — Review `app/api/` auth/admin routes (9 files): `__init__.py`, `routes.py`, `auth.py`, `decorators.py`, `schemas.py`, `admin.py`, `system.py`, `core.py`, `filters.py` → `.context/notes/review/0.7.18/chunk-05-api-auth.md`
- [x] **Chunk 06: API Routes — Domain Features** — Review `app/api/` domain routes (14 files): `items.py`, `manifestations.py`, `works.py`, `collections.py`, `scanner.py`, `lending.py`, `social.py`, `sharing.py`, `taxonomies.py`, `profile.py`, `public.py`, `feedback.py`, `roadmap.py`, `docs.py` → `.context/notes/review/0.7.18/chunk-06-api-domain.md`

## Phase 3: Ingestion & External APIs (Chunks 07-08)

- [x] **Chunk 07: Ingestion Strategies** — Review `app/strategies/` (9 files): `__init__.py`, `base.py`, `factory.py`, `book.py`, `video.py`, `audio.py`, `boardgame.py`, `puzzle.py`, `default.py` → `.context/notes/review/0.7.18/chunk-07-strategies.md`
- [x] **Chunk 08: External API Clients & Utils** — Review `app/utils/` (16 files): `__init__.py`, `http_client.py`, `isbn.py`, `covers.py`, `images.py`, `tmdb.py`, `bgg.py`, `discogs.py`, `musicbrainz.py`, `igdb.py`, `upc.py`, `allegro.py`, `json_utils.py`, `rclone_utils.py`, `llm_covers.py`, `vision.py` → `.context/notes/review/0.7.18/chunk-08-utils.md`

## Phase 4: Frontend Foundation (Chunks 09-10)

- [x] **Chunk 09: Frontend Types, API Client & Hooks** — Review `frontend/types/`, `frontend/lib/api/` (13 files): `frbr.ts`, `insights.ts`, `taxonomy.ts`, `client.ts`, `server-client.ts`, `hooks.ts`, `infinite-hooks.ts`, `admin.ts`, `social.ts`, `escalations.ts`, `profile.ts`, `intents.ts`, `boardgame.ts` → `.context/notes/review/0.7.18/chunk-09-fe-api.md`
- [x] **Chunk 10: Frontend Libs & Providers** — Review `frontend/lib/`, `frontend/hooks/`, provider components (12 files): `utils.ts`, `media.ts`, `media-badge.ts`, `permissions.ts`, `version.ts`, `escalation-utils.tsx`, `use-media-query.ts`, `providers.tsx`, `theme-provider.tsx`, `mode-toggle.tsx`, `language-toggle.tsx`, `cookie-consent.tsx` → `.context/notes/review/0.7.18/chunk-10-fe-libs.md`

## Phase 5: Frontend Components (Chunks 11-14)

- [x] **Chunk 11: Frontend — Dashboard & Landing** — Review dashboard + landing components (11 files): `navbar.tsx`, `navbar-wrapper.tsx`, `stats-cards.tsx`, `collection-insights.tsx`, `current-context.tsx`, `fresh-arrivals.tsx`, `type-distribution-chart.tsx`, `velocity-chart.tsx`, `footer.tsx`, `hero.tsx`, `global-stats.tsx` → `.context/notes/review/0.7.18/chunk-11-fe-dashboard.md`
- [x] **Chunk 12: Frontend — Collection & Filters** — Review collection components (13 files): `collection-grid.tsx`, `item-card.tsx`, `item-header.tsx`, `filter-bar.tsx`, `sidebar-filters.tsx`, `mobile-filter-drawer.tsx`, `add-to-collection-dropdown.tsx`, `collection-quick-add.tsx`, `bulk-add-toolbar.tsx`, `manage-collections-modal.tsx`, `share-collection-dialog.tsx`, `reading-roadmap.tsx`, `roadmap-view.tsx` → `.context/notes/review/0.7.18/chunk-12-fe-collection.md`
- [x] **Chunk 13: Frontend — Item Detail & Scanner** — Review item + scanner components (20 files): `hero-banner.tsx`, `item-header.tsx`, `item-actions.tsx`, `item-sidebar.tsx`, `item-tabs.tsx`, `item-timeline.tsx`, `extended-metadata.tsx`, `taxonomy-editor.tsx`, `discovery-pivot.tsx`, `multi-scan-gallery.tsx`, `qrcode-dialog.tsx`, `viewfinder.tsx`, `camera-capture.tsx`, `bottom-sheet.tsx`, `top-bar.tsx`, `manual-entry-form.tsx`, `disambiguation-sheet.tsx`, `success-card.tsx`, `error-boundary.tsx`, `multi-image-uploader.tsx` → `.context/notes/review/0.7.18/chunk-13-fe-item-scanner.md`
- [x] **Chunk 14: Frontend — Admin, Social, Misc** — Review admin + social + misc components (20 files): `user-management.tsx`, `group-management.tsx`, `instance-settings.tsx`, `frbr-editor.tsx`, `rbac-sheet.tsx`, `escalation-queue.tsx`, `cover-art-editor-wrapper.tsx`, `cover-canvas.tsx`, `editor-toolbar.tsx`, `info-sidebar.tsx`, `frbr-feedback.tsx`, `frbr-notes.tsx`, `star-rating.tsx`, `escalation-trigger.tsx`, `my-escalations.tsx`, `feedback-modal.tsx`, `feedback-detail-modal.tsx`, `cover-provenance.tsx`, `manifestation-actions.tsx`, `check-inventory.tsx` → `.context/notes/review/0.7.18/chunk-14-fe-admin-social.md`

## Phase 6: Frontend Pages & Config (Chunks 15-16)

- [x] **Chunk 15: Frontend — Pages & App Router** — Review Next.js pages (22 files): all `frontend/app/` pages and route handlers → `.context/notes/review/0.7.18/chunk-15-fe-pages.md`
- [x] **Chunk 16: Frontend — Configuration & Telemetry** — Review frontend config (10 files): `next.config.ts`, `proxy.ts`, `instrumentation.ts`, `vitest.config.ts`, `vitest.setup.ts`, `playwright.config.ts`, `declarations.d.ts`, `request.ts`, `browser-telemetry.tsx`, `browser-openobserve-rum.tsx` → `.context/notes/review/0.7.18/chunk-16-fe-config.md`

## Phase 7: Infrastructure (Chunks 17-18)

- [x] **Chunk 17: Infra — Docker & Deploy** — Review Docker Compose, orchestration, build (12 files): `docker-compose.yml`, `docker-compose.prebuilt.yml`, `docker-compose.monitoring.yml`, `docker-compose.ai_sandbox.yml`, `docker-compose.local-ai.yml`, `run.py`, `wsgi.py`, `run.sh`, `Makefile`, `pyproject.toml`, `requirements.txt`, `package.json` → `.context/notes/review/0.7.18/chunk-17-infra-docker.md`
- [x] **Chunk 18: Infra — Environment & Config** — Review env files, linter configs, shared data (13 files): `.env.example`, `.env.dev.example`, `.env.test`, `.pylintrc`, `.prettierrc.json`, `.stylelintrc.json`, `.markdownlint-cli2.jsonc`, `.dockerignore`, `.gitignore`, `shared/taxonomies.yaml`, `shared/format_mappings.yaml`, `shared/permissions.yaml`, `deploy/sandbox_proxy/proxy.py` → `.context/notes/review/0.7.18/chunk-18-infra-config.md`

## Phase 8: Scripts (Chunk 19)

- [x] **Chunk 19: Operational Scripts** — Review all `scripts/` (24 files): `init_db.py`, `init_auth.py`, `sync_permissions.py`, `sync_db_permissions.py`, `fetch_covers.py`, `retry_missing_covers.py`, `rebind_covers.py`, `restore_covers.py`, `generate_ai_covers.py`, `refetch_metadata.py`, `generate_taxonomy.py`, `migrate_legacy.py`, `fix_alembic.py`, `fix_physical_kinds.py`, `validate_release.py`, `validate_yaml.py`, `extract_changelog.py`, `extract_version.py`, `sync_version.py`, `generate_admin_token.py`, `sql_to_json.py`, `allegro_auth.py`, `archive_orphans.py`, `update_bgg_mechanics.py` → `.context/notes/review/0.7.18/chunk-19-scripts.md`

## Phase 9: Migrations (Chunks 20-21)

- [x] **Chunk 20: Migrations Part 1 — Foundation** — Review `migrations/env.py` + first ~15 migration files (foundation → auth → FRBR schema → video/boardgame → collections → lending → FTS) → `.context/notes/review/0.7.18/chunk-20-migrations-1.md`
- [x] **Chunk 21: Migrations Part 2 — Hardening & Social** — Review remaining ~15 migration files (social sharing → feedback → escalations → hardening → recent) → `.context/notes/review/0.7.18/chunk-21-migrations-2.md`

## Phase 10: Tests (Chunks 22-26)

- [x] **Chunk 22: Backend Tests — Core & Models** — Review core test files (~15): `conftest.py`, `test_ontology.py`, `test_ontology_shacl.py`, `test_auth.py`, `test_auth_security.py`, `test_permissions.py`, `test_search.py`, `test_frbr_events.py`, `test_frbr_type_change.py`, `test_data_manager.py`, `test_format_normalizer.py`, `test_db_pool_config.py`, `test_db_portability.py`, `test_models_social.py`, `test_expression_kind.py` → `.context/notes/review/0.7.18/chunk-22-tests-core.md`
- [x] **Chunk 23: Backend Tests — API Endpoints** — Review API test files (~15): `test_api.py`, `test_api_items.py`, `test_api_collections.py`, `test_api_scanner.py`, `test_api_covers.py`, `test_api_pagination.py`, `test_api_facets.py`, `test_api_public.py`, `test_api_escalations.py`, `test_api_visibility.py`, `test_api_items_lending.py`, `test_api_items_permissions.py`, `test_api_admin.py`, `test_api_profile_insights.py`, `test_api_status_filters.py` → `.context/notes/review/0.7.18/chunk-23-tests-api.md`
- [x] **Chunk 24: Backend Tests — Security & Hardening** — Review security test files (~15): `test_security_http.py`, `test_security_uploads.py`, `test_http_client.py`, `test_ssrf_dns_timeout.py`, `test_ssrf_redirect_type_safety.py`, `test_xxe_prevention.py`, `test_subprocess_hardening.py`, `test_rclone_hardening.py`, `test_admin_security.py`, `test_system_auth.py`, `test_telemetry_sanitization.py`, `test_payload_validation.py`, `test_mask_api_key.py`, `test_lint_safeguards.py`, `test_observability_infra.py` → `.context/notes/review/0.7.18/chunk-24-tests-security.md`
- [x] **Chunk 25: Backend Tests — Features & Remaining** — Review remaining backend test files (~20): scanner strategies, external API mocks, covers, audio/video/boardgame, social, tasks, resilience, migration backfill, etc. → `.context/notes/review/0.7.18/chunk-25-tests-features.md`
- [x] **Chunk 26: Frontend Tests — Components & E2E** — Review representative frontend test files (~20): Vitest component tests + Playwright E2E specs → `.context/notes/review/0.7.18/chunk-26-tests-frontend.md`

## Phase 11: Consolidation

- [x] **Consolidate all findings** — Create `99-consolidated-findings.md` aggregating all 🔴 CRITICAL and 🟡 MODERATE findings across all chunks, grouped by priority and area
- [x] **Create fix-plan change** — Create `review-0718-fix-plan` openspec change with implementable tasks derived from the consolidated findings; the plan should also include update to the rule/skill/workflow definitions - to ensure critical issues like those we just found will not re-appear, even in some different form or shape.

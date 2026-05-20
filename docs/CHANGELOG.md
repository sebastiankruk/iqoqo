# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.0] - 2026-05-20

### Added

- **Infinite Scroll**:
  - Replaced manual Previous/Next pagination in the Collection view with lazy loading via `IntersectionObserver`.
  - Two new React Query hooks: `useInfiniteItems` and `useInfiniteManifestations` using `useInfiniteQuery` with page-based `getNextPageParam`.
  - Vitest unit tests for infinite query hooks (`infinite-hooks.test.tsx`).
  - Playwright E2E test for scroll-triggered data fetching (`infinite_scroll.spec.ts`).

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

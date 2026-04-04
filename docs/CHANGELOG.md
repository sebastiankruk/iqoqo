# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

## [Unreleased]

## [0.3.0] - 2026-04-03

### Added

- **Ontology Expansion**: Support for Video (Film, Series) and Board Games via FRBRoo `ManifestationContribution` (Studio/Distributor) and `ContainerAggregation` (Box Contents).
- **Background Tasks**: Centralized APScheduler for recurring maintenance (e.g., daily automated backups).
- **Telemetry Hardening**: Refactored `LLMTelemetry` to handle high-concurrency event logging with non-blocking database indexes.
- **Scanner Fallbacks**: Added a `ManualEntryForm` UX to handle scenarios where barcode/ISBN lookups timeout or return no results.
- **Desktop Scanner UX**: `CameraCapture` now detects available media devices. If no rear camera is detected (e.g., Desktop), it automatically defaults to a clean Drag & Drop file uploader UI.
- **Smart Image Handling**: Integrated `OpenCV` to automatically detect, crop, and perspective-warp (fix skew) media covers from smartphone photos.

### Changed

- **Scheduler Gating**: Background tasks are now gated by `SCHEDULER_AUTOSTART` to prevent side effects in CLI and test environments.
- **Backup Script**: Isolated `sys.path` mutations to prevent environment pollution when the backup module is imported.

### Fixed

- **Image Rotation**: Applied `PIL.ImageOps.exif_transpose` within the image processing pipeline to automatically fix the 90-degree rotation bug caused by smartphone EXIF metadata tags during cover uploads.

### Database Migrations

- Introduced multi-schema architecture (`catalog`, `inventory`, `auth`).
- Added DB-level `CheckConstraint` to `ContainerAggregation` to ensure data integrity of board game components.

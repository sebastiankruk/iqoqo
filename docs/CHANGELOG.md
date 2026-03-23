# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

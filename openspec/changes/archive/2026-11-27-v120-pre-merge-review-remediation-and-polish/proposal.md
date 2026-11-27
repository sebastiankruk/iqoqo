## Why

A pre-merge Principal Code Review of `release/1.2.0` (`31cd1b5b`) identified two critical runtime/security defects, five moderate correctness/hygiene gaps (including unsynced `v1.2.0` OpenSpecs and an undated changelog), and two low-severity polish items that should be resolved before tagging and merging `v1.2.0`.

## What Changes

- **PostgreSQL `total_reading_minutes` HTTP 500 DoS & `Item.meta` Write Protection (`C171` — CRITICAL):**
  - Guard PostgreSQL `CAST(NULLIF(Item.meta ->> 'total_reading_minutes', '') AS INTEGER)` queries in `app/api/manifestations.py` (`get_manifestation` and `_compute_manifestation_stats`) via a shared dialect-safe helper (`^[0-9]{1,9}$` on PostgreSQL and numeric/digit checks on SQLite) so non-integer or overflowing strings return `NULL` instead of triggering `DataError` HTTP 500 for visitors.
  - Prevent `_update_physical_item` in `app/api/items.py` from overwriting derived session totals directly via a dedicated `_DERIVED_ITEM_META_KEYS` exclusion guard (preserving existing session-derived `total_reading_minutes`, `reading_sessions_count`, and `reading_sessions` instead of popping them), and harden integer reads in `_compute_reading_duration_summary` / `log_reading_session`.
- **Mobile Multi-Server Legacy Token Isolation, Logout Cleanup & Cold-Start Safety (`C171` — CRITICAL + MODERATE):**
  - Resolve active server ID asynchronously via `await getActiveServerId()` in `getAuthToken`, `setAuthToken`, and `removeAuthToken` (`frontend/lib/capacitor/storage.ts`) so cold-start `localStorage` eviction on native devices never falls back to un-scoped `AUTH_TOKEN_KEY` reads or writes.
  - Remove the cross-server legacy `AUTH_TOKEN_KEY` fallback in `getAuthToken()` whenever a scoped server profile is active, relying on idempotent legacy migration in `migrateLegacyServerStorage()`, and ensure logout clears `AUTH_TOKEN_KEY` cleanly so logged-out credentials cannot resurrect.
- **Non-Book Media `avg_reading_days` Parity (`C171` — MODERATE):**
  - Expand `_compute_manifestation_stats()` `started_at` progression statuses in `app/api/manifestations.py` beyond `("reading", "currently_reading")` to include `"listening"`, `"watching"`, `"playing"`, and `"building"` across music, video, board games, and LEGO.
- **External `physical_location` Sync in `TaxonomyEditor` (`C171` — MODERATE):**
  - Synchronize `locationInput` in `frontend/components/item/taxonomy-editor.tsx` when `item.physical_location` changes externally (for example after editing via `EditItemDialog`) without triggering React effect lint violations.
- **Backfill Script & Lightbox Accessibility Polish (`C171` — LOW):**
  - In `scripts/migrate_author_lod_to_contributors.py`, delete the duplicate `loser` `SemanticLink` and call `session.flush()` *before* updating `winner.entity_type` / `winner.entity_id`, matching its inline comment and protecting against future unique constraints; drop the unused `--yes` argparse flag while retaining mandatory `_confirm_production_execution()` checks in `production`.
  - Add an `Escape` key handler in `frontend/components/manifestation/manifestation-covers-gallery.tsx` to close the cover lightbox preview dialog.
- **Release Finalization — OpenSpec Sync/Archive & Changelog Date (`C171` — MODERATE):**
  - Sync delta specs into `openspec/specs/` and archive the 9 completed `v1.2.0` OpenSpec changes (`C154`, `C155`, `C156`, `C157`, `C158`, `C163`, `C164`, `C167`, `C169`) plus `C171` on completion, while keeping `docs-conciseness-v120-sync-and-svg-blueprints` (`C168`, Task `3.2` waiting for human SVG regeneration) and `frbr-expression-manifestation-rdf-separation-v130` (`C170`, `v1.3.0`) active.
  - Update `docs/CHANGELOG.md` `[1.2.0]` header from `TBD` to `2026-11-27` and document `C171` fixes.

## Capabilities

### New Capabilities

- `v120-pre-merge-review-remediation`: Pre-merge security, reliability, accessibility, and release-hygiene requirements for `release/1.2.0` covering stats DoS hardening, multi-media duration parity, Capacitor multi-server token isolation, UI state synchronization, backfill ordering, and OpenSpec/changelog finalization.

### Modified Capabilities

<!-- None: all v1.2.0 delta specs remain in sibling unarchived change folders until final C171 archive sync, so this remediation consolidates its delta requirements under `v120-pre-merge-review-remediation` without conflicting with sibling changes. -->

## Impact

- Affected backend files: `app/api/manifestations.py`, `app/api/items.py`, `scripts/migrate_author_lod_to_contributors.py`, `tests/`.
- Affected frontend files: `frontend/lib/capacitor/storage.ts`, `frontend/components/item/taxonomy-editor.tsx`, `frontend/components/manifestation/manifestation-covers-gallery.tsx`, `frontend/__tests__/`.
- Affected docs/release files: `docs/CHANGELOG.md`, `openspec/specs/`, `openspec/changes/`, `.context/notes/`.

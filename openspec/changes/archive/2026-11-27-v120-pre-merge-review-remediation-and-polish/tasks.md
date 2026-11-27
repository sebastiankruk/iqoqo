## 1. Backend Stats Security & Multi-Media Parity

- [x] 1.1 Extract `_safe_total_reading_minutes_expr(dialect_name)` in `app/api/manifestations.py` (guarding PostgreSQL integer casts with regex `^[0-9]{1,9}$` and SQLite type/digit checks) and use it in both `get_manifestation()` and `_compute_manifestation_stats()`, verifying non-integer/overflow strings return `NULL` without HTTP `500`
- [x] 1.2 Add a separate `_DERIVED_ITEM_META_KEYS` (`{"total_reading_minutes", "reading_sessions_count", "reading_sessions"}`) exclusion guard in `app/api/items.py` (`_update_physical_item`) — without adding those keys to `_DISALLOWED_ITEM_META_KEYS` (which pops keys) — so direct `PUT`/`PATCH /api/items/<id>` payloads neither overwrite nor erase session-derived totals, and safely parse integer totals in `_compute_reading_duration_summary()` / `log_reading_session()`, verified by backend pytest coverage
- [x] 1.3 Include `"listening"`, `"watching"`, `"playing"`, and `"building"` in `_compute_manifestation_stats()` `started_at` progression status filtering (`app/api/manifestations.py`), verified by non-book `avg_reading_days` pytest assertions

## 2. Mobile Multi-Server Auth Isolation

- [x] 2.1 Update `getAuthToken`, `setAuthToken`, and `removeAuthToken` in `frontend/lib/capacitor/storage.ts` to await `getActiveServerId()` instead of calling synchronous `getSyncActiveServerId()`
- [x] 2.2 Remove cross-server legacy `AUTH_TOKEN_KEY` fallback in `getAuthToken()` when a scoped server profile is active and ensure `removeAuthToken()` clears stale legacy `AUTH_TOKEN_KEY` cleanly, verified by Vitest cold-start, multi-server switch, and logout isolation tests

## 3. Frontend Location Sync & Lightbox Accessibility

- [x] 3.1 Synchronize `locationInput` in `frontend/components/item/taxonomy-editor.tsx` when `item.physical_location` updates externally without `useEffect` setState lint violations, verified by Vitest tests
- [x] 3.2 Add an `Escape` key handler in `frontend/components/manifestation/manifestation-covers-gallery.tsx` to close the cover lightbox preview dialog, verified by Vitest keydown test

## 4. Backfill Script Polish

- [x] 4.1 Update `scripts/migrate_author_lod_to_contributors.py` to delete `loser` and call `session.flush()` before updating `winner.entity_type` / `winner.entity_id`, and remove the unused `--yes` argparse flag while retaining mandatory `_confirm_production_execution()` checks, verified by `tests/test_author_lod_backfill.py`

## 5. Tests & Verification

- [x] 5.1 Add/update regression tests in `tests/test_manifestation_stats.py`, `tests/test_item_location.py` (or `tests/test_api_items_078.py`), `tests/test_author_lod_backfill.py`, `frontend/__tests__/lib/capacitor/storage.test.ts`, `frontend/__tests__/components/item/taxonomy-editor-location.test.tsx`, and `frontend/__tests__/components/manifestation/manifestation-covers-and-stats.test.tsx`
- [x] 5.2 Run `IQOQO_AI_MODE=1 make format-python && IQOQO_AI_MODE=1 make format-js && IQOQO_AI_MODE=1 make lint && IQOQO_AI_MODE=1 make test-parallel && IQOQO_AI_MODE=1 make secret-scan` and confirm zero failures

## 6. v1.2.0 OpenSpec Sync/Archive & Changelog Finalization

- [x] 6.1 Run `openspec archive -y` (syncing delta specs into `openspec/specs/`) for the 9 completed `v1.2.0` changes (`isbn-lookup-timeout-budget-and-scanner-parity-v120`, `preview-clone-reencrypt-key-propagation-and-tag-parity`, `mobile-multi-server-switching-v120`, `physical-item-location-tagging-v120`, `manifestation-covers-read-stats-popularity-v120`, `aws-s3-archive-backup-repair-v120`, `graph-person-lod-canonical-dedup-v120`, `c157-c158-search-facets-openapi-and-test-hardening-v120`, `author-lod-contributor-linking-and-shacl-ontology-sync`) and `v120-pre-merge-review-remediation-and-polish` (`C171`), keeping `docs-conciseness-v120-sync-and-svg-blueprints` (`C168`, Task `3.2` waiting on human SVGs) and `frbr-expression-manifestation-rdf-separation-v130` (`C170`, `v1.3.0`) active
- [x] 6.2 Replace `## [1.2.0] - TBD` with `## [1.2.0] - 2026-11-27` in `docs/CHANGELOG.md`, add `C171` entries, update `.context/notes/` completion checkboxes, and re-run `IQOQO_AI_MODE=1 make lint-markdown && IQOQO_AI_MODE=1 make secret-scan`

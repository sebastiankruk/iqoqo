## 1. Reading Session Permission Guard & Public Note Redaction (`M-01`, `M-02` — `C115`)

- [x] 1.1 Decorate `log_reading_session` in `app/api/items.py` with `@require_permission(PermissionName.WRITE_ITEM)` and call `reject_if_federation_head_item_write()` before mutating `item.meta`, and verify with `IQOQO_AI_MODE=1 .venv/bin/pytest tests/test_reading_sessions.py`
- [x] 1.2 Strip `"reading_sessions"` from a shallow copy of `item.meta` in `_get_physical_item_detail` (`app/api/items.py`) when `not (is_owner or is_admin)` while preserving `reading_duration_summary`, and verify with `IQOQO_AI_MODE=1 .venv/bin/pytest tests/test_reading_sessions.py`

## 2. Wishlist Reactivation, Edition Binding Upgrade, Backslash Escaping & SA 2.0 (`M-03`, `L-01`, `L-07` — `C121`)

- [x] 2.1 Update `upsert_wishlist_intent_for_manifestation` in `app/core/wishlist_service.py` so the existing-intent branch resets `intent.status = default_progress` when `intent.status == "fulfilled"` (or when `status` is explicitly provided), updates `intent.is_hidden = is_hidden`, and upgrades `intent.expression_id = expr_id` and `intent.manifestation_id = manif_id` when provided, and verify with `IQOQO_AI_MODE=1 .venv/bin/pytest tests/test_wishlist_actions_v103.py`
- [x] 2.2 Replace manual `%`/`_` replacement in `get_wishlist` (`app/api/wishlist.py`) with `escape_ilike_term(q.strip().lower())` from `app.core.search_service` and migrate legacy `.query` calls in `app/api/wishlist.py` to SQLAlchemy 2.0 `select(UserWorkIntent)`, and verify with `IQOQO_AI_MODE=1 .venv/bin/pytest tests/test_wishlist_actions_v103.py tests/test_wishlist_api.py`

## 3. Shared Collection PostgreSQL FTS Offset, LEGO Wishlist Slicing & OpenAPI 3.1 Contract (`L-02`, `L-03`, `L-04` — `C118`)

- [x] 3.1 Fix PostgreSQL FTS offset handling in `fetch_shared_collection_by_token` and `public_shared_collection` (`app/api/public_items.py`) so `SearchService.search_items` receives `offset=max(0, offset)` without double-offsetting the outer `Item.id.in_(item_ids)` query, and add `"want_to_build"` + pagination slicing (`offset_val`/`limit_val`) to the `is_wish_list` `UserWorkIntent` block in `public_shared_collection`, verifying with `IQOQO_AI_MODE=1 .venv/bin/pytest tests/test_shared_collection_ai_feed.py`
- [x] 3.2 Update `app/api/docs.py` to add `page` and `per_page` query parameters on `/api/public/share/{token}` and `/api/public/rdf/share/{token}`, attach `ReadingSessionCreateSchema` (`duration_minutes`, `pages_read`, `note`) `requestBody` and `201` response to `POST /api/items/{item_id}/reading-sessions`, and add `"cartographic_map"` and `"map"` to `Expression.content_type` enum, verifying with `IQOQO_AI_MODE=1 .venv/bin/pytest tests/test_openapi_spec.py`

## 4. Wishlist UI Localization (`L-05`)

- [x] 4.1 Add EN and PL translation keys for wishlist category filter options (`categoryText`, `categoryMusic`, `categoryMovie`, `categoryBoardGame`, `categoryPuzzle`, `categoryLego`) and `AddToCollectionDropdown` actions (`addToCollection`, `viewWishlist`, `addToWishlist`, `addToMyLibrary`, `noFolder`, `noNamedFolders`) to `frontend/messages/en.json` and `frontend/messages/pl.json`, wire them in `frontend/app/wishlist/page.tsx` and `frontend/components/collection/add-to-collection-dropdown.tsx`, and verify with `cd frontend && npx vitest run __tests__/app/wishlist/page.test.tsx __tests__/components/manifestation/manifestation-wishlist.test.tsx`

## 5. Comprehensive Regression Test Suite (`/test-craftsman`)

- [x] 5.1 Add backend regression tests in `tests/test_reading_sessions.py`, `tests/test_wishlist_actions_v103.py`, `tests/test_shared_collection_ai_feed.py`, and `tests/test_openapi_spec.py` covering read-only PAT `403` and `FEDERATION_HEAD_MODE` `403` on `POST /api/items/<id>/reading-sessions`, non-owner `reading_sessions` note redaction on `GET /api/items/<id>`, `"fulfilled"` `UserWorkIntent` reactivation + edition binding upgrade, `GET /api/wishlist?q=Dune\` backslash escaping, page 2+ shared collection search offset and `"want_to_build"` wishlist pagination, and OpenAPI 3.1 contract assertions, verifying all pass via `IQOQO_AI_MODE=1 .venv/bin/pytest tests/test_reading_sessions.py tests/test_wishlist_actions_v103.py tests/test_shared_collection_ai_feed.py tests/test_openapi_spec.py`
- [x] 5.2 Add frontend regression assertions in `frontend/__tests__/app/wishlist/page.test.tsx` and `frontend/__tests__/components/manifestation/manifestation-wishlist.test.tsx` verifying localized category filter options and dropdown actions, and run `IQOQO_AI_MODE=1 make test-frontend`

## 6. Concise Documentation, Changelog & Roadmap Synchronization (`L-06` — `/tech-comm-expert`)

- [x] 6.1 Update `docs/CHANGELOG.md` under `## [1.0.3] - 2026-11-18` with concise, scannable entries for all `v1.0.3` changes (`C115`–`C125`), and verify with `npx markdownlint-cli2 "docs/CHANGELOG.md"`
- [x] 6.2 Check off `[x]` for all `v1.0.3` items and list `C115`–`C125` in `.context/notes/iqoqo roadmap.md`, `.context/notes/iqoqo development notes.md`, `.context/notes/plan/1.0.x-release-plan.md` (updating line 14 to `v1.0.3` and adding `C125`), `.agents/skills/*/SKILL.md`, and `.gemini/gems/*.md`, and verify with `IQOQO_AI_MODE=1 .venv/bin/pytest tests/test_ai_skills_integrity.py`
- [x] 6.3 Run `make format-python`, `make format-js`, `IQOQO_AI_MODE=1 make secret-scan`, `IQOQO_AI_MODE=1 make lint`, and `IQOQO_AI_MODE=1 make test-parallel` to verify zero regressions across all test and lint gates

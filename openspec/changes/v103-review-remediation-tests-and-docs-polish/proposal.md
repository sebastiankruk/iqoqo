## Why

The combined Principal + Gemini Argon release audit for `v1.0.3` (`release/1.0.3` / PR #420, `.context/notes/review/1.0.3/principal-review-release-1.0.3.md` and `review-release-1.0.3-pr-420.md`) identified 2 Moderate (`🟡`) and 7 Low (`🟢`) findings across reading session permission/privacy enforcement (`C115`), wishlist reactivation and search escaping (`C121`), shared collection pagination/search offsets (`C118`), OpenAPI 3.1 contract parity, wishlist UI localization, and `v1.0.3` changelog/roadmap synchronization. Addressing all Moderate and Low findings in a pre-tag remediation change (**C125**, scheduled for `v1.0.3`) with targeted regression tests and concise documentation ensures `v1.0.3` tags cleanly with zero security, ontology, or documentation debt.

## What Changes

- **Reading Session PAT Scope, Federation Hub Write Guard & Public Note Redaction (`M-01`, `M-02` — `C115` Remediation)**:
  - Decorate `POST /api/items/<int:item_id>/reading-sessions` (`log_reading_session` in `app/api/items.py`) with `@require_permission(PermissionName.WRITE_ITEM)` and enforce `reject_if_federation_head_item_write()` so read-only Personal Access Tokens (`iqo_*` scoped only to `read:catalog` / `read:items`) and `FEDERATION_HEAD_MODE` instances cannot mutate `Item.meta["reading_sessions"]`.
  - Redact or strip `reading_sessions` from `item_data["meta"]` in `_get_physical_item_detail` (`app/api/items.py`) when the caller is neither the item owner nor an admin (`not (is_owner or is_admin)`), keeping private reading session notes confidential while preserving the public `reading_duration_summary` (`total_minutes`, `sessions_count`, `elapsed_days`) on public items.
- **Wishlist Fulfilled Reactivation, Edition Binding Upgrade & SQLAlchemy 2.0 / ILIKE Hardening (`M-03`, `L-01`, `L-07` — `C121` Remediation)**:
  - Update `upsert_wishlist_intent_for_manifestation()` in `app/core/wishlist_service.py` so re-wishlisting a work with an existing `UserWorkIntent` row resets `intent.status = default_progress` when `intent.status == "fulfilled"` (or when an explicit `status` is passed), resets `intent.is_hidden = is_hidden`, and upgrades `intent.expression_id` and `intent.manifestation_id` when a specific manifestation (`manif_id` / `expr_id`) is provided.
  - Replace manual `.replace("%", r"\%").replace("_", r"\_")` in `get_wishlist()` (`app/api/wishlist.py`) with `escape_ilike_term(q.strip().lower())` from `app.core.search_service` so queries containing or ending with `\` cannot escape the trailing `%` wildcard or raise PostgreSQL `ESCAPE` errors.
  - Migrate remaining legacy `db.session.query()` / `UserWorkIntent.query` calls in `app/api/wishlist.py` to SQLAlchemy 2.0 `select(UserWorkIntent)`.
- **Shared Collection Pagination, PostgreSQL FTS Offset & LEGO Wishlist Parity (`L-02`, `L-04` — `C118` Remediation)**:
  - Pass `offset=max(0, offset)` (or `limit=limit + max(0, offset)`) appropriately in `fetch_shared_collection_by_token()` and `public_shared_collection()` (`app/api/public_items.py`) when `SearchService.search_items()` runs on PostgreSQL so page 2+ (`offset >= limit`) returns the expected paginated slice rather than an empty result set.
  - Add `"want_to_build"` to `_INTENT_LEVEL_STATUSES` in `public_shared_collection()` (`app/api/public_items.py`) and slice/paginate `UserWorkIntent` entries consistently when `page` and `per_page` are requested on a shared wishlist collection.
- **OpenAPI 3.1 Contract Parity for v1.0.3 Endpoints (`L-03`)**:
  - Add `page` and `per_page` query parameters to `/api/public/share/{token}` in `app/api/docs.py`.
  - Document the `POST /api/items/{item_id}/reading-sessions` `requestBody` (`duration_minutes`, `pages_read`, `note`) and `201` response in `app/api/docs.py`.
  - Add `"cartographic_map"` and `"map"` to the `Expression.content_type` schema enum in `app/api/docs.py`.
- **Wishlist UI Localization (`L-05`)**:
  - Replace hardcoded English category `<option>` labels in `frontend/app/wishlist/page.tsx` and hardcoded action strings in `frontend/components/collection/add-to-collection-dropdown.tsx` with `next-intl` translation keys in `frontend/messages/en.json` and `frontend/messages/pl.json`.
- **Concise v1.0.3 Changelog, Roadmap & AI Persona Synchronization (`L-06` — `/tech-comm-expert`)**:
  - Stamp `## [1.0.3] - 2026-11-18` in `docs/CHANGELOG.md` and concisely document all 10 `v1.0.3` changes (`C115`–`C124`), adding crisp entries for `C115`, `C116`, `C117`, `C121`, `C123`, and `C124` while tightening verbose bullets.
  - Check off `[x]` for all `v1.0.3` items and list `C115`–`C125` across `.context/notes/iqoqo roadmap.md`, `.context/notes/iqoqo development notes.md`, and `.context/notes/plan/1.0.x-release-plan.md` (updating line 14 from `v0.9.4` to `v1.0.3`).
  - Update the `v1.0.3` OpenSpec range from `C115–C120` to `C115–C125` across `.agents/skills/*/SKILL.md` and `.gemini/gems/*.md` while preserving `tests/test_ai_skills_integrity.py` invariants.
- **Comprehensive Regression Test Coverage (`test-craftsman`)**:
  - Add backend Pytest and frontend Vitest regression tests covering every issue detected during `v1.0.3` development and the release review (PAT scope & Federation Hub rejection on `log_reading_session`, public item `reading_sessions` note redaction, re-wishlisting `"fulfilled"` intents and edition binding upgrades, trailing-backslash `q=foo\` wishlist `ILIKE` search, PostgreSQL FTS offset pagination & `"want_to_build"` shared wishlist slicing, OpenAPI 3.1 schema assertions for `/api/items/{item_id}/reading-sessions` and `/api/public/share/{token}`, and localized `WishlistPage` / `AddToCollectionDropdown` rendering).

## Capabilities

### New Capabilities
- `v103-review-remediation-and-polish`: Pre-tag `v1.0.3` security, privacy, wishlist lifecycle, shared collection pagination, OpenAPI 3.1 contract, localization, documentation, and regression test hardening (`C125`).

### Modified Capabilities
- `item-reading-duration-tracking`: Enforce `PermissionName.WRITE_ITEM` and `reject_if_federation_head_item_write()` on `POST /api/items/<int:item_id>/reading-sessions`, and redact private `reading_sessions` notes from `GET /api/items/<int:item_id>` for non-owners/non-admins.
- `wishlist-item-actions-and-acquisition-flow`: Reactivate `"fulfilled"` `UserWorkIntent` rows and upgrade edition bindings (`expression_id`, `manifestation_id`) on re-wishlist, escape backslashes in `GET /api/wishlist?q=`, and localize wishlist UI controls.
- `shared-collection-ai-feed`: Fix PostgreSQL FTS search offset pagination on `page >= 2` and paginate `UserWorkIntent` rows (including `want_to_build`) on shared wishlist collections.
- `openapi-31-contract-and-ai-skills`: Document `POST /api/items/{item_id}/reading-sessions` request body, `page`/`per_page` on `/api/public/share/{token}`, and `"cartographic_map"` in `Expression.content_type`.

## Impact

- **Backend (`app/`)**: `app/api/items.py`, `app/core/wishlist_service.py`, `app/api/wishlist.py`, `app/api/public_items.py`, `app/api/docs.py`.
- **Frontend (`frontend/`)**: `frontend/app/wishlist/page.tsx`, `frontend/components/collection/add-to-collection-dropdown.tsx`, `frontend/messages/en.json`, `frontend/messages/pl.json`.
- **Documentation & Planning (`docs/`, `.context/notes/`, `.agents/`, `.gemini/`)**: `docs/CHANGELOG.md`, `.context/notes/iqoqo roadmap.md`, `.context/notes/iqoqo development notes.md`, `.context/notes/plan/1.0.x-release-plan.md`, `.agents/skills/*/SKILL.md`, `.gemini/gems/*.md`.
- **Tests (`tests/`, `frontend/__tests__/`)**: `tests/test_reading_sessions.py`, `tests/test_wishlist_actions_v103.py`, `tests/test_shared_collection_ai_feed.py`, `tests/test_openapi_spec.py`, `frontend/__tests__/app/wishlist/page.test.tsx`, `frontend/__tests__/components/manifestation/manifestation-wishlist.test.tsx`.

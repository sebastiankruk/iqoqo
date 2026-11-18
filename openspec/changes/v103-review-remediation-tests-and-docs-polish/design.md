## Context

`release/1.0.3` (PR #420) integrates ten OpenSpec changes (`C115`–`C124`). The combined Principal Code Review and Gemini Code Review Partner audit (`.context/notes/review/1.0.3/principal-review-release-1.0.3.md` and `review-release-1.0.3-pr-420.md`) verified that all ten features are implemented and tested, and flagged 2 Moderate (`🟡`) and 7 Low (`🟢`) findings that should be resolved in a single pre-tag remediation change (**C125**) before tagging `v1.0.3`. See `proposal.md` for the full scope.

## Goals / Non-Goals

**Goals:**
- Enforce `PermissionName.WRITE_ITEM` and `reject_if_federation_head_item_write()` on `POST /api/items/<int:item_id>/reading-sessions` and strip private `reading_sessions` notes from `GET /api/items/<int:item_id>` responses for non-owners/non-admins.
- Ensure `upsert_wishlist_intent_for_manifestation()` reactivates `"fulfilled"` `UserWorkIntent` rows, upgrades `expression_id` and `manifestation_id` when a specific manifestation is wishlisted, escapes backslashes via `escape_ilike_term()` in `GET /api/wishlist`, and uses SQLAlchemy 2.0 `select()`.
- Fix PostgreSQL FTS offset handling and `UserWorkIntent` pagination slicing (including `"want_to_build"`) on shared collections in `app/api/public_items.py`.
- Close OpenAPI 3.1 contract drift in `app/api/docs.py` for `/api/items/{item_id}/reading-sessions`, `/api/public/share/{token}`, and `Expression.content_type`.
- Localize hardcoded English strings in `WishlistPage` and `AddToCollectionDropdown` (`en.json` / `pl.json`).
- Keep `docs/CHANGELOG.md` and `.context/notes/*` accurate, complete (`C115`–`C125`), and concise per `/tech-comm-expert` standards.
- Achieve full regression test coverage across backend (`pytest`) and frontend (`Vitest`) for all areas touched in `v1.0.3` and flagged in the review per `/test-craftsman` standards.

**Non-Goals:**
- Introducing new database tables or Alembic migrations (all fixes operate on existing `Item.meta` and `UserWorkIntent` columns).
- Modifying `v1.1.0` backlog items (Valkey migration, ISSN serials ontology).

## Decisions

### 1. Reading Session Permission Guard & Public Note Redaction (`app/api/items.py`)
- **Decision**:
  1. Add `@require_permission(PermissionName.WRITE_ITEM)` beneath `@require_auth` on `log_reading_session(item_id: int)` and invoke `guard_err = reject_if_federation_head_item_write()` before mutating `item.meta`.
  2. In `_get_physical_item_detail(item_id: int)`, construct `public_meta = dict(item.meta) if isinstance(item.meta, dict) else item.meta`; when `not (is_owner or is_admin)` and `isinstance(public_meta, dict)`, remove `"reading_sessions"` from `public_meta` (`public_meta.pop("reading_sessions", None)`). `reading_duration_summary` is still computed from `item` (`total_minutes`, `sessions_count`, `started_at`, `finished_at`, `elapsed_days`), so public duration stats remain intact while individual session timestamps and private `note` fields are never exposed to non-owners.
- **Rationale**: Every other physical item mutation endpoint (`create_item`, `add_item`, `add_item_by_manifestation`, `add_item_manual`, `add_item_to_collection`) enforces `@require_permission(PermissionName.WRITE_ITEM)` and `reject_if_federation_head_item_write()`. Stripping `reading_sessions` from the shallow copy of `item.meta` avoids mutating the SQLAlchemy session state while protecting collector privacy.

### 2. Wishlist Intent Reactivation, Edition Upgrade & Backslash Escaping (`app/core/wishlist_service.py`, `app/api/wishlist.py`)
- **Decision**:
  1. In `upsert_wishlist_intent_for_manifestation()`, update the `else:` branch (when an existing `UserWorkIntent` for `(user_id, work_id)` is found):
     - If `expr_id is not None`: set `intent.expression_id = expr_id`.
     - If `manif_id is not None`: set `intent.manifestation_id = manif_id`.
     - If `intent.status == "fulfilled"` or `status is not None`: set `intent.status = default_progress`.
     - Set `intent.is_hidden = is_hidden`.
  2. In `app/api/wishlist.py:get_wishlist`, import `escape_ilike_term` from `app.core.search_service` and replace `q.strip().lower().replace("%", r"\%").replace("_", r"\_")` with `escape_ilike_term(q.strip().lower())`.
  3. Replace the 5 legacy `db.session.query(UserWorkIntent)` / `UserWorkIntent.query` calls in `app/api/wishlist.py` with SQLAlchemy 2.0 `db.session.execute(select(UserWorkIntent)...)`.
- **Rationale**: A collector who previously owned or fulfilled a work and later wishlists a specific new edition (e.g. a collector's hardcover or remastered vinyl pressing) expects that edition to appear on `/wishlist` and `/manifestation/[id]`. Using `escape_ilike_term()` reuses the tested canonical helper that escapes `\` before `%` and `_`.

### 3. Shared Collection PostgreSQL FTS Offset & Wishlist Pagination (`app/api/public_items.py`)
- **Decision**:
  1. In `fetch_shared_collection_by_token()` (`app/api/public_items.py:317-338`), when `db.engine.dialect.name == "postgresql"` and `search_query` is present, pass `limit=limit, offset=max(0, offset)` directly to `SearchService.search_items()` and do not apply a second `.offset(max(0, offset))` on the `Item.id.in_(item_ids)` query (which already has at most `limit` IDs for that page). In `public_shared_collection()` (`app/api/public_items.py:680-723`), increase the `SearchService.search_items` cap to `MAX_SHARED_COLLECTION_LIMIT` (`2000`) so pages up to the 2,000-item share cap resolve consistently.
  2. In `public_shared_collection()` (`app/api/public_items.py:733-838`), add `"want_to_build"` to `_INTENT_LEVEL_STATUSES`. Compute `intent_count` and slice `UserWorkIntent` rows when `items` has room on the current page (`remaining_limit = max(0, limit_val - len(items_list))`, `intent_offset = max(0, offset_val - total_count)`) so shared wishlists paginate accurately instead of duplicating all intents on every page.
- **Rationale**: Prevents empty page 2+ responses on PostgreSQL FTS-filtered shared collections and prevents multi-page shared wishlists from returning unbounded duplicate intent lists.

### 4. OpenAPI 3.1 Contract Completion (`app/api/docs.py`)
- **Decision**:
  1. Add `"cartographic_map"` and `"map"` to `Expression.properties.content_type.enum` in `create_spec()`.
  2. In `assemble_complete_openapi_spec()`, add `page` (`integer`, minimum 1) and `per_page` (`integer`, minimum 1, maximum 200) to `share_query_params` for `/api/public/share/{token}` and `/api/public/rdf/share/{token}`.
  3. Add an explicit `elif openapi_path == "/api/items/{item_id}/reading-sessions" and method == "post":` branch documenting `requestBody` (`duration_minutes` required `1..1440`, `pages_read` optional `1..50000`, `note` optional `maxLength: 500`) and `201` response (`SuccessEnvelope`).
- **Rationale**: Keeps `/api/docs/openapi.json` 100% aligned with the runtime Pydantic schemas (`ReadingSessionCreateSchema`) and query parameters introduced in `C115` and `C118`.

### 5. Concise Documentation Architecture (`/tech-comm-expert`) & Test Matrix (`/test-craftsman`)
- **Decision**:
  - **Documentation**: In `docs/CHANGELOG.md`, replace `## [1.0.3] - TBD` with `## [1.0.3] - 2026-11-18`. Consolidate the 15-line single-sentence `C118` paragraph into scannable sub-bullets and add concise, high-signal bullets for `C115`, `C116`, `C117`, `C121`, `C123`, `C124`, and `C125`. Sync checkboxes and `C115`–`C125` ranges in `.context/notes/iqoqo roadmap.md`, `.context/notes/iqoqo development notes.md`, `.context/notes/plan/1.0.x-release-plan.md`, `.agents/skills/*/SKILL.md`, and `.gemini/gems/*.md`.
  - **Testing**: Extend existing test modules (`tests/test_reading_sessions.py`, `tests/test_wishlist_actions_v103.py`, `tests/test_shared_collection_ai_feed.py`, `tests/test_openapi_spec.py`, `frontend/__tests__/app/wishlist/page.test.tsx`, `frontend/__tests__/components/manifestation/manifestation-wishlist.test.tsx`) rather than creating redundant test files, ensuring fast parallel execution (`IQOQO_AI_MODE=1 make test-parallel`).

## Risks / Trade-offs

- **[Risk] Changing `v1.0.2` baseline text in `.agents/skills/*/SKILL.md` could break `tests/test_ai_skills_integrity.py`** → **Mitigation**: Keep `v1.0.2` as the shipped baseline on `main` and update only the `v1.0.3` change range (`C115`–`C120` → `C115`–`C125`) under `## Upcoming (v1.0.3 & Beyond)`, verifying `pytest tests/test_ai_skills_integrity.py` passes.
- **[Risk] Stripping `reading_sessions` from `item.meta` in `_get_physical_item_detail` could mutate the ORM instance in session** → **Mitigation**: Copy `item.meta` (`dict(item.meta)`) before popping `"reading_sessions"` for non-owner/non-admin responses, leaving `item.meta` on the SQLAlchemy model untouched.

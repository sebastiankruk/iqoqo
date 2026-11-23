## Why

Second-pass Principal + Gemini code review of `release/1.1.0` (PR #433, `.context/notes/review/1.1.0/principal-review-release-1.1.0-pass-2.md`) identified one critical privacy regression in `SearchService.search_items()` where `include_hidden=False` combined with `owner_only=True` matches the owner's `private` and `friends_only` items, a one-line `include_hidden` mismatch in `get_shared_collection()`, two residual unbatched queries in `GraphService`, and minor documentation/release-tracking finalization items (`docs/COVERS_SETUP.md`, `docs/API.md`, `docs/CHANGELOG.md`, and `.context/notes/` plans). Fixing all of these in a single pre-merge OpenSpec change (`C138`) completes `v1.1.0` readiness.

## What Changes

- **Restore Strict `include_hidden=False` Privacy Isolation in `SearchService` (`app/core/search_service.py`)**:
  - In `_pg_item_fts` and `_ilike_item_search`, keep `if not filters.include_hidden:` strictly as `AND i.is_hidden = FALSE` (`Item.is_hidden.is_(False)`), removing the `OR (i.owner_id = :user_id AND i.visibility IN ('friends_only', 'shared', 'private'))` branch that bypassed `include_hidden=False` when `owner_only=True`.
  - When `filters.visibility` is supplied with `filters.include_hidden=True` and includes `"public"` alongside non-public tiers (`friends_only`, `shared`, `private`), guard the `"public"` tier with `is_hidden = FALSE` (`(i.visibility = 'public' AND i.is_hidden = FALSE) OR i.visibility IN :non_public_vis`) so hidden-public items remain excluded while `friends_only` (`is_hidden=True`) items are preserved.
- **Align `get_shared_collection()` FTS Search With Friend Bonus & `friends_and_public` (`app/api/public_items.py`)**:
  - Update `get_shared_collection()` (`app/api/public_items.py:826`) to pass `include_hidden=include_hidden or any(v != "public" for v in allowed_vis)` into `SearchService.search_items()`, matching `fetch_shared_collection_with_cache_policy()` (`app/api/public_items.py:382`).
- **Bound & Batch Residual `GraphService` Queries (`app/core/graph_service.py`)**:
  - Add `.limit(MAX_GRAPH_NODES)` to the `Manifestation` query inside `GraphService._expand_expression()` so serial expressions with hundreds of issues do not load unbounded rows.
  - Batch the `ContainerAggregation.container_work_id` parent `Work` lookup in `GraphService._expand_item()` with `select(Work).where(Work.id.in_(...))` instead of per-row `db.session.get(Work, ...)` inside a loop.
- **Documentation & Pre-Tag Release Finalization (`docs/COVERS_SETUP.md`, `docs/API.md`, `docs/CHANGELOG.md`, `.context/notes/`)**:
  - Align serial Vision OCR response example keys in `docs/COVERS_SETUP.md` and `docs/API.md` with `app/utils/vision.py:_parse_json_response()` snake_case output (`issn`, `indeks`, `issue_number`, `volume`, `publication_year`, `publication_month`, `cover_headline`), and document `GET /api/lookup/<barcode>` alongside `GET /api/scanner/preview/<barcode>`.
  - Stamp `## [1.1.0] - 2026-11-20` in `docs/CHANGELOG.md` and mark `C126`–`C138` complete in `.context/notes/plan/1.1.x-release-plan.md`, `.context/notes/iqoqo roadmap.md`, and `.context/notes/iqoqo development notes.md`.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `shared-collection-visibility-scope`: Require `SearchService.search_items()` to enforce strict `is_hidden = FALSE` when `include_hidden=False` (even when `owner_only=True`), guard `"public"` visibility against `is_hidden=True` when mixed with non-public tiers, and keep `get_shared_collection()` and `fetch_shared_collection_with_cache_policy()` consistent for query-filtered `friends_and_public` and Friend Bonus shares.
- `visual-frbr-relation-graph`: Require `GraphService._expand_expression()` to bound `Manifestation` queries by `MAX_GRAPH_NODES` and `_expand_item()` to batch-resolve parent container `Work`s in a single query.

## Impact

- **Backend**: `app/core/search_service.py`, `app/api/public_items.py`, `app/core/graph_service.py`
- **Tests**: `tests/test_api_public_extended.py`, `tests/test_catalog_graph_api.py`
- **Documentation & Release Plans**: `docs/COVERS_SETUP.md`, `docs/API.md`, `docs/CHANGELOG.md`, `.context/notes/plan/1.1.x-release-plan.md`, `.context/notes/iqoqo roadmap.md`, `.context/notes/iqoqo development notes.md`

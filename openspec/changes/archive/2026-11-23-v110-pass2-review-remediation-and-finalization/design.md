## Context

Following the second-pass review of `release/1.1.0` (PR #433, documented in `.context/notes/review/1.1.0/principal-review-release-1.1.0-pass-2.md`), all first-pass findings were verified resolved except for one privacy regression introduced in `app/core/search_service.py` (coupled with a one-line parameter omission in `app/api/public_items.py:get_shared_collection`), two minor query-bounding items in `app/core/graph_service.py`, and pre-tag documentation/plan alignment. See `proposal.md` for full motivation.

## Goals / Non-Goals

**Goals:**
- Ensure `SearchService.search_items()` never returns `is_hidden=True` (`private` or `friends_only`) items when `include_hidden=False`, even when `owner_only=True` and `user_id` is the target owner's ID.
- Ensure query-filtered `SharedCollection` links (`filters["query"]`) return matching `friends_only` items under `friends_and_public` and Friend Bonus across both `fetch_shared_collection_with_cache_policy()` and `get_shared_collection()` while excluding `private` and hidden-public (`visibility == "public" and is_hidden == True`) rows.
- Bound `GraphService._expand_expression()` manifestation fetches with `.limit(MAX_GRAPH_NODES)` and batch `ContainerAggregation` parent `Work` lookups in `GraphService._expand_item()`.
- Align `docs/COVERS_SETUP.md`, `docs/API.md`, `docs/CHANGELOG.md`, and `.context/notes/` release plans for `v1.1.0` tagging.

**Non-Goals:**
- Changing Docker Compose topology (`docker-compose.prebuilt.yml` already inherits Valkey 8 and `OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf` via Compose `include:`).
- Modifying `/scan` or `/collection` frontend components (verified clean in Pass 2).

## Decisions

1. **Strict `include_hidden=False` + Guarded `"public"` Tier in `SearchService` (`app/core/search_service.py`):**
   - *Decision:*
     - When `not filters.include_hidden`: apply `AND i.is_hidden = FALSE` in `_pg_item_fts` and `query = query.filter(Item.is_hidden.is_(False))` in `_ilike_item_search`. Never add `OR (i.owner_id = :user_id ...)` when `include_hidden=False`.
     - When `filters.visibility` is provided: compute `allowed_vis`. If `filters.include_hidden` is `True`, `"public"` is in `allowed_vis`, and non-public tiers (`friends_only`, `shared`, `private`) are also in `allowed_vis` (or `owner_only=True` on shared collections), ensure `"public"` items still require `is_hidden = FALSE` (`(i.visibility = 'public' AND i.is_hidden = FALSE) OR i.visibility IN :non_public_vis`) so a manually hidden item with legacy `visibility='public'` cannot leak when `include_hidden=True` is enabled to allow `friends_only` (`is_hidden=True`).
   - *Rationale:* In iqoqo's data model, `Item.set_visibility("friends_only")` and `Item.set_visibility("private")` both set `is_hidden = True`. Callers that want strictly public items pass `include_hidden=False`; callers that allow `friends_only` (such as `friends_and_public` or Friend Bonus shares) pass `include_hidden=True` with `visibility=["public", "friends_only", "shared"]`.
   - *Alternatives considered:* Filtering only in the outer SQLAlchemy query in `public_items.py` — rejected because `SearchService.search_items()` applies `LIMIT` before returning `item_ids` to `public_items.py`, so leaking hidden rows inside `SearchService` could displace valid visible results from the top-`limit` page and exposes direct callers of `SearchService.search_items(..., include_hidden=False)`.

2. **Consistent `include_hidden` Flag in `get_shared_collection()` (`app/api/public_items.py:826`):**
   - *Decision:* Pass `include_hidden=include_hidden or any(v != "public" for v in allowed_vis)` in `get_shared_collection()`, identical to `fetch_shared_collection_with_cache_policy()` (`line 382`).
   - *Rationale:* Eliminates divergence between the JSON `/api/public/share/<token>` route and the RDF/RSS/helper path.

3. **Bounded `_expand_expression` & Batched `_expand_item` in `GraphService` (`app/core/graph_service.py`):**
   - *Decision:* Append `.limit(MAX_GRAPH_NODES)` to the `select(Manifestation)` query in `_expand_expression()`, and replace `for agg in reverse_aggs: db.session.get(Work, agg.container_work_id)` in `_expand_item()` with a single `select(Work).where(Work.id.in_(container_ids))` dictionary lookup.
   - *Rationale:* Completes 100% batching across all four FRBR tier expanders in `GraphService`.

## Risks / Trade-offs

- **[Risk] Authenticated user searching their own library (`GET /api/items?q=...`) with `?visibility=public`:** → Mitigation: When a user filters their own library by `visibility=public`, `public` items have `is_hidden=False` via `Item.set_visibility("public")`, so requiring `is_hidden=False` for `visibility='public'` matches `CatalogFilterBuilder` and `_build_shared_visibility_predicate`.

## Context

Pass-2 review of `release/1.1.1` (`da35e8b6`, `.context/notes/review/1.1.1/principal-review-release-1.1.1-pass-2.md`) verified that all 29 CI checks pass and that all Pass-1 Critical and Moderate blockers were resolved by `C146`. It identified 1 Moderate edge case in category-filtered wishlist shares (`app/api/public_items.py:985-1017`) and 5 Low polish items across `app/core/search_service.py`, `app/core/graph_service.py`, `migrations/versions/v1_1_1_norm_legacy_formats.py`, `Makefile`, `app/core/frbr_service.py`, and Blueprint 8 SVG diagrams.

## Goals / Non-Goals

**Goals:**

- Preserve unmanifested conceptual F1/F2 `UserWorkIntent` wishlist entries in category-filtered wishlist shares (`excluded_formats` active without an explicit non-null `format` filter).
- Guard `_pg_item_fts` against whitespace-only `excluded_formats` tuples and add a direct regression test for `SearchService.search_items(..., excluded_formats=...)`.
- Accurately set `meta.truncated = True` when `GraphService.build_neighborhood()` caps a hub at `MAX_NEIGHBORS_PER_NODE_DEEP` (`depth >= 3`) or when `GraphService.build_library_graph()` caps an entity tier at `tier_quota`.
- Normalize uniform mixed-case format rows (`"Vinyl"`, `"Vinyl"`, `"Vinyl"`) in `v1_1_1_norm_legacy_formats.py`, scope the `preview-reconcile` OpenObserve container check in `Makefile`, percent-encode `#map-{att_id}` in `frbr_service.py`, and update Blueprint 8 SVG copy from `"2-Hop"` to `"1–4 Hop"`.

**Non-Goals:**

- Any schema DDL changes or new API endpoints.

## Decisions

### 1. Unmanifested `UserWorkIntent` Preservation in `_query_public_share_items()` (`app/api/public_items.py`)

- **Decision:**
  - Define a correlated existence subquery `any_manif_sub` matching any `Manifestation` of `UserWorkIntent.work_id` (constrained by `UserWorkIntent.expression_id` and `UserWorkIntent.manifestation_id` when bound).
  - When `filter_specs["formats"]` is set and `not filter_specs["include_null_fmt"]`, require `sa.exists(manif_sub)` (the intent must have a matching carrier format that is not in `excluded_formats`).
  - When `filter_specs["formats"]` is not set (only `excluded_formats` is active from a category filter) OR `filter_specs["include_null_fmt"]` is True, filter by `sa.or_(sa.exists(manif_sub), ~sa.exists(any_manif_sub))` so conceptual wishlist works with zero `Manifestation` rows are preserved while works whose manifestations are all in `excluded_formats` (e.g. a movie DVD work) are still excluded.

### 2. Accurate `meta.truncated` Reporting in `GraphService` (`app/core/graph_service.py`)

- **Decision:**
  - In `build_neighborhood()`, set `nonlocal node_truncated; node_truncated = True` inside `bounded_enqueue` and `bounded_try_add` whenever a new neighbor (`not was_present`) is skipped because `node_added >= per_node_cap`.
  - In `build_library_graph()`, compute `tier_quota = effective_max_nodes if len(active_tiers) <= 1 else max(1, effective_max_nodes // len(active_tiers))`. When querying each tier (`Work`, `Expression`, `Manifestation`, `Item`, `Contributor`, `SemanticLink`), query `.limit(quota + 1)` and, if `len(rows) > quota`, set `node_truncated = True` and slice `rows = rows[:quota]`.

### 3. Defensive `_pg_item_fts` `excl_tuple` Guard & Migration `has_case_drift`

- **Decision:**
  - In `SearchService._pg_item_fts()`, compute `excl_tuple = tuple(str(f).strip().lower() for f in filters.excluded_formats if str(f).strip())` and only add `params["excluded_formats"] = excl_tuple`, the SQL `NOT IN :excluded_formats` predicate, and `bindparam("excluded_formats", expanding=True)` (`if "excluded_formats" in params:`) when `excl_tuple` is non-empty.
  - In `migrations/versions/v1_1_1_norm_legacy_formats.py`, compute `has_case_drift = any(isinstance(val, str) and val.strip() != val.strip().lower() for val in (fmt, fmt_type, meta_fmt))` and include `has_case_drift` alongside `has_drift or has_missing_column`.

## Risks / Trade-offs

- **[Risk] Existing library graph tests might assert `meta.truncated is False` on tiny test fixtures.** → **Mitigation:** Tiny test fixtures have fewer rows than `tier_quota` (e.g. `< 18` rows per tier at default `max_nodes=150`), so `len(rows) > quota` is `False` on small catalogs and `True` only when a tier actually overflows its quota.

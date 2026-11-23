## Why

The Pass-2 Principal + Gemini review of `release/1.1.1` (PR #447, documented in `.context/notes/review/1.1.1/principal-review-release-1.1.1-pass-2.md` and `.context/notes/review/1.1.1/review-2-release-1.1.1-pr-447.md`) confirmed that all Pass-1 Critical and Moderate blockers were resolved by `C146`, while uncovering 1 Moderate FRBR wishlist regression (category-filtered wishlist shares dropping unmanifested conceptual F1/F2 `UserWorkIntent` works when `excluded_formats` is active) and 5 Low polish items (`_pg_item_fts` empty `excl_tuple` guard + unit test for `SearchService.search_items(..., excluded_formats=...)`, `GraphService` `meta.truncated` reporting on per-node deep cap and per-tier library quota overflow, `v1_1_1_norm_legacy_formats.py` uniform mixed-case `"Vinyl"` normalization, `Makefile` `preview-reconcile` container grep specificity, and `frbr_service.py` `#map-{att_id}` IRI encoding + Blueprint 8 SVG `"1–4 Hop"` copy). Resolving these in `C147` completes the `v1.1.1` release gate.

## What Changes

- **[MODERATE] Preserve unmanifested conceptual F1/F2 `UserWorkIntent` works on category-filtered wishlist shares (`app/api/public_items.py:985-1017`):**
  - When `filter_specs["formats"]` is set (and `filter_specs["include_null_fmt"]` is False), require `sa.exists(manif_sub)` (matching format and not in `excluded_formats`).
  - When `filter_specs["formats"]` is NOT set (only `excluded_formats` from a category filter is active) or when `filter_specs["include_null_fmt"]` is True, allow the `UserWorkIntent` when either `sa.exists(manif_sub)` holds OR no `Manifestation` exists yet for that intent's `Work` / bound `Expression` (`~sa.exists(any_correlated_manif)`).
- **[LOW] Guard `_pg_item_fts` against whitespace-only `excluded_formats` and add explicit `SearchService.search_items(..., excluded_formats=...)` test (`app/core/search_service.py:559-564, 647-649`; `tests/test_search.py`):**
  - Only bind `params["excluded_formats"]`, append `NOT IN :excluded_formats`, and bind `bindparam("excluded_formats", expanding=True)` when the stripped `excl_tuple` is non-empty.
- **[LOW] Report `meta.truncated = True` on per-node deep cap and per-tier library quota overflow (`app/core/graph_service.py:346, 356, 500-699`):**
  - Set `node_truncated = True` in `build_neighborhood()` whenever `bounded_enqueue` or `bounded_try_add` rejects a new neighbor due to `node_added >= per_node_cap` (`MAX_NEIGHBORS_PER_NODE_DEEP = 25`).
  - In `build_library_graph()`, compute `tier_quota = effective_max_nodes if len(active_tiers) <= 1 else max(1, effective_max_nodes // len(active_tiers))`, fetch `quota + 1` rows per tier, slice `[:quota]`, and set `node_truncated = True` whenever `len(rows) > quota`.
- **[LOW] Normalize uniform mixed-case format rows in Alembic migration `v1_1_1_norm_legacy_formats.py` (`lines 63-102`):**
  - Detect `has_case_drift = any(isinstance(val, str) and val.strip() != val.strip().lower() for val in (fmt, fmt_type, meta_fmt))` so rows with uniform capitalized values (`"Vinyl"`, `"Vinyl"`, `"Vinyl"`) are normalized to lowercase `"vinyl"`.
- **[LOW] Scope `preview-reconcile` OpenObserve container check in `Makefile` (`line 454`):**
  - Match `iqoqo-preview-openobserve` specifically (with fallback) so a co-located production OpenObserve container does not false-trigger preview auth checks.
- **[LOW] Percent-encode `MapAttachment` fragment IRI in `app/core/frbr_service.py` (`lines 2968, 3135`) and update Blueprint 8 SVG subtitle (`docs/images/architecture/08-frbr-visual-relation-graph.svg`, `frontend/public/images/help/08-frbr-visual-relation-graph.svg`):**
  - Use `quote(str(att_id), safe="")` when constructing `URIRef(f"{str(m_uri)}#map-{att_id}")`, remove the duplicate `from sqlalchemy import or_` at line 2968, and update Blueprint 8 SVG text from `"2-Hop"` to `"1–4 Hop"`.

## Capabilities

### New Capabilities
_None._

### Modified Capabilities
- `shared-collection-type-integrity`: Preserve conceptual F1/F2 `UserWorkIntent` wishlist entries that have a matching `Expression` but zero `Manifestation` rows when filtering by category (`excluded_formats` active without an explicit non-null `format` filter), and guard non-empty `excluded_formats` in PostgreSQL FTS.
- `visual-frbr-relation-graph`: Set `meta.truncated = True` whenever `build_neighborhood()` caps neighbors at `MAX_NEIGHBORS_PER_NODE_DEEP` (`depth >= 3`) or `build_library_graph()` caps an individual entity tier at `tier_quota`.
- `format-mapping-cli`: Normalize uniform mixed-case format columns (e.g., `"Vinyl"` across all three format fields) to lowercase canonical `MediaFormat` values during `v1_1_1_norm_legacy_formats.py` backfill.

## Impact

- **Backend & Migration:** `app/api/public_items.py`, `app/core/search_service.py`, `app/core/graph_service.py`, `app/core/frbr_service.py`, `migrations/versions/v1_1_1_norm_legacy_formats.py`.
- **Ops & Docs:** `Makefile`, `docs/images/architecture/08-frbr-visual-relation-graph.svg`, `frontend/public/images/help/08-frbr-visual-relation-graph.svg`, `docs/CHANGELOG.md`, `.context/notes/plan/1.1.x-release-plan.md`.
- **Tests:** `tests/test_api_public_extended.py`, `tests/test_search.py`, `tests/test_graph_and_wishlist_services.py`, `tests/test_migration.py`.

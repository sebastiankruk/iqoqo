## Context

Following the merge of all five `v1.1.1` feature/fix PRs (`C139` #448, `C140` #449, `C141` #450, `nginx:1.31.9` #451, and `C145` #452) into `release/1.1.1` (`94af1f46`), the Principal + Gemini release review (`.context/notes/review/1.1.1/principal-review-release-1.1.1.md`) identified 2 Critical blockers, 10 Moderate issues, and 5 Low hygiene findings across four layers. See `proposal.md` for full motivation and scope.

## Goals / Non-Goals

**Goals:**

- Achieve 100% behavioral and permission parity for `make start preview prebuilt` (`0600` `.env` handling without container `UID 10001` bind-mount failures, absolute `COMPOSE_ENV_FILE` path support, `preview-reconcile` invocation, and zero-argv `stdin` secret piping in `monitoring-reset-auth`).
- Eliminate node-budget starvation in `GraphService.build_library_graph()` on production-scale catalogs (`>= 150` works) while restoring `WorkPart`, `WorkExpansionLink`, `ContainerAggregation`, `ExpressionContribution`, and `ManifestationContribution` edges in `mode=library`, bounding hop-1 hub fan-out at `depth >= 3`, and fixing `FederationConsent` friend visibility parity across `GraphService` and `SparqlService`.
- Close remaining format normalization and share filtering edge cases across `migrations/versions/v1_1_1_norm_legacy_formats.py`, `scripts/fix_physical_kinds.py`, `app/api/public_items.py`, `app/core/search_service.py`, `app/api/filters.py`, `app/core/f3_validation.py`, `app/core/data_manager.py`, and `app/utils/format_normalizer.py`.
- Enforce the `<= 4` visible inline button density rule on `/graph?mode=library` (`frontend/app/graph/page.tsx`) and finalize `docs/CHANGELOG.md` for `v1.1.1`.

**Non-Goals:**

- Introducing new database schema migrations (enhancing the existing `v1_1_1_norm_legacy_formats.py` migration on `release/1.1.1` before `v1.1.1` is tagged keeps the single linear Alembic head intact).
- Implementing `v1.1.2` roadmap items (`C142` item page declutter, `C143` multi-root person/object graph picker, `C144` cross-media FRBR reconciliation).

## Decisions

### 1. Container-Safe `0600` Env Secret Provisioning & Reconciliation in `Makefile` (`start` prebuilt preview & `monitoring-reset-auth`)

- **Decision:**
  - Normalize `COMPOSE_ENV_FILE` to an absolute path (`ABS_ENV_FILE`) via a POSIX `case "$(COMPOSE_ENV_FILE)" in /*) ... ;; *) ... ;; esac` check rather than prefixing `$(CURDIR)/$(COMPOSE_ENV_FILE)` or `./$(COMPOSE_ENV_FILE)`.
  - In `Makefile` `start` (`prebuilt` preview branch), avoid bind-mounting a `0600` host-owned `.env` directly into `web` as `appuser` (`UID 10001`) for in-place file replacement (which fails with `PermissionError` both on reading a `0600` file owned by another UID and on `tempfile.mkstemp` inside `/tmp` followed by `os.replace` across bind-mount boundaries). Instead, run the container helper with `--user "$$(id -u):$$(id -g)"` (or pipe via `stdin`/`stdout` on the host file) and tighten `chmod 0600` on the host immediately after, then invoke `$(MAKE) preview-reconcile DEPLOY_DIR="$(CURDIR)" DEPLOY_ENV_FILE="$$abs_env"` after bringing up `db`, `redis`, `web`, and `worker`.
  - In `monitoring-reset-auth`, pipe `$$oo_auth` via `printf '%s' "$$oo_auth" | docker compose ... exec -T web python3 -c "import sys; raw = sys.stdin.read().strip(); ..."` instead of `-e OO_BASIC_AUTH="$$oo_auth"`, eliminating CLI argument exposure in `ps aux`.
- **Alternatives Considered:**
  - Requiring host `python3` in `make start preview prebuilt`: Rejected because `prebuilt-env-propagation-and-secret-decrypt-guard` explicitly requires `make preview start prebuilt` to succeed on hosts without `python` or `python3` installed.

### 2. Connected Multi-Tier Node Budgeting & Complete Edge Emission in `GraphService.build_library_graph()`

- **Decision:**
  - When multiple entity types are active in `build_library_graph()`, partition `effective_max_nodes` across active tiers so Step 1 (`Work` / `Series`) claims at most its share of the budget (`work_budget = effective_max_nodes` if only `work`/`series` are active, otherwise `max(10, effective_max_nodes // max(2, len(active_types)))`, e.g., up to ~35–40 root works when all tiers are active on a `150`-node budget) and pushes `Work.work_kind != "series"` directly into the SQL `WHERE` clause when `want_work and not want_series`.
  - In Steps 2–6 (`Person`, `Expression`, `Manifestation` + `Map`, `Item`, `LOD`), prioritize entities connected to the already-selected `Work` / `Expression` / `Manifestation` IDs (falling back to global `id.asc()` only if connected entities do not fill the remaining node budget). This guarantees that on a 2,000-work catalog, `/graph?mode=library` renders connected FRBR trees (`Work -> Expression -> Manifestation -> Item`) plus their contributors, maps, and LOD links rather than 150 isolated `Work` nodes and 0 edges.
  - In Step 7, in addition to `WorkContribution` and `Expression`/`Manifestation` hierarchy edges, query and emit:
    - `WorkPart` (`parent_work_id`, `child_work_id`) and `WorkExpansionLink` (`base_work_id`, `expansion_work_id`) when `want_parts` and at least 2 work/series nodes are present.
    - `ContainerAggregation` (`container_item_id`, `contained_item_id`) when `want_parts` and at least 2 item nodes are present.
    - `ExpressionContribution` and `ManifestationContribution` when `want_contrib`, `present_person_ids` is non-empty, and `present_expr_ids` / `present_manif_ids` are non-empty.
- **Alternatives Considered:**
  - Simply dividing `150 // 8 = 18` independent `ORDER BY id ASC` rows per table without filtering by parent `present_work_ids`: Rejected because the oldest 18 `Expression`s or `Item`s in a large catalog may not belong to the oldest 18 `Work`s, which would still leave most nodes disconnected. Seeding connected children from `present_work_ids` (with an unlinked fallback when `Work` is toggled off) maximizes graph connectivity while respecting `effective_max_nodes`.

### 3. Per-Node Expansion Bounds at `depth >= 3` & Shared `FederationConsent` Friend-Exemption Helper

- **Decision:**
  - Add `MAX_NEIGHBORS_PER_NODE_DEEP = 25` in `GraphService.build_neighborhood()` when `effective_depth >= 3`, bounding per-node neighbor expansion queries so a single prolific hub at hop 1 cannot monopolize all 150 node slots before hop 2–4 nodes are visited.
  - Update `is_item_visible_to_viewer()` in `app/core/graph_service.py` so `Item.visibility == "public"` only excludes `opted_out_user_ids` when `item.owner_id not in viewer_friend_ids`, and extract a shared SQL clause helper `build_sql_item_visibility_clause(viewer_user_id, viewer_friend_ids, opted_out_user_ids)` in `app/core/graph_service.py` imported by `SparqlService._build_rdf_graph()`.

### 4. Comprehensive Format Backfill, FTS Case/NULL Parity & Pre-`LIMIT` Format Exclusion

- **Decision:**
  - In `migrations/versions/v1_1_1_norm_legacy_formats.py`:
    - Treat any row where at least one of `(fmt, fmt_type, meta_fmt)` is `None`/blank while another is non-blank as `has_missing_column = True`, so a single canonical column (`meta['format'] = "vinyl"`, `format = None`) is synchronized across all three fields.
    - When `not raw_values` (all three columns are `None`/blank) and `raw_payload is not None`, call `FormatNormalizer.recover_carrier_from_raw_payload(raw_payload, content_type=content_type)`.
  - In `scripts/fix_physical_kinds.py`:
    - Update `get_non_canonical_rows()` so rows with column disagreement (`format != format_type`, `format != meta['format']`, missing columns, or non-canonical values in *any* of the three columns) are included rather than short-circuiting on `func.coalesce(Manifestation.format, ...)`.
    - In `_update_manifestation_format()`, pass `content_type` to `FormatNormalizer.recover_carrier_from_raw_payload(manif.raw_payload, content_type=content_type)` and repair mis-tagged `Expression.content_type == "music"` rows when `target_fmt in {"dvd", "bluray", "vcd", "book"}`.
  - In `app/api/public_items.py`, `app/core/search_service.py`, `app/api/filters.py`, `app/core/f3_validation.py`, `app/core/data_manager.py`, and `app/utils/format_normalizer.py`:
    - Add `excluded_formats: list[str] | None = None` support to `SearchService.search_manifestations()` and `SearchService.search_items()` so `_build_fts_matched_ids()` pushes format exclusion into the FTS query before `LIMIT 500`.
    - Use `LOWER(COALESCE(m.format, m.format_type, m.meta ->> 'format'))` and `filter_includes_null_format()` (`OR COALESCE(...) IS NULL`) in `_pg_manifestation_fts`, `_pg_item_fts`, `CatalogFilterBuilder._apply_format`, and `DataManager.get_filtered_works`.
    - Constrain `_query_public_share_items` wishlist `sa.exists` by bound `UserWorkIntent.expression_id` and `UserWorkIntent.manifestation_id`, plus `include_null_fmt` and `excluded_formats`.
    - Add `"moving image"` and explicit alias lookup to `validate_format_type(..., strict=False)` in `app/core/f3_validation.py`, and pre-compute lowercased alias reverse mappings in `FormatNormalizer._load_config()`.

### 5. `/graph?mode=library` Inline Entity Filter Compaction (`<= 4` Primary Pills)

- **Decision:**
  - Split `LIBRARY_ENTITY_TYPES` in `frontend/app/graph/page.tsx` into `PRIMARY_LIBRARY_ENTITY_TYPES = ["work", "expression", "manifestation", "item"]` (rendered inline) and `SECONDARY_LIBRARY_ENTITY_TYPES = ["series", "contributor", "map", "lod"]` (revealed via a compact `+4` / `More types` disclosure toggle button inside `data-testid="graph-entity-type-filters"`). This keeps the default inline entity pill count at 4 (+1 disclosure button) while preserving instant access to all 8 entity types.

## Risks / Trade-offs

- **[Risk] Existing unit tests for `frontend/app/graph/page.tsx` may query secondary entity type filter buttons (`series`, `contributor`, `map`, `lod`) directly.** → **Mitigation:** Render the secondary filter pills inside a collapsible popover/inline disclosure (or keep them accessible via the toggle button and update/extend `frontend/__tests__/app/graph/page.test.tsx` to verify both the compact `<= 4` primary pill view and secondary disclosure expansion).
- **[Risk] Modifying `v1_1_1_norm_legacy_formats.py` on `release/1.1.1`.** → **Mitigation:** `v1.1.1` has not been tagged or merged to `main` yet, and `v1_1_1_norm_legacy_formats.py` is idempotent data normalization with zero DDL schema changes. Updating both `v1_1_1_norm_legacy_formats.py` and `scripts/fix_physical_kinds.py` ensures both fresh upgrades and manual `--apply` runs converge to identical data state.

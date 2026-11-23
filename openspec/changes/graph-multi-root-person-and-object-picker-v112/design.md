## Context

`C133` introduced `GraphService` (`app/core/graph_service.py`), `GET /api/catalog/graph` (`app/api/works.py:948`), and the full-screen `/graph` page (`frontend/app/graph/page.tsx`) with `CAPACITOR_BUILD=true` static-export compatibility via query parameters (`?type=...&id=...&depth=...`). However, `VALID_GRAPH_ENTITY_TYPES` (`graph_service.py:35`), `VALID_TYPES` (`page.tsx:30`), and `RECENTERABLE_TYPES` (`frbr-relation-graph.tsx:53`) are currently locked to `work`, `expression`, `manifestation`, and `item`. Opening `/graph` without query parameters displays a passive dead-end card (`page.tsx:102-109`), and clicking a `contributor` node in the graph hides the `"Recenter Graph"` button.

See `proposal.md` for motivation. This design preserves the current `MAX_GRAPH_DEPTH = 2` and `MAX_GRAPH_NODES = 150` bounds of `openspec/specs/visual-frbr-relation-graph/spec.md` without assuming unmerged sibling changes (`C140` depth `1..4` or `C144` `R2_is_derivative_of` cross-media links), while keeping all interfaces cleanly additive.

## Goals / Non-Goals

**Goals:**
- Support `person` (alias `contributor`) and `series` as first-class graph roots in `GraphService`, `GET /api/catalog/graph`, `/graph`, and `RECENTERABLE_TYPES`, including bidirectional traversal across `Contributor` (`person` and `organization`) and `Series` (`Work`).
- Provide a dedicated, rate-limited, `@optional_auth`, SQL-`LIMIT`-bounded `GET /api/catalog/graph/search` endpoint enforcing three-tier `Item` visibility in SQL before `LIMIT`.
- Deliver a keyboard-accessible `<GraphRootPicker />` on `/graph` (inline in empty state, `"Switch Root"` dialog on active graphs) that honors `iqoqo-ux-auditor` button-density heuristics, `CAPACITOR_BUILD=true` static export, and `app/api/docs.py` OpenAPI 3.1 parity.

**Non-Goals:**
- Extending traversal depth beyond `2` or adding a full-library explorer view (covered separately by `C140`).
- Creating new database tables or Alembic migrations (`Contributor` and `Work`/`WorkSeriesMembership` already model persons/organizations and series in FRBRoo).
- Refactoring the existing 9-button graph canvas toolbar (`frbr-relation-graph.tsx:297-357`) into a popover (out of scope, though `C143` must add zero buttons to it).

## Decisions

### 1. `person` / `contributor` Alias Normalization & `organization` Subtype Handling
- **Decision:** Accept both `"person"` and `"contributor"` (and `"organization"` if passed explicitly, or normalize via `Contributor.type`) in `VALID_GRAPH_ENTITY_TYPES`, `VALID_TYPES`, and `RECENTERABLE_TYPES`. Internally in `GraphService`, normalize `"person"` and `"contributor"` to `"contributor"` node keys (`"contributor:<id>"`) via `_contributor_node_dict(contributor, hop=..., is_anchor=...)`, while adding `"contributor_type": contributor.type or "person"` (`"person"` | `"organization"`) to the node payload. Add `_expand_contributor()` querying `WorkContribution`, `ExpressionContribution`, `ManifestationContribution` (each `.limit(MAX_GRAPH_NODES)` with batched entity loads—zero N+1) plus `_add_semantic_links("contributor", contributor.id, ...)`. Update `_expand_work()`, `_expand_expression()`, and `_expand_manifestation()` to call `enqueue_neighbor("contributor", contrib, next_hop)` instead of `try_add_node(...)` so `depth=2` around a `Work` traverses through hop-1 contributors to sibling works.
- **Alternative Considered:** Reject `"person"` and force callers to pass `"contributor"` everywhere, OR restrict `"person"` anchors strictly to `Contributor.type == "person"` and reject `"organization"`.
- **Trade-offs:** Dual acceptance satisfies the `1.1.x-release-plan.md` contract (`/graph?type=person&id=<id>`) while preserving compatibility with `GraphService`'s existing `"contributor"` node type (`frbr-relation-graph.tsx:83`) and allowing recentering onto bands/studios/publishers (`Contributor.type == "organization"`, `F11_Corporate_Body`, verified in `tests/test_catalog_graph_api.py:239`). Minor asymmetry (`?type=person&id=7` yielding `node_id: "contributor:7"`) is explicit and avoids duplicate node keys. Keep `_contributor_node_dict`'s `url: f"/collection?q={quote_plus(contributor.name)}"` unchanged so existing `test_catalog_graph_encodes_contributor_urls` continues to pass.

### 2. `series` Root Resolution onto Canonical `work:<id>` Nodes
- **Decision:** Accept `"series"` in `VALID_GRAPH_ENTITY_TYPES` and `VALID_TYPES`. In `GraphService._load_anchor("series", entity_id, ...)`, load the `Work` matching `id == entity_id` AND (`Work.work_kind == "series"` OR existence in `WorkSeriesMembership.series_work_id` OR existence in `WorkPart.container_work_id`), returning `None` (`404`) otherwise. Normalize the loaded anchor onto the canonical `"work:<id>"` node key (retaining `work_kind` and `url: f"/work/{work.id}"`) so `_expand_work()`'s existing `WorkSeriesMembership` / `WorkPart` expansion connects member works cleanly without duplicate nodes.
- **Alternative Considered:** Emit a distinct `series:<id>` node key and `entity_type: "series"` in `GraphService`.
- **Trade-offs:** Existing tests (`tests/test_catalog_graph_api.py:54, 142`) and fixtures (`tests/test_rdf_serialization.py:931`) create series `Work`s with `work_kind=None` linked only via `WorkSeriesMembership` and expect `work:<id>` nodes. Using canonical `work:<id>` prevents a series `Work` from appearing twice (`series:<id>` and `work:<id>`) during `depth=2` bidirectional traversal. The `WorkSeriesMembership`/`WorkPart` fallback ensures legacy series containers without `work_kind="series"` still resolve cleanly.

### 3. Dedicated `GET /api/catalog/graph/search` vs. Loosening Admin Search Routes
- **Decision:** Create a dedicated `GET /api/catalog/graph/search` route on `api_bp` (`app/api/works.py`) decorated with `@optional_auth` and `@limiter.limit("60 per minute")`. Accept `q` (diacritic-folded via `normalize_diacritics`, `escape_ilike_term`, and `db.func.immutable_unaccent`), `types` (CSV subset of `person`, `contributor`, `series`, `work`, `expression`, `manifestation`, `item`; default `person,series,work,manifestation,item`), and `limit` (SQL `LIMIT` clamped to `1..25`, default `10` total or bounded per requested type). Return typed summaries (`entity_type`, `entity_id`, `label`, `subtitle`, optional `contributor_type`, `work_kind`, `issn`, `url`) with batched joins.
- **Alternative Considered:** Loosen RBAC on `/api/admin/frbr/search` (`app/api/admin.py:884`) or `/api/admin/works/search` (`app/api/admin.py:674`) to allow public/unprivileged users.
- **Trade-offs:** Both admin endpoints live on `admin_bp` behind `@require_auth` + `@require_permission(PermissionName.READ_METADATA)` (`tests/test_api_admin.py:87-93` explicitly asserts `403` for plain users), lack `@limiter.limit`, lack `Contributor`/`Series`/`Item` support, and `/frbr/search` has an unbounded `limit` + N+1 `db.session.get()` queries. A dedicated catalog endpoint isolates admin maintenance surfaces from public graph navigation while enforcing strict SQL `LIMIT` bounds and rate limits.

### 4. Strict Three-Tier `Item` Visibility in SQL, Catalog Discoverability, and `FEDERATION_HEAD_MODE`
- **Decision:** Enforce three-tier `Item` visibility directly inside the SQLAlchemy `select(Item)` `WHERE` clause **before** `.limit()` (never in Python post-filtering):
  1. `and_(Item.visibility == "public", Item.is_hidden.is_(False))`
  2. OR `Item.owner_id == viewer_uuid` (when authenticated)
  3. OR `and_(Item.owner_id.in_(viewer_friend_ids), Item.visibility.in_(("friends_only", "shared")))` (when authenticated with accepted friends from `get_friend_user_ids(viewer_uuid)`).
  Keep catalog-tier entities (`Work`, `Series`, `Expression`, `Manifestation`, `Contributor`) discoverable under `@optional_auth` consistent with existing `GET /api/catalog/graph`, `GET /api/works/shelf`, and `GET /api/manifestations` (none of which have `owner_id` or `visibility` columns), while never exposing private `Item` IDs, local barcodes, or owner notes in picker payloads. Keep both `GET /api/catalog/graph` and `GET /api/catalog/graph/search` active when `FEDERATION_HEAD_MODE=true`, since `reject_if_federation_head_item_write()` (`app/api/federation_guard.py`) only blocks inventory mutations.
- **Alternative Considered:** Post-filter `Item` rows in Python using `is_item_visible_to_viewer()`, or hide `Work`/`Contributor` catalog rows that lack public `Item`s.
- **Trade-offs:** Post-filtering in Python after `LIMIT` lets private items fill the SQL `LIMIT` window and starve visible matches (or risks leaking counts); SQL-level `WHERE` avoids both. Hiding catalog `Work`s without public `Item`s would contradict existing `C133` graph behavior (`tests/test_catalog_graph_api.py:139-150`) where catalog works render regardless of private item ownership.

### 5. Frontend Architecture: Capacitor Routing, Anchor URL Fix, Native Combobox, and UX Button Density
- **Decision:**
  - **Static-Export Routing:** Keep `/graph` reading `?type=...&id=...&depth=...` via `useSearchParams()` inside `<Suspense>` (`CAPACITOR_BUILD=true` compatible; zero dynamic `[type]/[id]` path segments). Use `router.push` on root selection and recentering so browser Back/Forward history tracks exploration steps.
  - **Fix Hardcoded Header Link (`page.tsx:63`):** Replace `<Link href={`/${rawType}/${rawId}`}>` with `anchorHref` derived from `graph?.nodes.find((n) => n.is_anchor)?.url` (only rendering when starting with `/`, with fallback `/work/${rawId}` when `rawType === "series"`). This prevents guaranteed 404s because `frontend/app/` has no `/person`, `/contributor`, or `/series` routes.
  - **Zero-Dependency ARIA Combobox (`<GraphRootPicker />`):** Build `frontend/components/graph/graph-root-picker.tsx` using native ARIA combobox semantics (`role="combobox"`, `aria-expanded`, `aria-controls`, `aria-activedescendant`, `role="listbox"`, `role="option"`, `ArrowUp`/`ArrowDown`/`Enter`/`Escape`), `useDebounce(..., 300)`, `useCatalogGraphSearch`, and existing Shadcn `Select` / `Badge` / `Dialog`.
  - **UX Auditor Button-Density Placement:** Render `<GraphRootPicker />` inline inside the `!isValidAnchor` empty-state hero card (making root selection the single primary CTA), and add **one** `"Switch Root"` `<Button>` (`data-testid="graph-switch-root-button"`) in the `page.tsx` header opening a Shadcn `<Dialog>` containing `<GraphRootPicker />` (keeping header buttons `<= 4`: `Open Entity`, `Switch Root`, `1 hop`, `2 hops`, and adding **zero** buttons to the existing 9-button toolbar in `frbr-relation-graph.tsx:297-357`).
- **Alternative Considered:** Install `cmdk` + `@radix-ui/react-popover` and embed a persistent search input + type dropdown directly inside the `frbr-relation-graph.tsx` toolbar.
- **Trade-offs:** Installing `cmdk` adds npm/bundle overhead for Capacitor builds and embeds controls into an already dense 9-button toolbar (`iqoqo-ux-auditor` flags `> 4` buttons per container and mobile `~390px` header overflow). The empty-state hero + single `"Switch Root"` dialog button keeps every viewport clean at the cost of 1 extra click when switching roots from an active graph.

### 6. OpenAPI 3.1 Contract (`app/api/docs.py`)
- **Decision:** Update the parameter override block in `assemble_complete_openapi_spec()` (`app/api/docs.py:828-871`) for `("/api/catalog/graph", "/api/v1/catalog/graph")` so `entity_type.schema.enum` becomes `["work", "expression", "manifestation", "item", "person", "contributor", "series"]`, and add an explicit block for `("/api/catalog/graph/search", "/api/v1/catalog/graph/search")` documenting `q`, `types`, `limit` (`minimum: 1`, `maximum: 25`), and `200`/`400`/`429` responses (under tag `"Catalog"`, with `_endpoint_requires_auth` returning `False` for `@optional_auth`).
- **Alternative Considered:** Rely solely on `FlaskPlugin` docstring parsing without explicit parameter overrides in `app/api/docs.py`.
- **Trade-offs:** `app/api/docs.py` already uses explicit overrides for `/api/catalog/graph` so `tests/test_openapi_contract_completeness.py` can verify exact enum values and bounds programmatically.

### 7. Localization (`frontend/messages/en.json` & `pl.json`)
- **Decision:** Add `graph.*` keys (`switchRoot`, `pickerDialogTitle`, `pickerDialogDescription`, `pickerInputPlaceholder`, `pickerTypeLabel`, `pickerTypeAll`, `pickerMinChars`, `pickerLoading`, `pickerNoResults`, `pickerError`, `nodeTypes.person`, `nodeTypes.series`) and update `missingParamsTitle` / `missingParamsDescription` in both `en.json` and `pl.json`. Strictly enforce **sentence case** in `pl.json` (capitalizing only the first word and acronyms such as `FRBR` / `ISBN`, e.g., `"Wyszukaj osobę, serię, dzieło, manifestację lub egzemplarz, aby zbadać powiązania FRBR."`, `"Osoba"`, `"Seria"`).

## Risks / Trade-offs

- **High-Degree Contributors (`depth=2` or `entity_type=person`)** → A prolific author/publisher could have hundreds of works/manifestations; bound every query inside `_expand_contributor()` with `.limit(MAX_GRAPH_NODES)`, batch entity hydration with `IN (...)` queries, and enforce `effective_max_nodes` (`<= 150`) with `meta.truncated = True`.
- **`series` Anchor Strictness vs. Arbitrary `Work` ID** → Passing a non-series `Work` ID with `entity_type=series` returns `404` when checking `work_kind == "series"` or `WorkSeriesMembership` / `WorkPart` presence; mitigate by ensuring the picker `series` filter uses the exact same predicate.
- **Unauthenticated Rate Abuse on `/api/catalog/graph/search`** → Enforce `@limiter.limit("60 per minute")`, require `len(q.strip()) >= 2` on the frontend before firing requests, and clamp SQL `LIMIT` to `<= 25` on the backend.
- **Coordination with Sibling Milestone `C140`** → If `C140` merges before `C143` is applied and expands `depth` to `1..4` or adds full-library mode, rebase `page.tsx` depth buttons and `VALID_GRAPH_ENTITY_TYPES` cleanly without altering `C143`'s root picker contract.

## Open Questions

- None. All entity mappings, visibility predicates, routing, UX placement, and OpenAPI schemas are fully resolved against existing codebase contracts.

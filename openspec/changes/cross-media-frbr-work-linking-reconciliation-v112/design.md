## Context

See `proposal.md` for motivation. Today, iqoqo models `Work -> Expression -> Manifestation -> Item` in PostgreSQL across `_CATALOG` (`catalog`) and `_INVENTORY` (`inventory`) schemas (`app/db/core.py:49-65`). Existing Work-to-Work models are purpose-built for structural containment (`WorkPart` in `app/db/contributions.py:194`, `ContainerAggregation` in `app/db/core.py`), ordered sequences (`WorkSeriesMembership` in `app/db/contributions.py:217`), and 1:1 board-game expansions (`WorkExpansionLink` in `app/db/core.py:302`). Meanwhile, `DuplicateCandidate` (`inventory.duplicate_candidates`, `app/db/core.py:1036`) drives destructive consolidation via `app/core/frbr_merge.py`, and `GraphService` (`app/core/graph_service.py`) + `build_collection_rdf_graph()` (`app/core/frbr_service.py:3178`) expose accepted catalog relationships without emitting `frbroo:R2_is_derivative_of` or `schema:isBasedOn`.

## Goals / Non-Goals

**Goals:**

- Model many-to-many, directional cross-media `Work -> Work` derivative/adaptation relations (`derived_work -> source_work`) without collapsing distinct `Work`s or modifying `WorkExpansionLink` board-game invariants.
- Provide a two-stage cross-media reconciliation pipeline (`ENGINE_HEURISTIC` default + optional `ENGINE_LLAMA` via SSRF-safe `OLLAMA_URL`) with a dry-run-by-default CLI and a Custodian review queue.
- Expose accepted-only links in `GET /api/catalog/graph`, `/graph`, and RDF/JSON-LD exports (`frbroo:R2_is_derivative_of`, `schema:isBasedOn`) with zero leakage of `pending` or `dismissed` candidates.
- Maintain OWL/SHACL parity (`scripts/sync_ontology.py --check`), mechanical `frbr_merge` FK coverage (`tests/test_frbr_merge_coverage.py`), and a single linear Alembic migration chain.

**Non-Goals:**

- Merging cross-media `Work`s (explicitly forbidden; same-medium duplicates stay in `/admin/duplicates`).
- Modifying `boardgame-expansion-modeling` (`WorkExpansionLink` / `ExpansionWorkShape`) or overloading external authority LOD ETL (`semantic/lod-reconciliation` on `/admin/lod`).
- Automatically publishing unreviewed heuristic or LLM candidates into `/graph` or public RDF exports without custodian confirmation.

## Decisions

### Decision 1: Dedicated `WorkRelation` + `WorkLinkCandidate` (Option B) vs. Generalizing `WorkExpansionLink` (Option A)

| Dimension | Option A: Generalize `WorkExpansionLink` (`catalog.work_expansion_links`) | Option B: Dedicated `catalog.work_relations` + `inventory.work_link_candidates` (Chosen) |
|---|---|---|
| **Multiplicity & `Work` ORM** | `WorkExpansionLink.expansion_work_id` has `unique=True` (`app/db/core.py:327`) and `Work.base_game` has `uselist=False` (`app/db/core.py:270`). Supporting many-to-many cross-media adaptations (e.g., a film adapting both a novel and a stage play, or a Work that is both an expansion and adapted) forces dropping `unique=True` and breaking `Work.base_game` 1:1 semantics. | `catalog.work_expansion_links`, `Work.base_game` (`uselist=False`), and `Work.expansions` remain untouched. `catalog.work_relations` uses `UNIQUE (source_work_id, target_work_id, relation_type)` supporting true N:M directed relations. |
| **SHACL & Ontology Validation** | `WorkExpansionLinkShape` (`docs/ontology/iqoqo-shapes.ttl:71-108`) restricts `iqoqo:link_type` to `("is_expansion_of")`, `ExpansionWorkShape` (`lines 150-163`) bans `ContainerAggregation` on `sh:targetSubjectsOf iqoqo:is_expansion_of`, and `ontology_validation.validate_container_not_linked_as_expansion()` (`app/core/ontology_validation.py:53-73`, called unconditionally by `frbr_service.link_expansion_to_base()` at `line 985`) blocks any `F16` Container Work regardless of `link_type`. Widening `WorkExpansionLink` risks falsely blocking box-set `F16` Works from cross-media adaptation links unless every guard is refactored. | `WorkExpansionLinkShape` and `ExpansionWorkShape` stay 100% isolated for board games. New `iqoqo:WorkRelation` and `iqoqo:WorkLinkCandidate` OWL classes + `WorkRelationShape` / `WorkLinkCandidateShape` (`sh:SPARQLConstraint` banning `?src = ?tgt`, controlled `relation_type` and `status`) register cleanly in `docs/ontology/iqoqo.ttl`, `docs/ontology/iqoqo-shapes.ttl`, and `scripts/sync_ontology.py`. |
| **`catalog` vs `inventory` Leak Prevention** | Stores unverified/dismissed heuristic and LLM triage rows (`resolved_by_id -> auth.users`) inside `catalog.work_expansion_links`, requiring every catalog/RDF/Graph reader to remember `WHERE status == 'accepted'` or risk leaking unconfirmed suggestions. | Enforces iqoqo's structural schema split (`app/db/core.py:16-25`): `catalog.work_relations` holds **only confirmed bibliographic relations** (making candidate leakage into `/graph` or RDF structurally impossible), while `inventory.work_link_candidates` mirrors `inventory.duplicate_candidates` for custodian triage. |
| **`frbr_merge.py` & ETL Impact** | Already listed in `REFPOINTS_BY_TIER["work"]` (`app/core/frbr_merge.py:115-116`) and `scripts/etl/{backup,merge}.py`, though natural keys would still require adding `link_type` to prevent merge collisions. | Requires registering `WorkRelation` (`source_work_id`, `target_work_id`) and `WorkLinkCandidate` (`source_work_id`, `target_work_id`) in `app/core/frbr_merge.py` (`_WORK_REFPOINTS`), updating `documented["work"]` in `tests/test_frbr_merge_coverage.py:153`, and adding tables to `scripts/etl/{backup,merge}.py`, with self-link cleanup when `source == target` after merge. |

**Rationale:** Choose **Option B**. The `unique=True` constraint on `expansion_work_id`, `uselist=False` on `Work.base_game`, `validate_container_not_linked_as_expansion()`, and `catalog`-vs-`inventory` separation make overloading `WorkExpansionLink` brittle and prone to regression in `boardgame-expansion-modeling` and candidate leak prevention. The extra `frbr_merge.py` registration is mechanical and enforced by CI (`tests/test_frbr_merge_coverage.py`).

### Decision 2: Directionality, Controlled Relation Lexicon, and DAG Enforcement

- **Directionality (`source_work_id -> target_work_id`):** Store `(source_work_id = derived_work_id, target_work_id = base_work_id)` so `source_work` is the derivative/adaptation and `target_work` is the original/source `Work` (e.g., *The Lord of the Rings (2001 film)* `->` *The Lord of the Rings (novel)*). This maps 1:1 to `frbroo:R2_is_derivative_of` (`F1_Work -> F1_Work`) and `schema:isBasedOn` without inverting predicates during RDF serialization.
- **Controlled `relation_type` Lexicon:** `("is_adaptation_of", "is_derivative_of", "inspired_by", "sequel_to", "spin_off_of", "companion_to")`, with `is_adaptation_of` and `is_derivative_of` emitting `frbroo:R2_is_derivative_of` + `schema:isBasedOn` (and other controlled derivative types also aligning under `frbroo:R2_is_derivative_of` / `rdfs:subPropertyOf` in `docs/ontology/iqoqo.ttl` + `schema:isBasedOn`).
- **Self-Link & Cycle (DAG) Guards:** Enforce `CHECK (source_work_id <> target_work_id)` at the database layer, `SH.SPARQLConstraint` in `iqoqo-shapes.ttl`, and a bounded BFS/DFS reachability check in `work_linking_service` before committing any confirmed `WorkRelation` (rejecting cycles with HTTP `409` / `ValueError`).
- **Alternative Considered:** Storing symmetric undirected pairs (`source_id < target_id`). Rejected because `frbroo:R2_is_derivative_of` and `schema:isBasedOn` are inherently asymmetric (film is based on novel, not vice versa).

### Decision 3: Two-Stage Reconciliation Pipeline (`app/core/work_linking_service.py`)

Mirror `app/core/duplicate_service.py` without invoking `frbr_merge`:
1. **Cross-Media Eligibility:** Compute each Work's normalized media category set from child `Expression.content_type` mapped via `shared/taxonomy.yaml` `format_aliases` (`book`→`text`, `video`→`movie`, `audio`/`sound`→`music`, etc.). Skip Works without Expressions and skip pairs with identical single-medium category sets (leaving same-medium duplicates to `/admin/duplicates`).
2. **Stage 1 — Heuristic Blocking & Scoring (`ENGINE_HEURISTIC`, default):**
   - Keyset scan (`SCAN_PAGE_SIZE = 200`, `selectinload` on `expressions`, `contributions`, `semantic_links`, `series_memberships`).
   - Blocking keys (`MAX_BLOCK_SIZE = 40`): normalized full title (`normalize_title()`), colon/hyphen franchise stem (`text` before `:` / ` - ` when length >= 4), prefix/suffix keys, shared `WorkSeriesMembership.series_work_id`, and shared/related DBpedia `SemanticLink` stem.
   - Scoring: combines normalized title similarity / whole-token containment (*"The Lord of the Rings"* vs *"The Lord of the Rings: The Fellowship of the Ring"*) + optional creator overlap + LOD corroboration. Crucially, unlike `duplicate_service.classify_pair()` (which auto-rejects low-title-similarity pairs or weights disjoint creators heavily against duplication), cross-media scoring **MUST NOT auto-reject disjoint creator sets** (since a novel credits author *J.R.R. Tolkien* while a film credits director *Peter Jackson*).
3. **Stage 2 — Optional Local Ollama (`ENGINE_LLAMA`):**
   - Reuses `ollama_base_url()`, `ollama_model()`, `check_ollama_health()`, `MAX_LLM_EVALUATIONS_PER_RUN = 200`, and SSRF-validated `OLLAMA_URL`. Evaluates grey-zone pairs, returning structured `verdict`, `relation_type`, `source_is` (determining `derived -> base` direction, assisted by earliest child Manifestation year), `confidence`, and `reasoning`.
4. **Idempotent Queue Persistence:** Preload existing `(source, target)` unordered pairs across ALL `WorkLinkCandidate` statuses (`pending`, `accepted`, `dismissed`) and existing `WorkRelation` rows so dismissed/confirmed pairs are never re-queued. Back with portable order-insensitive unique index on `inventory.work_link_candidates` (`CASE` expression matching `DuplicateCandidate`) and `IntegrityError` handling.

### Decision 4: `GraphService` Edge Category Trade-Off (`"derivatives"` vs `"parts_expansions"`)

- **Options Considered:**
  1. **Add `"derivatives"` (chosen)** to `VALID_EDGE_CATEGORIES` (`app/core/graph_service.py:36`), `app/api/docs.py:863`, and `ALL_EDGE_CATEGORIES` (`frontend/components/graph/frbr-relation-graph.tsx:51`), exposed as a dedicated `"Cross-media / Derivatives"` filter pill in `/graph` (enabled by default when no `edge_types` query filter is passed, matching existing defaults).
  2. **Fold into `"parts_expansions"`:** Avoids updating `VALID_EDGE_CATEGORIES`, but conflates board-game expansions and box-set physical parts with cross-media adaptations so users cannot toggle adaptations independently.
- **Coordination with `C140` / `C143`:** Adding `"derivatives"` in `graph_service.py`, `docs.py`, and `frbr-relation-graph.tsx` is additive and orthogonal to `C140` (depth/SPARQL benchmarking) and `C143` (multi-root `Person`/object picker). `GraphService._expand_work()` queries only `catalog.work_relations` (both `source_work_id == work.id` and `target_work_id == work.id`, deterministic `order_by(WorkRelation.id.asc())`) via `enqueue_neighbor("work", ...)` so `MAX_GRAPH_NODES = 150` and `Item` visibility stay enforced.

### Decision 5: RDF/JSON-LD Serialization (`build_collection_rdf_graph()`)

- In `app/core/frbr_service.py`, `_enrich_graph_from_db()` (`lines 2606-2921`) already collects `seen_works: set[int]` across `Item`, `Manifestation`, `Expression`, `Work`, and dict inputs. Add one batched query over `WorkRelation` where `WorkRelation.source_work_id.in_(seen_works)` OR `WorkRelation.target_work_id.in_(seen_works)`.
- For each confirmed `WorkRelation`, mint canonical URIs via `_frbr_uri("work", ...)` and emit `(derived_uri, FRBROO.R2_is_derivative_of, base_uri)` and `(derived_uri, SCHEMA.isBasedOn, base_uri)` (`FRBROO` and `SCHEMA` are already bound in `build_collection_rdf_graph()` and JSON-LD `@context` in `stream_collection_to_rdf` / `serialize_collection_to_rdf`). Update `_enrich_dict_item()` to support optional `derivative_links` matching `series_memberships` / `semantic_links`. Never query `inventory.work_link_candidates` during RDF generation.

### Decision 6: Custodian API, CLI, OpenAPI 3.1, and Admin UI

- **API (`/api/v1/admin/work-links*` on `admin_bp`):**
  - `GET /api/v1/admin/work-links/candidates` & `GET /api/v1/admin/work-links`: `@require_auth` + `@require_permission(PermissionName.READ_METADATA)` + SQL `LIMIT`/`OFFSET` pagination + `func.count()` (`# pylint: disable=not-callable`).
  - `POST /api/v1/admin/work-links/scan`: `@require_auth` + `@require_permission(PermissionName.WRITE_METADATA)` + `@limiter.limit("5 per minute")` + `is_federation_head_mode()` `403` guard.
  - `POST /api/v1/admin/work-links/candidates/<id>/accept`, `POST /api/v1/admin/work-links/candidates/<id>/dismiss`, `POST /api/v1/admin/work-links` (manual link), `DELETE /api/v1/admin/work-links/<id>`: `@require_auth` + `@require_permission(PermissionName.WRITE_METADATA)` + `is_federation_head_mode()` `403` guard.
  - Request schemas in `app/api/schemas.py` using Pydantic v2 `ConfigDict(extra="forbid")`.
  - Update `_get_route_tag()` in `app/api/docs.py:76` to match `path.startswith("/api/v1/admin")` alongside `"/api/admin"` so all `/api/v1/admin/work-links*` endpoints receive the `"Admin"` tag and explicit schemas in `assemble_complete_openapi_spec()`.
- **CLI (`scripts/reconcile_cross_media.py`):** Mirrors `scripts/detect_duplicates.py` (`--dry-run` default, `--apply`, `--engine heuristic|llama`, `--limit`, `--threshold`, `--skip-health-check`, `--quiet`, `run_scan(app=...)` for direct Pytest, exit codes `0/1/2`) plus `Makefile` target.
- **Admin UI (`/admin/work-links`):** Mirrors `/admin/duplicates/page.tsx` + `DuplicateReviewer` (`AdminSidebar` entry gated on `PermissionName.WRITE_METADATA`, `AdminLayout` mobile exclusion, Shadcn primitives, heuristic-vs-LLM provenance badges, manual Work search using `/api/v1/admin/works/search`, and `next-intl` sentence-case translations in `en.json` and `pl.json`).

## Risks / Trade-offs

- **Risk: `test_frbr_merge_coverage.py` CI failure on new `works.id` FKs** → Register all four FK columns (`WorkRelation.{source,target}_work_id`, `WorkLinkCandidate.{source,target}_work_id`) in `app/core/frbr_merge.py` (`_WORK_REFPOINTS`), update `documented["work"]` in `tests/test_frbr_merge_coverage.py`, and add merge cleanup for self-links (`source == target`) and duplicate collisions.
- **Risk: False positives on multi-part franchises (e.g., *Lord of the Rings* trilogy vs single book)** → Use Stage 1 franchise stem blocking (`: ` / ` - ` prefix) to surface candidates in the review queue with confidence and heuristic/LLM provenance rather than auto-confirming; custodian confirmation remains mandatory before graph/RDF publication.
- **Risk: Disjoint creators across mediums (*Tolkien* vs *Peter Jackson*)** → Explicitly omit creator-mismatch auto-rejection in cross-media `classify_pair()`, relying on title/franchise normalization, optional LOD/series signals, and optional Ollama adjudication.
- **Risk: Sibling changes (`C138`, `C140`, `C143`) modifying `visual-frbr-relation-graph` or `frbr-relation-graph.tsx`** → Use `## ADDED Requirements` in specs and additive `"derivatives"` category registration so merges remain conflict-free regardless of landing order.

## Migration Plan

1. Create a single linear Alembic migration chaining directly from `v1_1_0_serial_issn_issues` with `revision` length $\le 32$ chars (e.g., `v1_1_2_cross_media_work_links`, 29 chars) using dialect-aware schema prefixes (`catalog` / `inventory` on PostgreSQL, `None` on SQLite).
2. `upgrade()` creates `catalog.work_relations` and `inventory.work_link_candidates` with self-link `CHECK` constraints, `relation_type` / `status` / `resolution_source` `CHECK` constraints, confidence range `CHECK`, and order-insensitive unique index on `work_link_candidates` (compiling cleanly on both PostgreSQL and SQLite).
3. `downgrade()` drops `inventory.work_link_candidates` and `catalog.work_relations` in reverse order, restoring the linear head to `v1_1_0_serial_issn_issues` with zero impact on existing FRBR tables.

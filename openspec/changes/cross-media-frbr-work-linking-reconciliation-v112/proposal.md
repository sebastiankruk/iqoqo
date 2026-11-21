## Why

Cross-media franchises cataloged in iqoqo—such as *The Lord of the Rings* novels and film adaptations or *Harry Potter* books and movies—currently live as isolated `Work` subgraphs with no semantic connection between creative mediums, leaving them disconnected in `/graph` and RDF/JSON-LD exports. We need a non-merging cross-media `Work -> Work` linking and reconciliation pipeline so custodians can discover, review, and confirm adaptation/derivative relationships while strictly preserving the four-tier FRBR ontology (`Work -> Expression -> Manifestation -> Item`).

## What Changes

- **Dedicated Cross-Media Relation & Candidate Data Model**: Introduce `WorkRelation` (`catalog.work_relations`) for confirmed `Work -> Work` derivative/adaptation edges and `WorkLinkCandidate` (`inventory.work_link_candidates`) for the triage queue (`pending`, `accepted`, `dismissed`), keeping `WorkExpansionLink` and `ExpansionWorkShape` strictly scoped to board game expansions (`is_expansion_of`). Enforce self-link prohibition (`source_work_id != target_work_id`) and cycle/DAG prevention on confirmed `R2_is_derivative_of` edges.
- **Two-Stage Cross-Media Reconciliation Engine & Batch CLI**: Add `app/core/work_linking_service.py` using bounded keyset pagination (`SCAN_PAGE_SIZE = 200`), normalized title/franchise blocking, shared creator/series/LOD corroboration across distinct `Expression.content_type` categories (without auto-rejecting disjoint creators), and optional local Ollama adjudication (`ENGINE_HEURISTIC` default vs `ENGINE_LLAMA` with SSRF-validated `OLLAMA_URL`)—never invoking `frbr_merge`. Expose standalone CLI `scripts/reconcile_cross_media.py` (`--dry-run` default, `--apply`, `--engine heuristic|llama`, exit codes `0/1/2`) and a `Makefile` target.
- **Custodian Admin REST API & Security Guards**: Expose `/api/v1/admin/work-links*` routes on `admin_bp` with `PermissionName.READ_METADATA` (queue reads) and `PermissionName.WRITE_METADATA` (scan, accept, dismiss, manual link/unlink), `@limiter.limit` on scan, Pydantic v2 `ConfigDict(extra="forbid")` request schemas, SQL `LIMIT`/`OFFSET` pagination, `is_federation_head_mode()` `403` write guards, and OpenAPI 3.1 registration (including matching `/api/v1/admin` in `_get_route_tag` in `app/api/docs.py`).
- **Custodian Admin UI & Localization**: Add `/admin/work-links` (`AdminLayout` mobile exclusion, `AdminSidebar` link gated on `PermissionName.WRITE_METADATA`, Shadcn primitives, heuristic-vs-LLM provenance badges, manual Work linking, and sentence-case `next-intl` translations in `en.json` and `pl.json`).
- **Graph Explorer & RDF/JSON-LD Emission (Accepted-Only)**: Extend `GraphService._expand_work()` and `build_collection_rdf_graph()` (`_enrich_graph_from_db()` + `_enrich_dict_item()`) to emit accepted-only cross-media derivative links (`frbroo:R2_is_derivative_of` + `schema:isBasedOn`, direction `derived_work -> source_work`), strictly omitting `pending`/`suggested`/`dismissed` candidates.
- **Ontology/SHACL Sync, Merge Integrity & Linear Migration**: Update `docs/ontology/iqoqo.ttl`, `docs/ontology/iqoqo-shapes.ttl`, and `scripts/sync_ontology.py`; register new `works.id` foreign keys in `app/core/frbr_merge.py` (`REFPOINTS_BY_TIER["work"]`), `tests/test_frbr_merge_coverage.py`, and `scripts/etl/{backup,merge}.py`; and add a linear Alembic migration (`down_revision = "v1_1_0_serial_issn_issues"`, `len(revision) <= 32`).

## Capabilities

### New Capabilities

- `cross-media-work-linking-reconciliation`: Non-merging cross-media `Work -> Work` derivative relation model, two-stage heuristic + optional local Ollama candidate detection engine, standalone dry-run-by-default CLI, Custodian `/api/v1/admin/work-links*` REST API with RBAC and `FEDERATION_HEAD_MODE` guards, and `/admin/work-links` review UI.

### Modified Capabilities

- `frbr-ontology`: Add requirement enforcing that cross-media adaptations remain unmerged distinct `Work` entities connected by `Work -> Work` derivative relations while medium remains on `Expression.content_type` / `Manifestation.format`.
- `visual-frbr-relation-graph`: Add requirement exposing accepted-only cross-media derivative edges between `Work` nodes in `GET /api/catalog/graph` and `/graph` edge filtering while omitting `pending`/`suggested`/`dismissed` candidates.
- `semantic/rdf-serialization`: Add requirement emitting `frbroo:R2_is_derivative_of` and `schema:isBasedOn` triples (`derived_work -> source_work`) for accepted cross-media `Work` links in `build_collection_rdf_graph()`, suppressing unaccepted candidates.
- `semantic/ontology-sync`: Add requirement registering `WorkRelation` and `WorkLinkCandidate` OWL classes, `frbroo:R2_is_derivative_of` property contracts, and SHACL shapes in `docs/ontology/iqoqo.ttl`, `docs/ontology/iqoqo-shapes.ttl`, and `scripts/sync_ontology.py`.
- `frbr/merge-integrity`: Add requirement ensuring Work merges re-point `WorkRelation` and `WorkLinkCandidate` `works.id` foreign keys via `REFPOINTS_BY_TIER["work"]` and collapse duplicate or self-referential links cleanly.

## Impact

- **Backend Models & Migrations**: `app/db/core.py`, `app/db/models.py`, new linear Alembic revision off `v1_1_0_serial_issn_issues`.
- **Backend Core & API**: `app/core/work_linking_service.py` (new), `app/core/graph_service.py`, `app/core/frbr_service.py`, `app/core/frbr_merge.py`, `app/api/admin.py`, `app/api/schemas.py`, `app/api/docs.py`, `app/api/federation_guard.py`.
- **Ontology & Tooling**: `docs/ontology/iqoqo.ttl`, `docs/ontology/iqoqo-shapes.ttl`, `scripts/sync_ontology.py`, `scripts/reconcile_cross_media.py` (new), `scripts/etl/backup.py`, `scripts/etl/merge.py`, `Makefile`.
- **Frontend**: `frontend/app/admin/work-links/page.tsx` (new), `frontend/components/admin/work-link-reviewer.tsx` (new), `frontend/components/admin/admin-sidebar.tsx`, `frontend/components/graph/frbr-relation-graph.tsx`, `frontend/lib/api/admin.ts`, `frontend/types/{admin,frbr}.ts`, `frontend/messages/{en,pl}.json`.
- **Untouched Boundaries**: `boardgame-expansion-modeling`, `semantic/lod-reconciliation`, and `semantic/lod-linking` remain unchanged; `C138`, `C140`, and `C143` are coordinated without overlap via `## ADDED Requirements`.

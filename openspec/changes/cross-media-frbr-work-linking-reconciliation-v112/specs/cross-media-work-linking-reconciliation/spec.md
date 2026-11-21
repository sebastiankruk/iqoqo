## Purpose

Provides non-merging cross-media FRBR Work-to-Work derivative linking and two-stage heuristic plus optional local Ollama candidate reconciliation across distinct media expressions, exposed through a batch CLI, a RBAC- and federation-guarded Custodian Admin API, and an accessible Custodian review UI.

## ADDED Requirements

### Requirement: Non-Merging Cross-Media Work-to-Work Relation and Candidate Lifecycle

The system SHALL model confirmed cross-media derivative/adaptation relationships between distinct `Work` entities without invoking FRBR entity merging, preserving separate `Work` records per creative medium while enforcing self-link prohibition and acyclicity (DAG) on confirmed `R2_is_derivative_of` links. Unconfirmed detections SHALL live in a separate candidate queue with lifecycle states `pending`, `accepted`, and `dismissed`.

#### Scenario: Rejecting self-referential cross-media Work link

- **GIVEN** a `Work` record `W`
- **WHEN** an operator or API caller attempts to create a cross-media relation or candidate with `source_work_id == W.id` and `target_work_id == W.id`
- **THEN** the system MUST reject the request with a validation error (HTTP `400` via API) and MUST NOT persist a self-referential link.

#### Scenario: Preventing cycles in confirmed derivative Work links

- **GIVEN** an accepted cross-media link asserting `Work B` is derivative of `Work A` (`B -> A`)
- **WHEN** a custodian attempts to accept or manually create a confirmed link asserting `Work A` is derivative of `Work B` (`A -> B`) or any transitive cycle back to `A`
- **THEN** the system MUST reject the operation with HTTP `409` or `400` and preserve the directed acyclic graph (DAG) invariant.

#### Scenario: Preserving board game expansion modeling boundaries

- **GIVEN** an existing board game `Work` linked via `WorkExpansionLink` (`is_expansion_of`) or aggregated in an `F16_Container_Work`
- **WHEN** cross-media linking or reconciliation runs across the catalog
- **THEN** board game `WorkExpansionLink` uniqueness (`expansion_work_id`), `ExpansionWorkShape`, and `F16` container guards MUST remain unaffected, and an `F16` box-set or series `Work` MUST still be permitted to participate in cross-media derivative links.

### Requirement: Two-Stage Cross-Media Reconciliation Engine

The system SHALL provide a two-stage cross-media reconciliation engine that scans `Work` entities in bounded keyset pages, compares pairs whose child `Expression.content_type` category sets differ (cross-media pairs only), blocks by normalized title/franchise stem, shared creator, shared series, or shared/related `SemanticLink` authority signals without auto-rejecting disjoint creator sets, and classifies candidates deterministically under `ENGINE_HEURISTIC` (default) or adjudicates grey-zone pairs via optional local Ollama under `ENGINE_LLAMA` using an SSRF-validated `OLLAMA_URL`. Dismissed and already-linked pairs MUST NOT be re-queued on subsequent scans.

#### Scenario: Detecting cross-media adaptation with disjoint creators under default heuristic engine

- **GIVEN** a novel `Work` (*The Lord of the Rings*, author `J.R.R. Tolkien`, `Expression.content_type = "text"`) and a film `Work` (*The Lord of the Rings: The Fellowship of the Ring*, director `Peter Jackson`, `Expression.content_type = "movie"`) with no running Ollama service
- **WHEN** the reconciliation scan executes with default `engine="heuristic"`
- **THEN** the engine MUST pair the two Works across distinct media categories via normalized title/franchise blocking without auto-rejecting due to disjoint creator sets, MUST persist a `pending` candidate with `resolution_source="heuristic"`, and MUST NOT invoke `frbr_merge` or modify `Work`/`Expression`/`Manifestation` rows.

#### Scenario: Adjudicating grey-zone cross-media pair with optional local Ollama engine

- **GIVEN** two cross-media `Work`s (*Harry Potter and the Philosopher's Stone* book `Work` and film `Work`) whose similarity score falls in the grey-zone band and a reachable SSRF-validated `OLLAMA_URL`
- **WHEN** the reconciliation scan executes with `engine="llama"`
- **THEN** the engine MUST request structured adjudication within the bounded per-run LLM cap, record `resolution_source="llama"`, store confidence and `llm_reasoning` on the `pending` candidate, and preserve `derived_work -> source_work` directionality.

#### Scenario: Idempotent re-scan skips dismissed and accepted pairs

- **GIVEN** a candidate pair `(W_movie, W_book)` previously marked `dismissed` or `accepted`
- **WHEN** a subsequent heuristic or Ollama scan evaluates the same pair in either order
- **THEN** the engine MUST skip creating a duplicate candidate and MUST NOT overwrite the existing `dismissed` or `accepted` decision.

### Requirement: Standalone Dry-Run-Default Cross-Media Reconciliation CLI

The system SHALL expose a standalone batch CLI script (`scripts/reconcile_cross_media.py`) defaulting to non-mutating `--dry-run` inspection, requiring `--apply` to persist new `pending` candidates, supporting `--engine heuristic|llama`, `--limit`, `--threshold`, and `--skip-health-check`, and returning standardized exit codes (`0` on success, `1` on runtime failure, `2` when an explicit `llama` prerequisite check fails).

#### Scenario: Dry-run CLI execution writes zero database records

- **GIVEN** unlinked *Harry Potter* book and movie `Work`s in the catalog
- **WHEN** an operator invokes `scripts/reconcile_cross_media.py` without `--apply`
- **THEN** the script exits with code `0`, prints candidate summary counts, and inserts zero rows into the database.

#### Scenario: CLI with llama engine fails fast when Ollama is unreachable

- **GIVEN** `engine="llama"` and an unreachable local Ollama endpoint without `--skip-health-check`
- **WHEN** an operator invokes `scripts/reconcile_cross_media.py --engine llama --apply`
- **THEN** the script exits with code `2` and writes no partial candidate rows.

### Requirement: RBAC-Protected, Federation-Guarded, OpenAPI-Documented Custodian API

The system SHALL expose Custodian REST endpoints under `/api/v1/admin/work-links*` supporting SQL `LIMIT`/`OFFSET` paginated candidate and relation listing (`PermissionName.READ_METADATA`), rate-limited scan triggering (`PermissionName.WRITE_METADATA`), candidate acceptance/dismissal (`PermissionName.WRITE_METADATA`), and manual Work-to-Work linking/unlinking (`PermissionName.WRITE_METADATA`). All request payloads SHALL enforce Pydantic v2 `ConfigDict(extra="forbid")` validation, all mutating endpoints SHALL enforce `is_federation_head_mode()` returning HTTP `403`, and all routes SHALL be tagged and schema-documented in OpenAPI 3.1.

#### Scenario: Read-only metadata user can view queue but cannot mutate links

- **GIVEN** an authenticated user holding `PermissionName.READ_METADATA` without `PermissionName.WRITE_METADATA`
- **WHEN** the user calls `GET /api/v1/admin/work-links/candidates`
- **THEN** the API returns HTTP `200` with SQL-paginated candidates and `meta`/`pagination` totals;
- **WHEN** the same user calls `POST /api/v1/admin/work-links/scan`, `POST /api/v1/admin/work-links/candidates/<id>/accept`, `POST /api/v1/admin/work-links/candidates/<id>/dismiss`, `POST /api/v1/admin/work-links`, or `DELETE /api/v1/admin/work-links/<id>`
- **THEN** the API returns HTTP `403`.

#### Scenario: Federation head mode blocks cross-media link mutations

- **GIVEN** an instance running with `FEDERATION_HEAD_MODE` enabled and an authenticated custodian holding `PermissionName.WRITE_METADATA`
- **WHEN** the custodian invokes any mutating `/api/v1/admin/work-links*` endpoint
- **THEN** the endpoint MUST return HTTP `403` with a JSON error envelope (`{"error": ..., "code": 403}`) and perform no database writes.

#### Scenario: OpenAPI 3.1 specification includes Admin-tagged work-links endpoints

- **GIVEN** the Flask application OpenAPI spec assembler
- **WHEN** `/api/docs/openapi.json` is generated
- **THEN** every `/api/v1/admin/work-links*` endpoint MUST appear under the `"Admin"` tag with complete query parameter and `requestBody` Pydantic schemas.

### Requirement: Custodian Cross-Media Review Admin UI and Localization

The system SHALL provide a web-only Custodian review page at `/admin/work-links` reachable from `AdminSidebar` (both gated on `PermissionName.WRITE_METADATA` and excluded from Capacitor native mobile builds via `AdminLayout`), built with Shadcn UI primitives, surfacing heuristic vs. LLM provenance badges and optional LLM reasoning, side-by-side Work medium summaries, manual Work search-and-link controls, and `next-intl` sentence-case translations in `en.json` and `pl.json`.

#### Scenario: Standard user or non-custodian is excluded from sidebar and admin page

- **GIVEN** an authenticated user without `PermissionName.WRITE_METADATA`
- **WHEN** `AdminSidebar` renders or the user navigates to `/admin/work-links`
- **THEN** the `"Cross-media links"` sidebar link MUST NOT render and `/admin/work-links` MUST redirect away to `/profile`.

#### Scenario: Custodian confirms a cross-media candidate with provenance badges

- **GIVEN** an authenticated custodian viewing `/admin/work-links` with both `heuristic` and `llama` candidates
- **WHEN** the reviewer inspects the queue and confirms acceptance of a *Lord of the Rings* film-to-novel candidate
- **THEN** the UI displays distinct provenance badges (`heuristic` vs. `llama` percentage + reasoning), invokes `POST /api/v1/admin/work-links/candidates/<id>/accept`, refreshes the queue, and renders all labels from `next-intl` sentence-case keys in `en.json` and `pl.json`.

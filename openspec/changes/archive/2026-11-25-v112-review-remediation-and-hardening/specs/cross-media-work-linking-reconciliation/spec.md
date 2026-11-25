## ADDED Requirements

### Requirement: Hardened Cross-Media LLM Configuration, Derivation Direction, and Atomic Candidate Resolution

The cross-media reconciliation engine and Custodian admin review workflow SHALL enforce centralized LLM governance, accurate taxonomy derivation ranking, atomic candidate state transitions, and responsive manual `Work` search:

1. **LLM Governance & Sync Scan Bounds (`app/core/work_linking_service.py`, `app/api/admin.py`):** Ollama tie-breaker calls MUST resolve `OLLAMA_URL` (including Docker `http://host.docker.internal:11434` fallback) and `OLLAMA_DEDUPE_MODEL` through `ConfigService`, MUST skip all LLM probing and inference when `ALLOW_LLM` is disabled (`false`/`0`/`no`/`off`), MUST pass `allow_redirects=False` on outbound HTTP requests, and MUST cap synchronous HTTP scan requests (`POST /api/v1/admin/work-links/scan`) to a bounded wall-clock LLM budget (`<= 15s`, default sync cap `<= 5` pairs) while preserving full batch limits for CLI runs (`scripts/reconcile_cross_media.py`) and supporting `USE_DOCKER=true` in `make reconcile-cross-media`.
2. **Taxonomy-Aligned Derivation Rank (`app/core/work_linking_service.py`):** `_MEDIA_DERIVATION_RANK` MUST map canonical `shared/taxonomy.yaml` category keys—including `"text"` (`1`), `"audiobook"` (`2`), `"magazine"` (`2`), `"movie"` (`3`), `"music"` (`4`), `"game"` (`5`), `"map"` (`6`), and `"lego"` (`7`)—so a derivative film, game, or music `Work` is consistently oriented as `source_work_id` (`derivative`) pointing to the original `"text"`/`"book"` `Work` as `target_work_id` (`original`).
3. **Single-Commit Atomic Acceptance & Pair-Override Validation (`app/core/work_linking_service.py`):** `accept_candidate()` MUST reject candidates whose `status != "pending"` with a `409` conflict error, MUST reject any `source_work_id`/`target_work_id` override whose `{source_work_id, target_work_id}` set does not equal `{candidate.source_work_id, candidate.target_work_id}` with a `400` validation error, and MUST create/reuse the `WorkRelation` and update the `WorkLinkCandidate` within a single database `commit()`.
4. **Custodian Manual Work Search & Triage Ergonomics (`frontend/components/admin/work-link-reviewer.tsx`):** Manual `Work` search inputs in `WorkLinkReviewer` MUST debounce user keystrokes and parse the canonical `GET /api/catalog/graph/search` response envelope (`data: CatalogGraphSearchCandidate[]`, via `useCatalogGraphSearch`), render `"—"` when `candidate.confidence` is `null`, provide a one-click direction swap between `source` and `target` `Work`s during manual creation or candidate review, and include an explicit `"Cancel"` button in the relation deletion confirmation dialog.

#### Scenario: Synchronous admin scan respects disabled ALLOW_LLM and bounded wall-clock budget

- **GIVEN** `InstanceSettings` / `ConfigService` has `ALLOW_LLM=false` (or an unreachable/slow `OLLAMA_URL`) and ambiguous cross-media `Work` pairs exist
- **WHEN** a Custodian invokes `POST /api/v1/admin/work-links/scan` with `use_llm=true`
- **THEN** when `ALLOW_LLM=false`, zero outbound requests are sent to Ollama and ambiguous pairs remain `pending` with heuristic provenance
- **AND** when `ALLOW_LLM=true`, Ollama requests use `ConfigService` settings with `allow_redirects=False` and stop invoking the LLM once the synchronous wall-clock budget (`<= 15s`) or sync pair cap is reached, returning HTTP `200` without timing out the Gunicorn worker

#### Scenario: Book Work categorized as taxonomy text ranks as original target of film adaptation

- **GIVEN** a literary `Work` (`W_novel`) whose Expression `content_type` resolves to canonical taxonomy category `"text"` and a film `Work` (`W_film`) whose category resolves to `"movie"`
- **WHEN** `scan_cross_media_candidates()` evaluates `(W_novel, W_film)`
- **THEN** `_infer_direction()` assigns `source_work_id = W_film.id` (derivative adaptation) and `target_work_id = W_novel.id` (original work) with `relation_type = "is_adaptation_of"`

#### Scenario: Accepting a candidate commits atomically, validates direction-swap overrides, and blocks re-acceptance

- **GIVEN** a `pending` `WorkLinkCandidate` between `Work` `10` and `Work` `20`
- **WHEN** a Custodian submits `accept` with swapped `{source_work_id: 20, target_work_id: 10}`
- **THEN** the `WorkRelation(20 -> 10)` creation and `WorkLinkCandidate(status="accepted")` update persist in a single atomic transaction
- **AND** if a caller passes an unrelated `Work` ID (`{source_work_id: 10, target_work_id: 999}`), the service raises a `400` `WorkLinkValidationError` without mutating either table
- **AND** if a caller attempts to `accept` a candidate whose `status` is already `"accepted"` or `"dismissed"`, the service raises a `409` conflict error

#### Scenario: Custodian searches Works with debounced graph search envelope and swaps link direction in UI

- **GIVEN** a Custodian on `/admin/work-links` typing `"Hobbit"` into the manual link Source or Target search field
- **WHEN** the debounced `GET /api/catalog/graph/search?q=Hobbit&types=work&limit=8` response returns `{ "success": true, "data": [{ "entity_type": "work", "entity_id": 42, "label": "The Hobbit" }], "error": null }`
- **THEN** `"The Hobbit"` renders as a selectable option, selecting both Source and Target enables `"Create link"` and a direction-swap control, null-confidence candidates render `"—"` instead of `"0%"`, and opening the delete confirmation dialog presents both `"Cancel"` and `"Delete"` actions

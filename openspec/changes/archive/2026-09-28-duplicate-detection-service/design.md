## Context

See `proposal.md` for motivation and background.

iqoqo organizes library assets using the strict FRBR Group 1 ontology: `Item` (physical/digital exemplar) -> `Manifestation` (edition, format, publication date, ISBN) -> `Expression` (realization, language, version) -> `Work` (intellectual creation). Currently, duplicate entities can be created during manual catalog entry, external barcode scans, and batch imports. While administrators can manually edit entities via `/v1/admin/frbr/*`, there is no automated mechanism to detect duplicates across the catalog, no queue for reviewing candidate matches, and no atomic merge operation to consolidate duplicate Works or Manifestations without corrupting child relationships.

Local LLM capabilities are already established in the codebase (using `OLLAMA_URL` for vision cover extraction in `app/utils/vision.py` and `scripts/generate_ai_covers.py`). This design extends local LLM inference to semantic duplicate detection and defines atomic, FRBR-compliant merge semantics.

## Goals / Non-Goals

**Goals:**
- Implement a two-stage detection pipeline: heuristic candidate screening (fuzzy text/token matching) followed by local LLM pairwise semantic evaluation via Ollama.
- Persist detected duplicate pairs in a dedicated `duplicate_candidates` database table with confidence scores, status tracking, and LLM reasoning.
- Provide atomic, transactional FRBR merge functions in `app/core/duplicate_service.py` that re-parent child entities (Expressions for Works, Items for Manifestations), reconcile contributions, delete/archive obsolete parent records, and log actions to `EntityAuditLog`.
- Expose authenticated administrative REST endpoints under `/v1/admin/duplicates` guarded by `@require_auth`, `@admin_required`, and role permissions.
- Provide an operational CLI script `scripts/detect_duplicates.py` supporting batch scans, candidate thresholding, and dry-run execution.
- Build a side-by-side comparison and merge review interface in `frontend/app/admin/duplicates/page.tsx` and `frontend/components/admin/duplicate-reviewer.tsx`.

**Non-Goals:**
- Fully autonomous automated merging without administrator confirmation (every merge requires explicit administrative review).
- Merging Item entities directly (Items represent distinct physical or digital copies; duplicates exist at the Work and Manifestation tiers).
- Heavy vector database infrastructure (e.g. pgvector or external vector store); heuristic filtering + Ollama pairwise evaluation provides privacy-preserving, local-first detection for v0.8.2.

## Decisions

### 1. Two-Tier Detection Pipeline (Heuristic Candidate Screening + LLM Pairwise Verification)
- **Decision**: Detection runs in two phases:
  1. *Heuristic Screening*: Query Works and Manifestations to find potential candidate pairs using normalized title similarity (Levenshtein ratio / trigrams), sort titles, author overlap, or matching ISBNs (for Manifestations).
  2. *LLM Verification*: Send candidate pairs to Ollama via `POST /api/chat` with `format: "json"` asking the model to evaluate semantic equivalence, outputting a JSON object with `verdict` (boolean), `confidence` (float between 0.0 and 1.0), and `reasoning` (string).
- **Rationale**: An unconstrained pairwise comparison on an N-item library requires $O(N^2)$ LLM calls, which is computationally infeasible on local hardware. Heuristic screening prunes the candidate set to $O(K)$ high-probability pairs before invoking LLM inference.
- **Alternatives considered**:
  - *Pure heuristic / string distance matching*: High false positive rate on works with similar titles (e.g., "Dune" vs "Dune Messiah") and misses subtitle variations or transliterations.
  - *Vector embeddings / pgvector*: Adds dependency weight and embedding index maintenance overhead; deferred to a future dedicated vector search milestone.

### 2. Dedicated `DuplicateCandidate` Persistence Table
- **Decision**: Add a `duplicate_candidates` table in PostgreSQL with columns:
  - `id` (primary key, integer / UUID)
  - `entity_tier` (varchar: `'work'` or `'manifestation'`)
  - `source_id` (foreign key to source entity)
  - `target_id` (foreign key to target entity)
  - `confidence` (float, 0.0 - 1.0)
  - `llm_reasoning` (text)
  - `status` (varchar: `'pending'`, `'merged'`, `'dismissed'`)
  - `created_at`, `resolved_at`, `resolved_by_id` (foreign key to `users`)
  - Unique constraint on `(entity_tier, LEAST(source_id, target_id), GREATEST(source_id, target_id))` to avoid duplicate pairs in reverse order.
- **Rationale**: Decouples batch CLI/background detection runs from interactive administrative review, tracks review history, and prevents re-flagging previously dismissed false positives.
- **Alternatives considered**: Storing candidates purely in Redis or in-memory queues; rejected because candidate state must persist across server restarts and provide review history.

### 3. Strict FRBR Merge Semantics & Transaction Isolation
- **Decision**: Implement merge operations within an atomic database transaction (`db.session.begin_nested()` or transaction block) using PostgreSQL row-level locks (`with_for_update`):
  - **Work Merge (Source Work -> Target Work)**:
    - Update all child `Expression` rows: set `expression.work_id = target_work.id`.
    - Transfer or deduplicate `WorkContribution` and `WorkPart` links.
    - Transfer `WorkExpansionLink` records.
    - Delete or soft-archive `source_work`.
    - Create `EntityAuditLog` record with action `merge_work`, recording source/target IDs and child counts.
  - **Manifestation Merge (Source Manifestation -> Target Manifestation)**:
    - Update all child `Item` rows: set `item.manifestation_id = target_manifestation.id`.
    - Transfer `ManifestationContribution` links.
    - Preserve and consolidate ISBNs strictly on the target `Manifestation` (F3).
    - Delete or soft-archive `source_manifestation`.
    - Create `EntityAuditLog` record with action `merge_manifestation`.
- **Rationale**: Prevents orphaned Expressions or Items and guarantees FRBR Group 1 hierarchy compliance. If any step fails, the entire transaction rolls back.
- **Alternatives considered**: Cascading delete on merge; rejected as it would destroy all child items and expressions owned by users.

### 4. Resilient Local LLM Integration via Ollama HTTP API
- **Decision**: Implement Ollama communication in `app/core/duplicate_service.py` using standard HTTP requests to `OLLAMA_URL` (default: `http://localhost:11434`), model `OLLAMA_MODEL` (default: `llama3:latest`), configured with a 15-second request timeout and structured system prompt enforcing JSON output.
- **Rationale**: Reuses established environment configuration (`OLLAMA_URL` from `.env.example`), keeps the system local-first and privacy-respecting, and requires no heavy external LLM framework dependencies.
- **Alternatives considered**: Cloud-only LLM APIs (violates local-first architecture and offline library support).

### 5. Admin Review UI with Side-by-Side Diff and Primary Selection
- **Decision**: Create a dedicated view at `frontend/app/admin/duplicates/page.tsx` and `frontend/components/admin/duplicate-reviewer.tsx`. The UI renders:
  - Queue summary with filters by entity tier (`work` / `manifestation`) and status (`pending` / `resolved`).
  - Side-by-side comparison card displaying title, sort title, creator credits, publication year, child counts, cover images, and ISBNs (for Manifestations).
  - Primary entity selector (swap button allowing the administrator to choose which entity to keep and which to merge into it).
  - Confidence badge and expandable LLM reasoning explanation.
  - "Merge Duplicates" confirmation dialog and "Dismiss False Positive" action.
- **Rationale**: Provides clear visual context so administrators never make accidental destructive changes, and allows choosing which record has the higher quality metadata as the surviving primary.

## Risks / Trade-offs

- **[Risk: Heuristic screening misses subtle duplicates with translated or radically altered titles]** → **Mitigation**: Provide an admin manual candidate submission tool allowing administrators to input any two entity IDs for on-demand LLM evaluation and merge queuing.
- **[Risk: Large catalogs cause high latency during full table scans]** → **Mitigation**: In `scripts/detect_duplicates.py`, batch candidate processing using SQLAlchemy `yield_per()`, scope searches by media category/format, and support `--limit`, `--offset`, and `--since` CLI parameters.
- **[Risk: Concurrent modifications while merge transaction executes]** → **Mitigation**: Use `with_for_update()` locking on source and target entities and child collections, rolling back cleanly with descriptive HTTP error if a concurrency conflict occurs.
- **[Risk: Ollama process offline or model missing]** → **Mitigation**: CLI script and API endpoints test Ollama health upfront (`GET /api/tags`), reporting a clear prerequisite message (`Ollama unreachable at OLLAMA_URL or model missing; run 'ollama pull llama3'`) without crashing.

## Migration Plan

1. **Alembic Migration**: Generate and apply Alembic migration creating the `duplicate_candidates` table with indices on `(status, confidence)` and `(entity_tier, source_id, target_id)`.
2. **Backend Deployment**: Add `app/core/duplicate_service.py`, extend `app/api/admin.py` with duplicate routes, and install CLI script `scripts/detect_duplicates.py`.
3. **Frontend Deployment**: Add `frontend/app/admin/duplicates/page.tsx`, `frontend/components/admin/duplicate-reviewer.tsx`, and API client functions in `frontend/lib/api/admin.ts`.
4. **Rollback Strategy**: Dropping the `duplicate_candidates` table rolls back the feature cleanly without impacting any core FRBR entity tables.

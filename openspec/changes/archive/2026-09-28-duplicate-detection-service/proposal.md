## Why

As collections expand through manual cataloging, external metadata lookups, and batch imports, duplicate entities inevitably accumulate across the catalog—such as variant titles of the same intellectual Work or multiple entries for the same Manifestation edition. Automated duplicate detection powered by local LLMs (Ollama) paired with an administrative review and merge workflow ensures catalog data integrity, eliminates data fragmentation, and preserves strict FRBR hierarchy without risking accidental data loss as part of the v0.8.2 release (C15: FRBR Duplicate Detection).

## What Changes

- Add a duplicate detection and entity resolution service in `app/core/duplicate_service.py` implementing candidate evaluation, local LLM prompt construction, and atomic FRBR-compliant merge transactions.
- Add an operational CLI detection script `scripts/detect_duplicates.py` utilizing local Ollama instances to evaluate candidate Work and Manifestation pairs with similarity scoring and reasoning.
- Introduce `DuplicateCandidate` persistence model in `app/db/models.py` tracking candidate entity pairs, entity tier (`work` or `manifestation`), confidence score, LLM reasoning rationale, and lifecycle status (`pending`, `merged`, `dismissed`).
- Expose administrative REST endpoints in `app/api/admin.py` under `/v1/admin/duplicates` to list pending candidates, trigger detection scans, execute merges, and dismiss candidates.
- Implement strict FRBR merge semantics:
  - **Work Merging**: Re-parent child Expressions from source Work to target Work, reconcile Work contributions and expansion links, delete/archive source Work, and record `EntityAuditLog` entries.
  - **Manifestation Merging**: Re-parent child Items from source Manifestation to target Manifestation, reconcile manifestation contributions and physical attributes (ISBNs belong strictly to Manifestation F3), delete/archive source Manifestation, and record `EntityAuditLog` entries.
- Create an administrative Duplicate Review UI at `frontend/app/admin/duplicates/page.tsx` with component `frontend/components/admin/duplicate-reviewer.tsx` featuring side-by-side entity comparisons, confidence metrics, and interactive merge/dismiss controls.
- Add TypeScript API client helpers in `frontend/lib/api/admin.ts` for duplicate candidate querying and merge actions.

## Capabilities

### New Capabilities
- `operations/duplicate-detection`: LLM-assisted duplicate detection across FRBR Works and Manifestations, candidate queue persistence, and administrative merge operations preserving FRBR hierarchy integrity.

### Modified Capabilities
<!-- None: introduces a dedicated duplicate detection and merge capability -->

## Impact

- **API & Routing**: New admin endpoints at `/v1/admin/duplicates` on `admin_bp` in `app/api/admin.py` guarded by `@require_auth` and `@admin_required`.
- **Backend Services**: New core service in `app/core/duplicate_service.py` handling candidate generation heuristics, Ollama API invocation, and transactional FRBR entity merging.
- **Database & Models**: New database table `duplicate_candidates` managed via Alembic migration, with foreign keys to source/target entity IDs and lifecycle status tracking.
- **CLI & Scripts**: New maintenance CLI script `scripts/detect_duplicates.py` for manual or cron-based background scanning.
- **Frontend**: New administrative page `frontend/app/admin/duplicates/page.tsx` and UI components `frontend/components/admin/duplicate-reviewer.tsx` integrated with TanStack Query and Sonner toasts.
- **Dependencies**: Leverages existing Ollama local API integration (`OLLAMA_URL`, default: `http://localhost:11434`), SQLAlchemy ORM session transactions, and PostgreSQL.

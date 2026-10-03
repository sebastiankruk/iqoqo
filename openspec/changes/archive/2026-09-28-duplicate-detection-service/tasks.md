## 1. Database Model & Migration

- [x] 1.1 Create `DuplicateCandidate` SQLAlchemy model in `app/db/models.py` with fields `id`, `entity_tier` (`work` or `manifestation`), `source_id`, `target_id`, `confidence`, `llm_reasoning`, `status` (`pending`, `merged`, `dismissed`), `created_at`, `resolved_at`, and `resolved_by_id`, verifying model definitions and relationships in unit tests.
- [x] 1.2 Generate and execute Alembic migration creating the `duplicate_candidates` table with indices on `(status, confidence)` and a unique constraint preventing duplicate pairs in reverse order, verifying migration upgrade and downgrade cleanly.

## 2. Core Detection & Merge Service

- [x] 2.1 Implement heuristic candidate screening in `app/core/duplicate_service.py` to identify potential duplicate Works and Manifestations using title normalization, sort titles, creator overlaps, and ISBN matching, verifying candidate generation in unit tests.
- [x] 2.2 Implement local Ollama API client in `app/core/duplicate_service.py` with structured JSON prompt formatting and response validation for pairwise confidence scoring and rationale generation, verifying resilient error handling with mocked Ollama API tests.
- [x] 2.3 Implement atomic FRBR Work merge in `app/core/duplicate_service.py`, re-parenting child Expressions, reconciling Work contributions and expansion links, removing source Work, and recording entries in `EntityAuditLog`, verifying hierarchy preservation in unit tests.
- [x] 2.4 Implement atomic FRBR Manifestation merge in `app/core/duplicate_service.py`, re-parenting child Items, consolidating Manifestation contributions, maintaining ISBNs strictly on the Manifestation entity (F3), removing source Manifestation, and recording entries in `EntityAuditLog`, verifying hierarchy preservation in unit tests.

## 3. Operational CLI Script

- [x] 3.1 Create `scripts/detect_duplicates.py` CLI supporting `--tier (work|manifestation|all)`, `--threshold`, `--limit`, and `--dry-run` options with progress reporting and Ollama health verification, verifying script flags and exit codes via CLI unit tests.

## 4. Administrative REST API Endpoints

- [x] 4.1 Add administrative endpoints under `/v1/admin/duplicates` in `app/api/admin.py` for listing pending candidates with filtering/pagination, dismissing false positives, and triggering scan runs, guarded by `@require_auth` and `@admin_required`, verifying permission enforcement in API tests.
- [x] 4.2 Add administrative merge endpoint `POST /v1/admin/duplicates/<id>/merge` in `app/api/admin.py` supporting primary entity selection and executing transactional FRBR merges, verifying success, bad request, and rollback scenarios in API tests.

## 5. Admin Review UI

- [x] 5.1 Implement TypeScript API client methods in `frontend/lib/api/admin.ts` for querying duplicate candidate queues, triggering scans, executing merges, and dismissing candidates, verifying type definitions compile cleanly.
- [x] 5.2 Build `frontend/components/admin/duplicate-reviewer.tsx` providing side-by-side entity comparison (titles, creators, dates, child counts, covers, ISBNs), primary entity toggle, confidence badges, and confirmation dialogs, verifying rendering in React component tests.
- [x] 5.3 Create `frontend/app/admin/duplicates/page.tsx` and integrate the Duplicate Review link into the Admin Navigation layout, verifying page load and interactive controls in frontend tests.

## 6. End-to-End Validation & Verification

- [x] 6.1 Implement end-to-end integration test suite in `tests/test_duplicate_detection.py` validating the complete lifecycle from candidate detection to administrative merge across both Works and Manifestations, verifying all tests pass with `pytest`.

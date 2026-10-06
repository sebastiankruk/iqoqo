## 1. Database Schema & Roadmap Normalization

- [x] 1.1 Update `RoadmapItem` model in `app/db/roadmap.py` to add `expression_id` foreign key, update `to_dict()` to resolve Expression titles/creators, and declare the single-FRBR-level check constraint, verifying imports with `python3 -c "from app.db.roadmap import RoadmapItem"`
- [x] 1.2 Create linear Alembic migration in `migrations/versions/` chained after current head to add `expression_id`, clean/normalize existing `roadmap_items` records with ambiguous/zero entity references, and apply the `check_roadmap_item_single_frbr_level` constraint, verifying upgrade and downgrade execution on test database
- [x] 1.3 Update roadmap API endpoints in `app/api/roadmap.py` and schemas to validate that exactly one of `work_id`, `expression_id`, or `manifestation_id` is supplied on creation/update, verifying with `pytest tests/test_roadmap.py`

## 2. Backend Relation Management Services

- [x] 2.1 Implement `reassign_frbr_parent()` in `app/core/frbr_service.py` to reparent Expressions to Works and Manifestations to Expressions with hierarchy validation, cycle prevention, and `EntityAuditLog` recording, verifying with unit tests in `tests/test_admin_frbr.py`
- [x] 2.2 Implement `merge_frbr_entities()` in `app/core/frbr_service.py` for Works, Expressions, and Manifestations to reparent children, merge metadata and event contributions, delete source records, and record audit logs, verifying with unit tests in `tests/test_admin_frbr.py`
- [x] 2.3 Implement `split_frbr_entity()` in `app/core/frbr_service.py` to extract designated child subsets into newly created sibling entities at the same FRBR level with audit logging, verifying with unit tests in `tests/test_admin_frbr.py`

## 3. Admin API Endpoints for FRBR Relations

- [x] 3.1 Implement `/api/v1/admin/frbr/relations/reassign`, `/merge`, and `/split` endpoints in `app/api/admin.py` protected by `@require_auth` and `@require_permission(PermissionName.WRITE_METADATA)`, verifying request validation and error responses with integration tests
- [x] 3.2 Update Pydantic / validation schemas in `app/api/schemas.py` for reassign, merge, and split payloads, verifying validation rules for invalid cross-level requests

## 4. Frontend Types & Admin API Client

- [x] 4.1 Define relation management TypeScript types in `frontend/types/frbr.ts` and `frontend/lib/api/admin.ts` (`FrbrReassignPayload`, `FrbrMergePayload`, `FrbrSplitPayload`, `FrbrImpactPreview`), verifying type checking with `npm --prefix frontend run typecheck`
- [x] 4.2 Add `reassignFrbrParent()`, `mergeFrbrEntities()`, and `splitFrbrEntity()` client functions in `frontend/lib/api/admin.ts`, verifying with frontend unit tests in `frontend/__tests__/lib/api/admin-frbr.test.ts`

## 5. Frontend Admin Relation Management UI

- [x] 5.1 Implement `RelationManagementDialog` component with action tabs (Reassign, Merge, Split), entity search autocomplete, and live impact preview of affected child counts in `frontend/components/admin/relation-management-dialog.tsx`, verifying rendering with React Testing Library
- [x] 5.2 Wire relation management action triggers into the entity action menus in `frontend/components/admin/frbr-editor.tsx`, ensuring TanStack Query cache invalidation and toast feedback upon execution, verifying component tests in `frontend/__tests__/components/admin/frbr-editor.test.tsx`

## 6. End-to-End Testing & Verification

- [x] 6.1 Add comprehensive end-to-end regression tests in `tests/test_admin_frbr.py` covering reparenting, merging duplicate works/manifestations, splitting entities, and roadmap item constraint enforcement
- [x] 6.2 Run full lint and test verification across backend and frontend via `IQOQO_AI_MODE=1 make lint` and `pytest tests/test_admin_frbr.py tests/test_roadmap.py` to confirm zero regressions

## 1. Backend Celery Task Enhancement

- [x] 1.1 Update `batch_link_catalog_lod_task` in `app/core/tasks.py` to count links added per authority (`dbpedia`, `geonames`, `wordnet`) and maintain a rolling ring buffer of recent item-by-item resolution events (`meta["recent_logs"]`). Verify with unit tests in `tests/test_tasks_celery.py`.
- [x] 1.2 Add support for optional filtering parameters (`unlinked_only: bool`, `throttle_delay: float`) in `batch_link_catalog_lod_task`. Verify filtering logic with unit tests.

## 2. Admin & Custodian REST API Endpoints

- [x] 2.1 Implement `POST /api/admin/lod/reconcile` in `app/api/admin.py` with authorization check permitting both `admin` and `custodian` roles (and `REFETCH_METADATA` permission), query extraction (all vs unlinked), Celery dispatch, and HTTP 202 task ID response. Verify with API unit tests.
- [x] 2.2 Implement `GET /api/admin/lod/tasks/<task_id>` in `app/api/admin.py` returning active Celery task progress (total, processed, percentage, authority counts, and recent logs) accessible to admins and custodians. Verify with API unit tests.
- [x] 2.3 Implement `GET /api/admin/lod/stats` in `app/api/admin.py` querying lifetime database counts of `SemanticLink` rows grouped by authority, accessible to admins and custodians. Verify with API unit tests.

## 3. Frontend API Client & React Hooks

- [x] 3.1 Define TypeScript types (`LODReconciliationTaskStatus`, `LODStats`, `LODLogEntry`) in `frontend/types/admin.ts`. Verify type compilation with `npm run type-check`.
- [x] 3.2 Add API functions (`triggerLodReconciliation`, `getLodTaskStatus`, `getLodStats`) in `frontend/lib/api/admin.ts`. Verify export declarations.
- [x] 3.3 Implement TanStack Query hooks (`useLodStats`, `useLodTaskStatus` with adaptive 1.5s refetch interval during active states, and `useTriggerLodReconciliation` mutation) in `frontend/lib/api/hooks/admin.ts`. Verify hooks in frontend test environment.

## 4. Admin & Custodian LOD Reconciliation Dashboard UI

- [x] 4.1 Implement metric summary cards (`frontend/components/admin/lod/metric-cards.tsx`) displaying processed manifestations count and authority breakdown (DBpedia, GeoNames, WordNet) using Shadcn UI Card and Lucide icons. Verify component renders properly in unit tests.
- [x] 4.2 Implement batch control and progress bar panel (`frontend/components/admin/lod/batch-control.tsx`) strictly enforcing <= 4 buttons heuristic (single primary CTA `Start Full Scan`, options dropdown for unlinked-only and throttling, cancel action). Verify button states and progress updates.
- [x] 4.3 Implement live resolution audit log stream (`frontend/components/admin/lod/audit-log-stream.tsx`) with authority badges, status chips (`SUCCESS`, `SKIPPED`, `WARN`), auto-scroll toggle, and category filters. Verify log filtering behavior.
- [x] 4.4 Assemble the full dashboard page at `frontend/app/admin/lod/page.tsx` with breadcrumbs, route guards permitting both `admin` and `custodian` roles, admin/custodian navigation links, and i18n support in `frontend/messages/en.json` and `frontend/messages/pl.json` (strict sentence case). Verify page rendering and route navigation.

## 5. Automated Multi-Tier Testing & Verification

- [x] 5.1 Create comprehensive backend test suite in `tests/test_admin_lod.py` covering permissions gating for both `admin` and `custodian` roles (and rejection for standard collectors), batch task execution, authority counting, and API endpoint schemas with `pytest tests/test_admin_lod.py`.
- [x] 5.2 Create frontend component test suite in `frontend/__tests__/admin/lod-dashboard.test.tsx` verifying card metric rendering, live progress polling transitions, and log stream filtering with `npm test`.
- [x] 5.3 Author End-to-End Playwright test suite in `frontend/tests/e2e/admin-lod.spec.ts` covering both Administrator and Custodian logins, navigation to `/admin/lod`, triggering batch reconciliation, verifying progress animation, inspecting log entries, and verifying rejection for standard users with `npx playwright test frontend/tests/e2e/admin-lod.spec.ts`.
- [x] 5.4 Run full linting, type-checking, secret scanning, and formatting across backend and frontend (`make lint`, `npm run type-check`, `make secret-scan`).

## 6. Active Task Persistence, Hierarchy Count Fix & UI Refinements

- [x] 6.1 Update `batch_link_catalog_lod_task` in `app/core/tasks.py` to set and clear Redis active task key `lod:active_task_id` on task lifecycle events.
- [x] 6.2 Implement `GET /api/admin/lod/tasks/active` and add concurrency lock check returning HTTP 409 Conflict to `POST /api/admin/lod/reconcile` in `app/api/admin.py`.
- [x] 6.3 Fix `get_lod_stats` in `app/api/admin.py` to count distinct manifestations linked directly or via parent `Work` semantic links.
- [x] 6.4 Add `lod_authority` and `lod_status` query parameters to catalog manifestation endpoints in `app/api/manifestations.py`.
- [x] 6.5 Add `getActiveLodTask` in `frontend/lib/api/admin.ts` and `useActiveLodTask` hook in `frontend/lib/api/hooks/admin.ts`.
- [x] 6.6 Update `frontend/app/admin/lod/page.tsx` to automatically restore active task state and stream on reload.
- [x] 6.7 Update `frontend/components/admin/lod/metric-cards.tsx` to link metric cards to `/collection` with `lod_authority` and `lod_status` query parameters.
- [x] 6.8 Default `unlinkedOnly` to `true` in `frontend/components/admin/lod/batch-control.tsx`.
- [x] 6.9 Improve refresh stats button visual feedback (loading spinner and confirmation toast) in `frontend/app/admin/lod/page.tsx`.
- [x] 6.10 Improve auto-scroll toggle visual contrast with prominent active badge styling in `frontend/components/admin/lod/audit-log-stream.tsx`.
- [x] 6.11 Add reciprocal navigation links to `/admin/lod` in `frontend/app/admin/content/page.tsx` and `frontend/app/admin/sparql/page.tsx`.
- [x] 6.12 Update test suites in `tests/test_admin_lod.py` and `frontend/__tests__/admin/lod-dashboard.test.tsx` to cover active task recovery, 409 conflict, hierarchical link calculation, and drill-down links. Run `make lint` and `make test`.
- [x] 6.13 Add `GEONAMES_USERNAME` to `API_KEYS` in `app/api/admin.py`, expose in `API_SERVICE_GROUPS` in `frontend/components/admin/instance-settings.tsx`, and update `GeoNamesClient.resolve_location` in `app/core/lod_linking_service.py` to prioritize `InstanceSettings.get_value("GEONAMES_USERNAME")` over environment variable.

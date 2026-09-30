## Why

Currently, entity resolution to Linked Open Data (LOD) authorities (DBpedia, GeoNames, WordNet) can only be triggered per individual manifestation on its detail page or transparently upon creation. Library custodians and instance administrators have no centralized interface to trigger catalog-wide reconciliation, monitor real-time background progress, view counts of links generated per authority (DBpedia, GeoNames, WordNet), or inspect item-by-item resolution logs. For collections with hundreds or thousands of physical media items, manual re-linking imposes severe friction (thousands of repetitive clicks) with zero progress observability. A unified batch linking and tracking dashboard accessible to both Administrators and Custodians is needed to provide one-click reconciliation and real-time observability.

## What Changes

- **Per-Authority Metric & Log Tracking in Celery ETL**: Extend `batch_link_catalog_lod_task` in `app/core/tasks.py` to count links generated broken down by authority (`dbpedia`, `geonames`, `wordnet`) and stream structured resolution logs (timestamp, entity ID, title, status, links added) within task state metadata. Maintain an active task lock key in Redis (`lod:active_task_id`) to track running scans and prevent duplicate concurrent jobs.
- **Admin & Custodian LOD REST Endpoints**: Add endpoints in `app/api/admin.py` accessible to users with `admin` or `custodian` role (or `refetch:metadata` permission):
  - `POST /api/admin/lod/reconcile`: Trigger on-demand catalog or scoped batch linking jobs (supporting options: `unlinked_only` defaulting to `true`, `force_refresh`, `throttle_delay`). Returns HTTP 409 Conflict if a scan is already executing.
  - `GET /api/admin/lod/tasks/<task_id>`: Query active or completed task progress (percentage, items processed, per-authority counts, and recent resolution events).
  - `GET /api/admin/lod/tasks/active`: Query current in-flight reconciliation task ID and progress to restore UI state on browser reload.
  - `GET /api/admin/lod/stats`: Query lifetime database link counts grouped by authority and entity type, properly calculating linked editions across both manifestation-level and work-level semantic links.
- **Instance Settings Panel Integration for GeoNames**: Add `GEONAMES_USERNAME` to `InstanceSettings` and administrative settings panel (`frontend/components/admin/instance-settings.tsx` and `app/api/admin.py`), enabling administrators to configure GeoNames credentials directly in the UI with fallback to environment variables.
- **Catalog Filtering by LOD Facet**: Extend catalog and manifestation endpoints (`app/api/manifestations.py`) with `lod_authority` and `lod_status` query parameters to allow filtering collection items by external LOD presence.
- **Administrative & Custodian LOD Reconciliation Dashboard**: Implement `frontend/app/admin/lod/page.tsx` accessible to Administrators and Custodians incorporating:
  - Metric summary cards displaying total processed items and links attributed to DBpedia, GeoNames, and WordNet, acting as clickable drill-downs to the collection viewer filtered by LOD authority.
  - Active task persistence that reconnects on page reload to stream progress without losing state.
  - Progress indicator displaying live batch completion percentage and estimated time.
  - Streamlined control panel adhering to `/iqoqo-ux-auditor` heuristics (strictly <= 4 buttons, single primary CTA `Start Full Scan`, options dropdown defaulting to "Unlinked entries only", disabled during active scans).
  - Filterable live audit log stream displaying item resolution events with authority badges, status indicators, and high-contrast auto-scroll toggle.
  - Integrated navigation links between Custodian content views (`/admin/content`, `/admin/sparql`) and `/admin/lod`.
  - Responsive refresh button with active loading spinner and confirmation toast.
- **Multi-tier Automated Test Suite**:
  - Backend integration tests in `tests/test_admin_lod.py` covering permissions gating for both `admin` and `custodian` roles, rate-limiting, 409 concurrency lock, active task querying, and task state tracking.
  - Frontend component tests in `frontend/__tests__/admin/lod-dashboard.test.tsx` verifying card metrics, progress updates, reload rehydration, and log filtering.
  - End-to-end browser test in `frontend/tests/e2e/admin-lod.spec.ts` using Playwright to validate both Administrator and Custodian navigation, job trigger, and live progress hydration.

## Capabilities

### New Capabilities
- `semantic/lod-reconciliation`: Centralized batch LOD reconciliation engine accessible to Administrators and Custodians, task progress tracking with authority metric breakdowns, active task restoration, catalog facet drill-downs, real-time audit log streaming, and E2E Playwright verification.

### Modified Capabilities

## Impact

- **Backend**: `app/core/tasks.py`, `app/api/admin.py`, `app/api/manifestations.py`.
- **Frontend**: `frontend/app/admin/lod/page.tsx`, `frontend/app/admin/content/page.tsx`, `frontend/app/admin/sparql/page.tsx`, `frontend/components/admin/lod/*`, `frontend/lib/api/admin.ts`, `frontend/lib/api/hooks/admin.ts`, `frontend/messages/en.json`, `frontend/messages/pl.json`.
- **Tests**: `tests/test_admin_lod.py`, `frontend/__tests__/admin/lod-dashboard.test.tsx`, `frontend/tests/e2e/admin-lod.spec.ts`.

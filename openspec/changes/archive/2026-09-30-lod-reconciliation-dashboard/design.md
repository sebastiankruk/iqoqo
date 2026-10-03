## Context

Following the completion of `lod-linking-and-etl`, iQoQo possesses core entity resolution clients (`DBpediaClient`, `GeoNamesClient`, `WordNetMapper`) and background workers (`link_manifestation_lod_task`, `batch_link_catalog_lod_task`). However, background reconciliation operates without administrative or custodian oversight: there is no catalog-level trigger, no real-time progress visibility, no breakdown of links created per external authority, and no visual audit stream.

Both Administrators and Catalog Custodians are responsible for catalog quality and semantic enrichment. Therefore, the batch LOD interface and its corresponding API endpoints must be accessible to both roles.

See `proposal.md` for problem motivation and `specs/semantic/lod-reconciliation/spec.md` for behavioral requirements.

## Goals / Non-Goals

**Goals:**
- Extend `batch_link_catalog_lod_task` to compute live counts by authority (`dbpedia`, `geonames`, `wordnet`) and maintain a ring buffer of recent item-by-item resolution events.
- Implement REST endpoints in `app/api/admin.py` accessible to users with `admin` or `custodian` role (or `REFETCH_METADATA` permission): `POST /api/admin/lod/reconcile`, `GET /api/admin/lod/tasks/<task_id>`, and `GET /api/admin/lod/stats`.
- Create the reconciliation dashboard at `frontend/app/admin/lod/page.tsx` accessible to both Administrators and Custodians, adhering to `/iqoqo-ux-auditor` heuristics (strictly <= 4 buttons, single primary CTA, responsive layout, live progress bar, authority stat cards, filterable log stream).
- Deliver comprehensive multi-tier test automation covering both Admin and Custodian roles: unit & API tests (`pytest`), component tests (`Vitest`), and full browser E2E tests (`Playwright`).

**Non-Goals:**
- Creating a separate persistent database table for individual reconciliation log rows (relying instead on ephemeral task state metadata and lifetime aggregations from `catalog.semantic_links`).
- Manual editing or authoring of external triples directly within the batch dashboard (individual link curation remains scoped to `frontend/components/manifestation/semantic-links.tsx`).

## Decisions

### 1. Unified Access Control for Administrators and Custodians
- **Decision**: Grant access to `/api/admin/lod/*` endpoints and `/admin/lod` frontend dashboard to users with the `admin` role, `custodian` role, or users possessing `PermissionName.REFETCH_METADATA` / `PermissionName.WRITE_METADATA`.
- **Rationale**: Custodians in iQoQo are entrusted with bibliographic taxonomy, metadata curation, and entity normalization. Forcing catalog reconciliation to be admin-only creates an operational bottleneck and prevents curators from maintaining Linked Data completeness.
- **Alternatives Considered**: Creating a separate `/api/custodian/lod/...` endpoint path. Rejected because consolidating under the existing administrative curation module avoids endpoint duplication and keeps routing clean.

### 2. Ring Buffer Task Metadata vs Persistent Log Table
- **Decision**: Store the active item-by-item resolution log stream in Celery task metadata (`meta["recent_logs"]`), capped as a rolling ring buffer of the latest 50 events. Historical and overall counts are computed directly from `catalog.semantic_links` grouped by authority.
- **Rationale**: Prevents database write bloat and transaction overhead on large library runs (e.g. 10,000 items generating 30,000 links). Ephemeral task metadata provides immediate live visual feedback without long-term DB cleanup tasks.
- **Alternatives Considered**: Creating a new `catalog.lod_reconciliation_logs` table. Rejected due to high I/O churn and unnecessary storage cost.

### 3. TanStack Query Interval Polling vs WebSockets / SSE
- **Decision**: The frontend dashboard polls `GET /api/admin/lod/tasks/<task_id>` with an adaptive 1.5s interval via TanStack Query when a job is active (`STARTED` or `PROGRESS`), automatically halting polling when state is `SUCCESS` or `FAILURE`.
- **Rationale**: Integrates cleanly with existing Next.js TanStack Query hooks, requires zero persistent stateful connection infrastructure (no socket tunnels or ASGI proxies), and recovers transparently from transient network hiccups.
- **Alternatives Considered**: Server-Sent Events (SSE). Rejected to avoid stateful proxy connection timeouts and keep backend architectural complexity minimal.

### 4. UX Heuristics & Button Density Discipline (`/iqoqo-ux-auditor`)
- **Decision**: The batch control panel enforces a strict 3-button limit:
  1. Primary CTA: `Start Full Scan` (or `Re-scan All`).
  2. Secondary Action: `Cancel / Stop` (rendered only during active execution).
  3. Tertiary Overflow Dropdown: `Options` (housing scope toggles: "Unlinked entities only", "Force refresh all", "Throttle delay").
- **Rationale**: Complies with the principal UX auditor heuristic forbidding viewports with more than 4 buttons, ensuring clear visual hierarchy and zero cognitive clutter for library administrators and custodians.

### 5. Multi-Persona End-to-End Automated Testing (`/test-automation-wizard`)
- **Decision**: Implement `frontend/tests/e2e/admin-lod.spec.ts` using Playwright, simulating journeys for both an `admin` and a `custodian` user: logging in, navigating via admin menu to `/admin/lod`, initiating a batch reconciliation run, observing progress bar advance, verifying metric card increments, and testing log filter toggles. Non-curator accounts must verify redirection and access denial.
- **Rationale**: Guarantees that role-based access control, frontend navigation guards, API routes, and task serialization operate coherently in a real browser environment.

### 6. Active Task Persistence and Concurrency Guard in Redis (`lod:active_task_id`)
- **Decision**: Track in-flight reconciliation tasks via Redis key `lod:active_task_id`. When `POST /api/admin/lod/reconcile` triggers a task, it checks Redis; if a task ID is already stored and its Celery state is active (`PENDING`, `STARTED`, `PROGRESS`), the request is rejected with `HTTP 409 Conflict`. When a task finishes or fails, the Celery task clears the key.
- **Endpoint**: Expose `GET /api/admin/lod/tasks/active` returning `{ "active_task_id": "...", "status": "..." }` or `{ "active_task_id": null }`.
- **Rationale**: Eliminates race conditions from concurrent duplicate scans and allows the frontend to seamlessly reattach to ongoing jobs when the browser is refreshed or reloaded.

### 7. Hierarchical FRBR-Aware Linked Manifestations Metric
- **Decision**: Compute linked manifestations count as distinct manifestations that either have direct `SemanticLink` rows (`entity_type == "manifestation"`) OR whose parent `Work` has `SemanticLink` rows (`entity_type == "work"`).
- **Rationale**: Under the FRBR ontology, conceptual entity links (such as authors, subjects, and abstract works) are linked to `Work`, whereas physical editions are linked to `Manifestation`. Counting only `entity_type == "manifestation"` incorrectly reports 0 linked editions when links were attached at the Work level.

### 8. Catalog LOD Facet Querying & Metric Card Drill-Down
- **Decision**: Make each metric card on the dashboard an interactive link targeting `/collection` (or `/manifestations`) with query parameters:
  - Total editions: `/collection`
  - Linked editions: `/collection?lod_status=linked`
  - DBpedia: `/collection?lod_authority=dbpedia`
  - GeoNames: `/collection?lod_authority=geonames`
  - WordNet: `/collection?lod_authority=wordnet`
- **Backend**: Extend `app/api/manifestations.py` to join `SemanticLink` and filter results based on `lod_authority` and `lod_status`.
- **Rationale**: Elevates summary metrics from passive numbers into actionable catalog navigation and quality assurance tools.

### 9. UI Ergonomics & Custodian Navigation Harmonization
- **Decision**:
  1. Default the scan option `unlinked_only` to `true` in `batch-control.tsx`.
  2. Provide explicit visual loading spinner and toast notification on the "Refresh stats" button in `frontend/app/admin/lod/page.tsx`.
  3. Improve visual contrast of the "Auto-scroll" toggle in `audit-log-stream.tsx` with a distinct active badge and accent background.
  4. Add reciprocal navigation links to `/admin/lod` in the Custodian Content Management view (`/admin/content`) and SPARQL query view (`/admin/sparql`).
- **Rationale**: Prevents accidental re-scanning of already enriched items, ensures intuitive tactile feedback on actions, improves accessibility, and unifies fragmented administrative/custodian navigation.

### 10. Dynamic InstanceSettings for GeoNames Credentials
- **Decision**: Expose `GEONAMES_USERNAME` in the administrative settings panel (`API_SERVICE_GROUPS` in `frontend/components/admin/instance-settings.tsx` and `API_KEYS` in `app/api/admin.py`). In `GeoNamesClient.resolve_location`, resolve the username dynamically via `InstanceSettings.get_value("GEONAMES_USERNAME")` before falling back to `os.environ.get("GEONAMES_USERNAME", "iqoqo_demo")`.
- **Rationale**: Eliminates the operational friction of requiring server SSH access or container restarts just to configure a GeoNames web service account. Administrators can configure credentials directly through the web UI with immediate effect.

## Risks / Trade-offs

- **[Risk: External Authority Rate-Limiting during Bulk Execution]**  
  *Mitigation*: The batch task applies chunking (10 manifestations per batch) and an adjustable inter-chunk throttle delay (default 0.5s), plus exponential backoff on HTTP 429/503 responses.
- **[Risk: Memory Pressure with Large Catalogs]**  
  *Mitigation*: The backend endpoint queries only primary keys (`select(Manifestation.id)`) using bounded pagination or iterator chunking, avoiding loading complete ORM object graphs into worker process memory.
- **[Risk: Redis Task Result Expiration]**  
  *Mitigation*: Celery task results expire after 24 hours. The dashboard handles non-existent or expired task IDs gracefully by reverting to lifetime database statistics.

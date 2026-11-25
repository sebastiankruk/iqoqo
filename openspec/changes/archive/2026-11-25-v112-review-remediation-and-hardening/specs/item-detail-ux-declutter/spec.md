## ADDED Requirements

### Requirement: Strict WRITE_METADATA Gating on LOD Scan Trigger, Safe Sync Cover Upload Fallback, and Escalation i18n Parity

1. **`SemanticLinks` `"Scan External LOD"` RBAC Alignment (`frontend/components/manifestation/semantic-links.tsx`, `frontend/components/item/item-sidebar.tsx`):** `SemanticLinks` MUST render the `"Scan External LOD"` button (`scanButton` in both compact and full card modes) ONLY when `canEdit` is `true`, and `ItemSidebar` (along with `/work/[id]` and `/manifestation/[id]` callers) MUST compute `canEdit` strictly from `hasPermission(PermissionName.WRITE_METADATA)` (never `isOwner || hasEditPermission`), matching backend `POST /api/manifestations/<id>/reconcile` enforcement (`@require_permission(PermissionName.WRITE_METADATA)`).
2. **Synchronous Cover Upload Fallback Safety (`app/api/manifestations.py`):** When `POST /api/manifestations/<id>/cover/upload` falls back to synchronous `process_tier1_task(...)` execution because Celery/Valkey broker dispatch fails, it MUST pass `llm_permissions={}` so Tier 1 processing never crashes on missing keyword arguments or triggers unintended LLM calls.
3. **Localized Escalation Labels in `ItemActions` (`frontend/components/item/item-actions.tsx`, `frontend/messages/en.json`, `frontend/messages/pl.json`):** Residual hardcoded escalation strings in `ItemActions` (`"Help Request:"` badge prefix and standalone `"Requests"` header) MUST resolve through `ItemDetail.*` translation keys with Polish sentence-case parity in `pl.json`.

#### Scenario: Anonymous visitor or standard item owner without write:metadata does not see Scan External LOD

- **GIVEN** an anonymous visitor OR an authenticated standard item owner (`write:item`, `upload:cover`, but lacking `write:metadata`) expanding `"Linked Open Data"` on `/item/[id]` or viewing `/manifestation/[id]`
- **WHEN** `SemanticLinks` renders
- **THEN** existing accepted authority links are displayed read-only and `"Scan External LOD"` is NOT rendered
- **AND** when a Custodian or Admin holding `write:metadata` views the same section, `"Scan External LOD"` IS rendered and operable

#### Scenario: Synchronous cover upload fallback succeeds when Valkey broker is unavailable

- **GIVEN** Valkey/Celery task dispatch raises an operational error during `POST /api/manifestations/<id>/cover/upload`
- **WHEN** the endpoint executes the synchronous `process_tier1_task` fallback
- **THEN** `process_tier1_task` is invoked with `llm_permissions={}` and completes HTTP `200` cover replacement without raising `TypeError`

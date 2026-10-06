## Context

The escalation (User Requests) feature in iqoqo allows authenticated non-custodian users to submit help requests targeting a FRBR entity (Manifestation or Item). Currently, the system supports only "correction" type requests where users specify a field name and a suggested correct value. A recent UX audit (improve-user-requests-ux) confirmed that users lack the ability to request deletion of entities that were created or scanned by mistake.

The existing data model (`EscalationRequest`) stores `field_name`, `suggested_value`, `current_value`, and `note` — all oriented around metadata correction. The resolution workflow is status-based: `pending → accepted/rejected/duplicate`. On acceptance, no side effects occur — the status change is purely informational.

The current codebase uses Flask (Python) with SQLAlchemy for the backend, Next.js with TypeScript and Shadcn UI for the frontend, and next-intl for i18n with English and Polish locales. Permissions are managed via a YAML-based permission system with auto-generated TypeScript enums.

Key constraints:

- Must be backward compatible: existing correction-type requests and API consumers must continue to work unchanged
- Must respect the existing FRBR entity deletion paths (`delete_manifestation()` in `app/api/manifestations.py`, `delete_item()` in `app/api/items.py`) — no code duplication
- Must respect the existing permission model: `escalate:request` for submission, `escalate:resolve` for resolution, `delete:manifestation`/`delete:item` for entity deletion

## Goals / Non-Goals

**Goals:**

- Allow users to submit "Request Deletion" as a distinct escalation type alongside "Metadata Correction"
- Add conditional validation: deletion requests require a reason note, not field/value pairs
- Enable admins to execute deletion by accepting a deletion-type request (gated by DELETE permissions)
- Display request type badges throughout the UI (submission form, admin queue, user view)
- Ensure custodians without DELETE permissions can still review but not execute deletion requests

**Non-Goals:**

- No support for Work or Expression deletion — only Manifestation and Item (aligned with existing delete endpoints)
- No batch deletion requests (one entity per request)
- No automatic deletion on acceptance by non-admin roles
- No notification system for status changes (future feature)
- No undo/deletion audit trail beyond the existing audit system
- No changes to the resolution status lifecycle (`pending → accepted/rejected/duplicate` remains unchanged)

## Decisions

### Decision 1: `request_type` column approach (not new model or enum table)

**Chosen**: Add a single `request_type` column (`VARCHAR(20)`, default `"correction"`) to the existing `EscalationRequest` model with values `"correction"` and `"deletion"`.

**Rationale**: Minimal schema change. The escalation request lifecycle and status semantics are identical for both types — only the input validation and resolution side effects differ. A single column with a sane default preserves backward compatibility. Existing `field_name` and `suggested_value` columns become nullable at the application level (conditional validation); physically they remain `NOT NULL` with the existing default empty string constraint — the validation layer simply stores empty strings for deletion requests.

**Alternative considered**: Separate `DeletionRequest` model inheriting from a base class. Rejected — adds significant ORM complexity, duplicate relationships, duplicate API logic, and duplicate frontend components for minimal semantic benefit. The two request types share 95% of their lifecycle.

**Alternative considered**: A `request_type` enum table with foreign key. Rejected — overkill for a boolean-like discriminator. A VARCHAR column is simpler, readable in raw SQL, and the CHECK constraint (if added) can enforce valid values at the database level.

### Decision 2: Permission model for deletion resolution

**Chosen**: The resolve endpoint (`PATCH /api/escalations/<id>`) checks if the request is `request_type === "deletion"` and `new_status === "accepted"`. If so, it additionally checks for the appropriate DELETE permission (`delete:manifestation` if targeting a manifestation, `delete:item` if targeting an item). If the resolver lacks the permission, the endpoint returns HTTP 403 with a descriptive error. Custodians with only `escalate:resolve` can still reject or mark deletion requests as duplicate.

**Rationale**: Deletion is destructive and should be gated behind the same permissions as direct entity deletion. Custodians (who may have `escalate:resolve` but not `delete:manifestation`/`delete:item`) can triage and reject inappropriate deletion requests, but cannot accidentally or maliciously delete entities. Only admins, who already have delete capabilities, can execute deletion through this path.

**Alternative considered**: Separate API endpoint for resolving deletion requests (e.g., `PATCH /api/escalations/<id>/execute-deletion`). Rejected — adds route bloat and frontend complexity. A single resolve endpoint with conditional permission checks is simpler.

**Alternative considered**: Allow any custodian to accept deletion, with deletion treated as a separate "request fulfillment" step by admins later. Rejected — creates a confusing two-step workflow where "accepted" doesn't mean "done" for deletion requests, breaking the mental model of the status lifecycle.

### Decision 3: Form UX for request type selection

**Chosen**: A toggle/radio group at the top of the escalation dialog with two options: "Metadata Correction" and "Request Deletion". Selecting "Request Deletion" hides the field_name/suggested_value/current_value fields and shows only a required "Reason for deletion" text area. Selecting "Metadata Correction" shows the existing fields. Default is "Metadata Correction" (backward compatible).

**Rationale**: The radio group pattern is a standard UX for mutually exclusive options. It keeps both request types in the same dialog, avoiding dialog proliferation. The client-side conditional rendering is simpler than managing two separate dialog components. The form adapts naturally; users don't need to understand the implementation — they just pick their intent.

**Alternative considered**: Two separate buttons/dialogs ("Request Correction" / "Request Deletion"). Rejected — clutters the UI with additional trigger buttons. The "Requests" accordion already has limited real estate.

**Alternative considered**: A dropdown select for request type. Rejected — radio buttons are more visible and reduce the required clicks by one. The choice is important enough to warrant prominent UI.

### Decision 4: Entity deletion on acceptance — call existing delete handlers

**Chosen**: When a deletion-type request is accepted, the resolve endpoint calls the existing entity deletion functions directly (importing `delete_manifestation` / `delete_item` from their respective modules, or calling `db.session.delete()` directly with the same cleanup logic). The deleted escalation record itself is handled by the existing cascading delete constraint — the escalation is cascade-deleted when its target entity is removed.

**Rationale**: No code duplication. The existing deletion endpoints already handle all edge cases (scan telemetry nullification for manifestations, virtual vs. physical item distinction, ownership checks for items). The resolve endpoint simply delegates to these existing handlers. The delete operation and escalation status update happen within the same database transaction, ensuring atomicity.

**Alternative considered**: Creating a new shared deletion utility function. Rejected — it would require extracting and refactoring logic from existing endpoints, increasing scope and risk. Delegating to existing handlers is lower risk and the call patterns are already well-tested.

**Alternative considered**: Performing the deletion before committing the status update. Rejected — needs careful transaction management. The implementation SHALL commit the deletion first, then update the escalation status (or vice versa, depending on cascade behavior). Since escalation_requests have `ondelete=CASCADE` on target FK columns, deleting the target entity will cascade-delete the escalation record. This is acceptable: the escalation record is no longer meaningful after the entity is gone. The resolver's action is still recorded in the audit log.

### Decision 5: i18n keys — reuse existing namespace

**Chosen**: Add all new translation keys to the existing `HelpRequests` namespace in `en.json` and `pl.json`.

**Rationale**: The `HelpRequests` namespace already covers escalation-related labels. Adding new keys to the same namespace avoids creating a new namespace that would require additional `useTranslations()` hooks. All components using escalation translations already import `HelpRequests`.

## Risks / Trade-offs

- **[Risk]** Cascade-delete removes the escalation record: When a deletion-type request is accepted and the entity is deleted, the escalation record is cascade-deleted (due to `ondelete=CASCADE` on FK columns). This means the resolved escalation disappears from all history views. → **Mitigation**: The resolver's action is still traceable via the entity audit log. The deletion request's lifecycle (created by user → accepted by admin) is recoverable from audit timestamps. The admins should use a resolution note to document the deletion justification.

- **[Risk]** Field columns store empty strings for deletion requests: Since `field_name` and `suggested_value` remain `NOT NULL` at the database level, deletion requests will store empty strings. This is technically denormalized but safe. → **Mitigation**: Validation layer ensures deletion requests pass empty strings. Frontend conditionally hides these fields so they're never presented as meaningful data.

- **[Trade-off]** No separate test for `delete:manifestation` on work/expression: The spec only covers Manifestation and Item deletion since those are the only entities with existing delete endpoints. → **Acceptable**: Work and Expression deletion is not supported in the system at all. If added later, the deletion-type escalation can be extended.

- **[Risk]** Accidental deletion by mistaken "Accept & Delete" click: An admin could accidentally accept and delete an entity in one click. → **Mitigation**: The "Accept & Delete" button is visually distinct (destructive styling) and labeled unambiguously. A confirmation dialog could be added as a follow-up enhancement (scope of a separate change).

## Migration Plan

1. **Database migration**: Add `request_type` column to `escalation_requests` table with `DEFAULT 'correction'` and `NOT NULL`. No data migration needed — all existing rows get the default value automatically.
2. **Backend deploy**: Deploy the updated `EscalationRequest` model, validation, create, and resolve endpoints. The API is backward compatible (clients not sending `request_type` get `"correction"` by default).
3. **Frontend deploy**: Deploy the updated form, admin queue, and user view components. The frontend passes `request_type` only for new requests; existing requests without the field in the JSON response will display as "Correction" by default (conditional or fallback in the badge component).
4. **Rollback**: Removing the migration (drop column) plus reverting code changes. Existing data is not corrupted since no data transformation occurs — the column defaults to the same behavior as before the change.

## Open Questions

- Should there be a confirmation dialog before "Accept & Delete" to prevent accidental deletion? (Recommended YES, but spec leaves this as a frontend implementation detail.)
- Should the escalation status card on entity detail pages show deletion-type requests differently (e.g., with a trash icon)? (Minor UX enhancement, can be done in a follow-up.)

## Why

The User Requests (escalation) feature currently only supports "correction" requests — users can suggest a field name and new value for metadata fixes. However, there is no mechanism for users to request deletion of a manifestation or item that was scanned or created by mistake. This is a critical gap identified in the improve-user-requests-ux UX audit: users can see and report wrong data, but cannot flag entire entities as candidates for removal. Adding deletion request support closes this gap and aligns the escalation system with real-world library/collection management workflows where erroneous catalog entries need a principled path to deletion.

## What Changes

- **Database schema**: Add `request_type` column (`VARCHAR(20)`, default `"correction"`) to the `EscalationRequest` model with values `"correction"` and `"deletion"`. The existing status CHECK constraint remains unchanged — resolution still flows through the `pending → accepted/rejected/duplicate` lifecycle. A DB migration is required.
- **API validation**: Modify `_validate_escalation_input()` — when `request_type === "deletion"`, `field_name` and `suggested_value` become optional but `note` becomes required (as the deletion reason). When `request_type === "correction"`, existing behavior is preserved.
- **API create endpoint**: Extend `POST /api/escalations/<level>/<target_id>` to accept and store the `request_type` parameter.
- **API resolve endpoint**: Extend `PATCH /api/escalations/<escalation_id>` — when resolving a deletion-type request with `status: "accepted"`, execute actual deletion of the target manifestation or item. This requires the resolver to hold the appropriate DELETE permission (`delete:manifestation` or `delete:item`), not just `escalate:resolve`. The target entity's delete handler is called directly (no code duplication). The `to_dict()` serialization SHALL include `request_type`.
- **Frontend escalation form** (`escalation-trigger.tsx`): Add a request type selector (toggle or radio group) at the top of the dialog: "Metadata Correction" / "Request Deletion". When "Request Deletion" is selected, hide `field_name`/`suggested_value`/`current_value` fields and show only a "Reason for deletion" text area (required). The `EscalationRequest` type definition SHALL include the new `request_type` field.
- **Frontend admin queue** (`escalation-queue.tsx`): Display a `request_type` badge on each card (e.g., "Correction" / "Deletion"). For deletion-type pending requests, the "Accept" button is relabeled "Accept & Delete" and is only enabled if the resolver holds `delete:manifestation` or `delete:item` permission as appropriate. The resolve API call SHALL pass the escalation ID and status; the backend handles the actual deletion.
- **Frontend user view** (`my-escalations.tsx`): Display a `request_type` badge on each request card.
- **i18n**: Add translation keys to `en.json` and `pl.json` for "Metadata Correction", "Request Deletion", "Accept & Delete", "Reason for deletion", "Deletion request submitted", "Request type", "Deletion", etc.
- **Permission model**: Custodians with only `escalate:resolve` CAN view deletion requests and can reject or mark them duplicate, but CANNOT execute deletion. Only admins with `delete:manifestation` and/or `delete:item` can accept and execute deletion-type requests.

## Capabilities

### New Capabilities

- `deletion-request-submission`: Users can select "Request Deletion" as a request type when submitting escalation requests; the form adapts to show only a reason note (no field/value fields); the API validates and stores the `request_type`.
- `deletion-request-resolution`: Admin queue supports deletion-type requests with permission-gated "Accept & Delete" action; accepted deletion requests trigger actual entity deletion on the backend.

### Modified Capabilities

- `custodian-escalation`: EscalationRequest model gains `request_type` column with DB migration; `_validate_escalation_input()` adds conditional validation logic; create endpoint accepts and stores `request_type`; resolve endpoint checks DELETE permissions for deletion-type accepted resolutions and calls entity deletion handlers; `to_dict()` serialization includes `request_type`.

## Impact

- **Database**: `escalation_requests` table — new `request_type` column with migration script
- **Backend API**: `app/api/social.py` — `_validate_escalation_input()`, `create_escalation_request()`, `resolve_escalation_request()` modified; imports added for `Item`/`Manifestation` deletion utilities
- **Backend model**: `app/db/social.py` — `EscalationRequest` class updated with `request_type` column and `to_dict()` updated
- **Frontend components**: `escalation-trigger.tsx`, `escalation-queue.tsx`, `my-escalations.tsx`
- **Frontend types**: `EscalationRequest` type definition gains `request_type` field
- **Frontend API hooks**: `createEscalation()` function signature updated to accept `request_type`
- **Frontend i18n**: `en.json`, `pl.json` — new keys under `HelpRequests` namespace
- **No new API endpoints** — existing routes extended, not replaced
- **No breaking changes** — `request_type` defaults to `"correction"` for backward compatibility with existing requests; existing API consumers that omit `request_type` continue to work

## 1. Schema and Model Changes

- [x] 1.1 Add `request_type` column to `EscalationRequest` model in `app/db/social.py`: `db.Column(db.String(20), default="correction", nullable=False)`, placed after `note` and before `status`
- [x] 1.2 Update `EscalationRequest.to_dict()` in `app/db/social.py` to include `"request_type": self.request_type` in the serialized output
- [x] 1.3 Generate and apply database migration: `flask db migrate -m "Add request_type to escalation_requests"` followed by `flask db upgrade`
- [x] 1.4 Verify migration applies correctly on a dev database with existing escalation rows (all should default to "correction")

## 2. API Validation Changes

- [x] 2.1 Update `_validate_escalation_input()` in `app/api/social.py` to accept an optional `request_type` parameter from the payload (defaulting to `"correction"`)
- [x] 2.2 Add conditional validation: when `request_type === "deletion"`, skip `field_name`/`suggested_value` requirements and instead require `note` to be non-empty; when `request_type === "correction"` (or absent), preserve existing validation behavior
- [x] 2.3 Add validation for invalid `request_type` values: reject with 400 error if not `"correction"` or `"deletion"`
- [x] 2.4 Update the validated dict returned by `_validate_escalation_input()` to include `"request_type"` key

## 3. API Create Endpoint Changes

- [x] 3.1 Update `create_escalation_request()` in `app/api/social.py` to pass `request_type` from validated data to the `EscalationRequest` kwargs
- [x] 3.2 Ensure `field_name` and `suggested_value` are passed as empty strings (NOT None) for deletion requests to satisfy the `nullable=False` column constraint
- [x] 3.3 Update the `createEscalation()` function signature in `frontend/lib/api/escalations.ts` to accept `request_type` field in the data parameter

## 4. API Resolve Endpoint Changes

- [x] 4.1 Update `resolve_escalation_request()` in `app/api/social.py` to detect deletion-type requests (check `escalation.request_type === "deletion"` and `new_status === "accepted"`)
- [x] 4.2 Add DELETE permission check for deletion acceptance: `require_permission(PermissionName.DELETE_MANIFESTATION)` when target is a manifestation, or dynamically check permission at runtime for the appropriate entity type
- [x] 4.3 Implement entity deletion logic: import and call `delete_manifestation()` from `app/api/manifestations.py` or the equivalent item deletion logic from `app/api/items.py` based on which FRBR target is set
- [x] 4.4 Handle edge case where target entity is already deleted (return 404) and ensure the escalation status is not updated in this case
- [x] 4.5 Ensure deletion and status update are wrapped in a single database transaction for atomicity

## 5. Frontend Escalation Trigger Form

- [x] 5.1 Add `requestType` state to `EscalationTrigger` component in `frontend/components/escalation/escalation-trigger.tsx`, defaulting to `"correction"`
- [x] 5.2 Add a radio group or toggle selector at the top of the dialog form for request type selection ("Metadata Correction" / "Request Deletion") using i18n labels
- [x] 5.3 Implement conditional rendering: when `requestType === "deletion"`, hide field_name/current_value/suggested_value fields and show only a required "Reason for deletion" text area; when `"correction"`, show existing fields
- [x] 5.4 Clear form state when switching request types to prevent stale data leakage
- [x] 5.5 Update `handleSubmit` to include `request_type` in the mutation payload and pass `field_name: ""`, `suggested_value: ""` for deletion requests
- [x] 5.6 Update the existing status card to handle deletion-type escalations — show the note as the primary content when `field_name` is empty
- [x] 5.7 Update success toast message to differentiate between correction and deletion submissions

## 6. Frontend Admin Queue

- [x] 6.1 Add `request_type` badge to each pending request card in `EscalationQueue` component (`frontend/components/admin/escalation-queue.tsx`), using distinct styling for "Correction" vs "Deletion"
- [x] 6.2 Add `request_type` badge to each resolved request card in `ProcessedRequestsSection`
- [x] 6.3 Modify `ResolveActions` component to show "Accept & Delete" label for deletion-type requests and "Accept" for correction-type requests
- [x] 6.4 Add permission check using `useProfile()` hook: when request is deletion-type, disable "Accept & Delete" button if user lacks `delete:manifestation` or `delete:item` permission; show tooltip explaining the missing permission
- [x] 6.5 Handle deletion-type request display in the card content — for deletion requests, show the note prominently and hide the field_name/suggested_value arrow display
- [x] 6.6 Update `ResolvedStatusBadge` to also show request type badge alongside the resolved status

## 7. Frontend User View (My Escalations)

- [x] 7.1 Add `request_type` badge to each request card in `MyEscalations` component (`frontend/components/escalation/my-escalations.tsx`)
- [x] 7.2 For deletion-type requests, show the deletion reason (from `note`) prominently instead of the field_name → suggested_value arrow display
- [x] 7.3 Add distinct visual styling for deletion-type request cards (e.g., a warning border or icon) to differentiate from correction requests

## 8. Type Definitions

- [x] 8.1 Add `request_type: "correction" | "deletion"` field to the `EscalationRequest` TypeScript interface in `frontend/types/frbr.ts` (or wherever the type is defined)

## 9. i18n

- [x] 9.1 Add new English translation keys to `frontend/messages/en.json` under `HelpRequests`: `requestType`, `metadataCorrection`, `requestDeletion`, `acceptAndDelete`, `reasonForDeletion`, `reasonForDeletionPlaceholder`, `deletionRequestSubmitted`, `deletePermissionRequired`, `deletion`, `correction`, `entityRemovedSuccess`
- [x] 9.2 Add corresponding Polish translations to `frontend/messages/pl.json`
- [x] 9.3 Update `EscalationTrigger` to use the new i18n keys for request type selector, deletion reason label, and toast messages
- [x] 9.4 Update `EscalationQueue`/`ResolveActions` to use i18n keys for request type badges and "Accept & Delete" label
- [x] 9.5 Update `MyEscalations` to use i18n keys for request type badges

## 10. Testing and Validation

- [x] 10.1 Write backend test for deletion request creation (valid request with reason note)
- [x] 10.2 Write backend test for deletion request creation rejection (missing reason note)
- [x] 10.3 Write backend test for deletion request acceptance with DELETE permission (manifestation target)
- [x] 10.4 Write backend test for deletion request acceptance rejection without DELETE permission
- [x] 10.5 Write backend test for deletion request acceptance where target entity no longer exists
- [x] 10.6 Write backend test for correction request creation is unchanged (backward compatibility)
- [x] 10.7 Run full backend test suite: `pytest` to ensure no regressions
- [x] 10.8 Run frontend type check: `npx tsc --noEmit`
- [x] 10.9 Run frontend lint: `npm run lint`
- [x] 10.10 Manual smoke test: submit a deletion request as non-custodian user, verify admin sees "Accept & Delete" button, accept it as admin, verify entity is deleted
- [x] 10.11 Manual smoke test: submit a correction request, verify it works identically to before the change
- [x] 10.12 Verify i18n: all new labels appear correctly in both English and Polish locales

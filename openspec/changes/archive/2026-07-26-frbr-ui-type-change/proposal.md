## Why

Currently, when editing a Manifestation (or other FRBR entities) in the FRBR UI, users cannot change its fundamental type (e.g., from Book to Board Game, or Video Game to Movie) if it was incorrectly categorized. To fix an incorrect type, users have to delete and recreate the item or use backend workarounds. This change introduces the ability to change a manifestation type directly from the FRBR UI, and integrates this workflow with the User Requests system so normal users can suggest type changes that admins can approve.

## What Changes

- Add a "Type" dropdown or selection mechanism to the FRBR edit forms in the frontend.
- Backend API endpoints for updating the `type` of a Manifestation/Expression/Work.
- Integrate type changing with the User Requests system (creating a request to change the type of an existing entity).
- Support admin approval/rejection of these type change requests in the Custodian UI.

## Capabilities

### New Capabilities

- `frbr-ui-type-change`: Ability to change the type of a FRBR entity via the frontend UI, including routing the change through the User Request system.

### Modified Capabilities

- `frbr-ontology`: Allowing modification of the `type` attribute on existing FRBR entities via API.

## Impact

- Frontend: FRBR entity edit forms, User Request submission forms, Custodian approval queues.
- Backend: API update endpoints for FRBR entities, User Request handling logic.
- Database: Potential constraints if certain fields are only applicable to specific types (though currently handled via `meta` JSON).

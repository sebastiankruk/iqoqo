## 1. Backend API Implementation

- [x] 1.1 Implement `update_frbr_entity_type` service function to change the `type` of a Work/Expression/Manifestation/Item, including logic to adapt parent types upwards.
- [x] 1.2 Add backend route or integration logic for handling `CHANGE_TYPE` User Requests in the Custodian service.
- [x] 1.3 Write backend unit tests for type change mutability, upward type propagation, and User Request integration.

## 2. Frontend User Request Integration

- [x] 2.1 Update the User Request submission form or API client to support `CHANGE_TYPE` actions and the `new_type` payload.
- [x] 2.2 Update Custodian Request Approval UI to display the requested `new_type` cleanly to admins.
- [x] 2.3 Implement the Custodian action handler in the frontend to call the approval API for `CHANGE_TYPE` requests.

## 3. Frontend FRBR Editor Updates

- [x] 3.1 Update the Manifestation (and other FRBR entity) edit forms to include a `Select` dropdown for `type`.
- [x] 3.2 Add conditional logic so that selecting a new type hides invalid fields and shows fields for the new type, if applicable.
- [x] 3.3 Connect the form submission so that changing the type (for non-admins) dispatches a User Request instead of a direct PUT update.
- [x] 3.4 Write frontend component tests for the type selector and User Request submission workflow.

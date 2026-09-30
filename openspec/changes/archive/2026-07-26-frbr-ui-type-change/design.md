## Context

In the iqoqo application, items are structured using the FRBR (Functional Requirements for Bibliographic Records) ontology (Work -> Expression -> Manifestation -> Item). Currently, a Manifestation has a `type` field (e.g., Book, Movie, Video Game). Once created, this type is static. If a user creates a Manifestation with the wrong type (or imports it incorrectly), there's no way to change it from the UI.

This design introduces a mechanism to safely change the type of a Manifestation (and related FRBR entities) from the frontend, routing the change through the existing User Requests system for admin approval.

## Goals / Non-Goals

**Goals:**

- Allow users to select a new FRBR type for a Manifestation within the FRBR editor UI.
- Hook into the User Requests API so that type change suggestions from non-admin users go through the standard approval queue (Custodian UI).
- Allow admins (Custodians) to approve and directly apply type changes to the underlying database records.

**Non-Goals:**

- Automatically mapping or migrating type-specific metadata (if a user changes a "Book" to a "Board Game", any Book-specific metadata in the `meta` JSON blob will be left as-is, though we may want to clean it up in the future. For now, it is out of scope).

## Decisions

1. **Frontend Type Selector:** We will add a `Select` dropdown component (Shadcn UI) in the FRBR Edit Form, populated with the valid FRBR types enum.
2. **User Request Integration:** When a type change is submitted, instead of a direct `PUT` to the Manifestation API, it generates a User Request with the action `CHANGE_TYPE` and payload `{"new_type": "desired_type"}`.
3. **Backend API Update:** We need a new backend service function `update_frbr_entity_type` which can be invoked by the Custodian upon request approval.

## Risks / Trade-offs

- **Risk:** Type-specific metadata becomes invalid when the type changes.
  **Mitigation:** The frontend editor will simply present the fields for the new type once the type is approved. Since `meta` is a JSONB blob, retaining old unused keys is harmless at the database level, but we should ensure the frontend ignores irrelevant keys for the new type.
- **Risk:** Parent Work type might mismatch with Manifestation type.
  **Mitigation:** When a Manifestation type is changed, the backend service will automatically adapt the parent Work and Expression upwards to ensure the new type is correctly covered, ensuring ontological consistency across the hierarchy.

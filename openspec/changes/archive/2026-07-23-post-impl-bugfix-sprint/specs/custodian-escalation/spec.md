---
type: Concept
title: spec
timestamp: 2026-07-23T00:47:00Z
---

## MODIFIED Requirements

### Requirement: Escalation Request Submission

The system SHALL allow any authenticated user with the `escalate:request` permission to submit an escalation request targeting a specific FRBR entity (Work, Expression, Manifestation, or Item). The request MUST capture the target entity level, target entity ID, the field name the user believes is incorrect, an optional current value, a required suggested value, and an optional free-text justification note. The `escalate:request` permission MUST be assigned to the default `user` role during database initialization.

#### Scenario: Authenticated user submits a valid escalation request

- **WHEN** an authenticated user with `escalate:request` permission submits a POST to `/api/escalations/<level>/<target_id>` with `field_name`, `suggested_value`, and optional `current_value` and `note`
- **THEN** the system SHALL create an `EscalationRequest` record with status `pending`, return HTTP 201 with the created request data, and associate it with the requesting user.

#### Scenario: Default role includes escalation permission

- **WHEN** a new user registers with the system
- **THEN** the user SHALL automatically have the `escalate:request` permission via the default `user` role, enabling them to submit escalation requests without manual permission grants.

### Requirement: Escalation Request Resolution

The system SHALL allow users with `escalate:resolve` permission to resolve pending escalation requests by changing their status to `accepted`, `rejected`, or `duplicate`. A resolution note MAY be provided. The `escalate:resolve` permission MUST be assigned to the `custodian` and `admin` roles during database initialization.

#### Scenario: Custodian accepts an escalation request

- **WHEN** a user with `escalate:resolve` permission sends a PATCH to `/api/escalations/<escalation_id>` with `status: "accepted"` and optional `resolution_note`
- **THEN** the system SHALL update the request status to `accepted`, record the `resolved_by` user ID, set `resolved_at` timestamp, store the `resolution_note`, and return the updated request.

#### Scenario: Custodian and admin roles include resolve permission

- **WHEN** a user is assigned the `custodian` or `admin` role
- **THEN** the user SHALL automatically have the `escalate:resolve` permission via their role, enabling them to view and resolve escalation requests.

### Requirement: Escalation UI Trigger Visibility

The system SHALL render a contextual "Ask Custodians for Help" escalation trigger on item detail and manifestation detail pages. This trigger MUST only be visible to authenticated users who do NOT have `write:metadata` permission. Users who already have custodian/admin metadata write access SHALL NOT see the escalation trigger. The "Edit FRBR" button SHALL only be rendered for users with `write:metadata` permission, NOT for users with only `read:metadata` permission.

#### Scenario: Non-custodian user views an item detail page

- **WHEN** an authenticated user without `write:metadata` permission views an item detail page
- **THEN** the system SHALL render an "Ask Custodians for Help" trigger button within the item actions panel AND SHALL NOT render the "Edit FRBR" button.

#### Scenario: Custodian views an item detail page

- **WHEN** an authenticated user with `write:metadata` permission views an item detail page
- **THEN** the system SHALL render the "Edit FRBR" button AND SHALL NOT render the escalation trigger.

#### Scenario: Regular user does not see "Edit FRBR" button

- **WHEN** an authenticated user with `read:metadata` but without `write:metadata` permission views an item detail page
- **THEN** the system SHALL NOT render the "Edit FRBR" button, since the user cannot use the FRBR metadata editor.

### Requirement: FRBR Entity Search Access Control

The system SHALL allow any user with `read:metadata` permission to search for FRBR entities via the search endpoint. Access MUST NOT be restricted to the `admin` role exclusively — custodians with appropriate permissions SHALL have equal access.

#### Scenario: Custodian searches for FRBR entities

- **WHEN** a user with the `custodian` role and `read:metadata` permission sends a GET to `/v1/admin/frbr/search?q=<query>`
- **THEN** the system SHALL return matching FRBR entities, NOT return HTTP 403 "Admin privileges required".

#### Scenario: User without read:metadata attempts FRBR search

- **WHEN** an authenticated user without `read:metadata` permission sends a GET to `/v1/admin/frbr/search`
- **THEN** the system SHALL return HTTP 403 with the `missing_permission` field indicating `read:metadata`.

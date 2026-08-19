# custodian-escalation-enrichment Specification

## Purpose

Define how the custodian escalation detail API returns target entity details (title, type, ID, and current state) so the review screen can display entity context before approval.

## Requirements

### Requirement: Custodian escalation response includes target entity details

The custodian escalation detail API endpoint SHALL return target entity details (title, type, ID, and current state) in the response payload, enabling the review screen to display entity context before approval.

#### Scenario: Fetching escalation detail with enriched entity data

- **WHEN** a custodian fetches an escalation request for review
- **THEN** the API response SHALL include a `target_entity` object with `title`, `type`, `id`, and `current_state` fields
- **AND** the `title` field SHALL contain the human-readable entity name
- **AND** the `type` field SHALL indicate the FRBR level (Work, Expression, Manifestation, or Item)

#### Scenario: Escalation review screen displays entity details

- **WHEN** a custodian views the escalation review screen
- **THEN** the target entity's title, type, and ID SHALL be clearly displayed
- **AND** the custodian SHALL be able to verify the entity before approving the type change

#### Scenario: Preventing blind IDOR approval

- **WHEN** a malicious payload attempts to approve a type change via `_handle_type_change_acceptance` with a different entity ID
- **THEN** the displayed entity details SHALL reveal the mismatch to the reviewing custodian
- **AND** the system SHALL validate that the entity ID in the approval matches the escalation request

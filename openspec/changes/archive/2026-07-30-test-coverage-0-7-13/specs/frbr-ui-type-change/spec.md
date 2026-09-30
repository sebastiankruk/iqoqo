## MODIFIED Requirements

### Requirement: Custodian Type Change Approval
The system SHALL allow Custodians (admins) to approve and apply type changes via the Custodian UI, and this workflow SHALL be verified by automated End-to-End tests.

#### Scenario: Approving Type Change

- **WHEN** a Custodian approves a `CHANGE_TYPE` User Request
- **THEN** the system updates the underlying FRBR entity's `type` attribute and resolves the request
- **AND** Playwright E2E tests validate that the parent Work and Expression records correctly adapt their types to maintain hierarchy consistency.

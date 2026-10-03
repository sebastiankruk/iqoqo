## ADDED Requirements

### Requirement: Expression kind settable through UI and escalation

A concert Expression's `kind` (e.g. `live_performance`) SHALL be settable and correctable through the FRBR editor UI by admins, and requestable through the escalation system by non-admin users. The concert identification SHALL NOT depend solely on ingestion-time auto-detection — manual correction SHALL be available through the same operational paths used for other expression metadata.

#### Scenario: Admin corrects misclassified expression kind via UI

- **WHEN** an admin discovers an Expression that should be a concert (or should no longer be a concert)
- **THEN** the admin SHALL be able to open the FRBR editor, change the `kind` dropdown, and save — without needing to delete and re-ingest the record

#### Scenario: Non-admin requests kind correction via escalation

- **WHEN** a non-admin user discovers an Expression with an incorrect `kind` value
- **THEN** the user SHALL be able to submit a correction request through the escalation system, and a Custodian SHALL be able to approve and apply the change

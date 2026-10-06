## MODIFIED Requirements

### Requirement: Specification Purpose Section

The `deletion-request-resolution` spec Purpose section SHALL be updated from the placeholder `TBD - created by archiving change add-deletion-request-support. Update Purpose after archive.` to a concise description of what this specification governs.

The Purpose SHALL read:

```text
Defines the custodial resolution workflow for deletion-type escalation requests: request type visibility in the admin queue, permission-gated "Accept & Delete" action requiring entity-specific DELETE permissions, entity deletion execution on acceptance, rejection and duplicate handling without DELETE permission requirements, and deletion request display in the user's "My Help Requests" view.
```

#### Scenario: Purpose section is populated after archive finalization

- **WHEN** the specification is read after this change is archived
- **THEN** the `## Purpose` section SHALL contain the description above and SHALL NOT contain the string `TBD` or the text `created by archiving change`.

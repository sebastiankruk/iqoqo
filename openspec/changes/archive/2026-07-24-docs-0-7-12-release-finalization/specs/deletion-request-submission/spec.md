## MODIFIED Requirements

### Requirement: Specification Purpose Section

The `deletion-request-submission` spec Purpose section SHALL be updated from the placeholder `TBD - created by archiving change add-deletion-request-support. Update Purpose after archive.` to a concise description of what this specification governs.

The Purpose SHALL read:

```text
Defines the user-facing submission flow for deletion requests within the escalation system: request type selection in the escalation trigger dialog, form adaptation between correction and deletion modes, API input validation for the `request_type` field, and i18n coverage for all deletion-related user labels.
```

#### Scenario: Purpose section is populated after archive finalization

- **WHEN** the specification is read after this change is archived
- **THEN** the `## Purpose` section SHALL contain the description above and SHALL NOT contain the string `TBD` or the text `created by archiving change`.

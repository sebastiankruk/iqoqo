## Context

See `proposal.md` for user requirements. Automatic gap-filling (C57) handles simple gaps, but custodians need human curation when providers return conflicting attributes (different covers, varied author spellings, disparate publishers).

## Goals / Non-Goals

**Goals:**
- Present candidate attributes from distinct providers in a side-by-side comparison matrix.
- Allow single-click selection per field grouped by FRBR entity tier.
- Atomically commit the selected attributes and update provenance.
- Log custodian decisions to `EntityAuditLog`.

**Non-Goals:**
- Merging two separate catalog manifestations (handled by C40 / duplicate detection).
- Automatic AI arbitration without human custodian confirmation.

## Decisions

- **Decision 1: On-demand provider re-fetch vs persisted fragments.**
  - *Rationale:* Manifestations store `raw_payload` from ingest. If raw provider fragments are missing or stale, provide an on-demand "Refetch Providers" trigger rather than bloating primary database tables with full multi-provider responses indefinitely.
  - *Alternatives considered:* New relational table storing raw responses for all providers forever (excessive storage overhead).
- **Decision 2: Transactional tier update with row-level locks.**
  - *Rationale:* Updating Work, Expression, and Manifestation concurrently requires acquiring row-level locks in deterministic ascending ID order to prevent deadlocks with background reconciliation tasks.

## Risks / Trade-offs

- **[Risk]** Complex UI matrix on small mobile screens.
  - *Mitigation:* Stack provider candidate cards vertically on mobile viewports with radio button selection per field.

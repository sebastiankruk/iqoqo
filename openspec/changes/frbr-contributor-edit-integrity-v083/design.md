## Context

See `proposal.md` for bug descriptions. Inconsistent serialization of Work authors (`list` vs `str` vs JSON-stringified `str`) crashes the manifestation view and causes single-character rendering bugs.

## Goals / Non-Goals

**Goals:**
- Guarantee `authors` is always returned as a list of strings (`list[str]`) from all manifestation and work endpoints.
- Synchronize relational `WorkContribution` rows with `work.meta["authors"]` on update.
- Provide a safe data repair script for existing corrupted rows.
- Fix CSS alignment of the FRBR level selector in `frbr-editor.tsx`.

**Non-Goals:**
- Redesigning the entire FRBR editor modal dialogs.
- Changing the database schema for contributions or works.

## Decisions

- **Decision 1: Centralized `normalize_authors_list` helper.**
  - *Rationale:* Rather than trusting raw JSONB values in `work.meta`, centralize normalization so strings, JSON lists, and corrupted unicode escapes are reliably resolved to clean Python lists.
- **Decision 2: Realign level selector with tabs header pattern.**
  - *Rationale:* Integrate the level selector with full container width and standard left alignment instead of a detached floating card.

## Risks / Trade-offs

- **[Risk]** Data repair script modifying active catalog entries.
  - *Mitigation:* Require explicit dry-run mode reporting affected row count before applying database updates.

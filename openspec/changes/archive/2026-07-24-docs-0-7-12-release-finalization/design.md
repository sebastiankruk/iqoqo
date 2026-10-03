## Context

The 0.7.12 release is feature-complete but has three documentation gaps that block the pre-release checklist (per `docs/RELEASE_PROCESS.md`):

1. **CHANGELOG.md**: The `## [0.7.12] - TBD` header needs a date, and the deletion-request feature — implemented across commits `35d96ab` and `bbab069`, with archived OpenSpec change `add-deletion-request-support`, merged PRs, database migration, and full frontend/backend code — has zero changelog entries.
2. **OpenSpec specs**: `deletion-request-submission/spec.md` and `deletion-request-resolution/spec.md` were archived with `TBD` Purpose sections from the auto-archive template. Both contain complete, valid requirement/scenario content but lack the one-line purpose statement.
3. **Stale active change**: `test-suite-hardening-0-7-12` (125 tasks, all unchecked) is the only active change in `openspec/changes/`. It was never implemented for 0.7.12 and should be archived to accurately reflect release state.

This is a pure documentation change — no code, no API, no schema modifications.

## Goals / Non-Goals

**Goals:**

- Finalize the 0.7.12 CHANGELOG date header
- Add comprehensive deletion-request entries to CHANGELOG following existing formatting conventions
- Fill in TBD Purpose sections for both deletion-request OpenSpec specs
- Archive the stale `test-suite-hardening-0-7-12` change
- Ensure all changes pass `markdownlint-cli2`

**Non-Goals:**

- Writing new code or tests
- Modifying existing requirement/scenario content in any spec
- Updating `docs/ARCHITECTURE.md`, `docs/CONTRIBUTING.md`, or `docs/INSTALL.md` (no new capabilities require their modification)
- Creating new OpenSpec specs beyond what's listed in the proposal
- Implementing the test-suite-hardening tasks

## Decisions

### D1: CHANGELOG entry placement: Added vs Changed

**Decision**: Deletion request entries split across both `Added` and `Changed` sections, matching the pattern used for the existing escalation entries (lines 10–28).

**Rationale**: The feature introduces genuinely new capabilities (new `request_type` column, new form selector, new `RequestTypeBadge` component) and modifies existing behavior (API validation, resolve endpoint, admin queue accept button). Following Keep a Changelog and the existing convention prevents inconsistency.

**Alternatives considered**: Placing everything under `Added` would overstate the novelty (much of the infrastructure already existed from the escalation system). Placing everything under `Changed` would undersell the genuinely new deletion-specific UI components and DB schema column.

### D2: CHANGELOG entry granularity

**Decision**: One entry per logical feature area (schema + API validation, form UI, admin queue UI, user view UI, i18n), each with a bold lead-in sentence and 1–2 explanatory sentences.

**Rationale**: Matches the existing 0.7.12 entries for the escalation queue (lines 10–14) and User Requests UX rename (lines 16–29). Avoids both over-condensed single-line entries and overly verbose paragraphs.

**Alternatives considered**: Bullet-point sub-items under a single "Deletion Requests" entry — rejected because existing entries don't use nested lists and consistency is preferred.

### D3: OpenSpec spec Purpose section content

**Decision**: Write single-sentence Purpose sections that describe what each spec governs: submission flow for `deletion-request-submission` (form UX, API input validation, request creation) and resolution flow for `deletion-request-resolution` (admin queue UX, permission gating, entity deletion).

**Rationale**: Minimal change — the existing specs already contain complete, valid requirements and scenarios. The Purpose section just needs a one-sentence summary. No requirement or scenario content is modified.

### D4: Archiving test-suite-hardening

**Decision**: Run `openspec archive test-suite-hardening-0-7-12 --yes` which moves the change directory to `archive/` and syncs any delta specs.

**Rationale**: All 125 tasks are unchecked and the user has decided not to implement them for 0.7.12. The change has no delta specs to sync (it created zero spec files — the `specs/` directory in the change is empty), so archiving is a safe no-op on main specs.

## Risks / Trade-offs

- **Risk**: CHANGELOG format inconsistency with existing entries → **Mitigation**: Follow exact pattern from existing 0.7.12 entries (bold lead-in, colon, explanatory sentence). Run `markdownlint-cli2` after editing.
- **Risk**: Deletion request entries duplicate or conflict with existing escalations entries → **Mitigation**: Only add entries for deletion-specific features. Existing entries cover general escalation queue UI, User Requests rename, shared utilities — deletion is distinct.
- **Risk**: Archiving test-suite-hardening loses task tracking if someone wants to resume later → **Mitigation**: Archiving moves the change to `archive/`, not deletion. All proposal/design/tasks content is preserved and recoverable. If needed later, a new change can be created referencing the archived design.

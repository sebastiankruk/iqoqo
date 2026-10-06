## Why

The 0.7.12 release branch (`release/0.7.12`) contains several documentation gaps that block release finalization. The CHANGELOG.md date header is still `TBD`, the deletion-request feature (commits `35d96ab`, `bbab069`) has fully implemented code, archived OpenSpec specs, and merged PRs but zero CHANGELOG entries, the `deletion-request-submission` and `deletion-request-resolution` OpenSpec specs were archived with `TBD` Purpose sections, and the stale `test-suite-hardening-0-7-12` change (125 unchecked tasks, blocked by user decision) remains active in `openspec/changes/`. Without resolving these, the release cannot pass the pre-release checklist and the deletion request feature is invisible to users and maintainers reading the changelog.

## What Changes

- **CHANGELOG.md**: Finalize the `## [0.7.12] - TBD` header to `## [0.7.12] - 2026-07-24` and add complete `Added` and `Changed` entries documenting the deletion request feature across all tiers (database schema, API validation, resolve endpoint permission gating, frontend form, admin queue UI, user view badges, i18n coverage).
- **OpenSpec specs**: Fill in the `Purpose` section for `deletion-request-submission/spec.md` and `deletion-request-resolution/spec.md`, replacing the `TBD - created by archiving change...` placeholder with concise descriptions of what each spec governs.
- **OpenSpec changes**: Archive the `test-suite-hardening-0-7-12` change from `openspec/changes/` to `archive/` so the active change list accurately reflects the release state. All 125 tasks were never implemented for 0.7.12 per user decision.
- **CHANGELOG lint compliance**: Verify all entries follow Keep a Changelog format (ATX headings, `bash` code block tags, no Setext-style headings) and pass `markdownlint-cli2`.

## Capabilities

### New Capabilities

- `changelog-deletion-requests`: CHANGELOG.md entries for the 0.7.12 deletion request feature covering database schema (`request_type` column on `EscalationRequest`), API validation (conditional field requirements per request type), resolve endpoint permission gating (`delete:manifestation` / `delete:item`), frontend request type selector in escalation trigger dialog, "Accept & Delete" button in admin queue, `RequestTypeBadge` component in both admin queue and user view, and i18n coverage for all deletion-related labels.

### Modified Capabilities

- `deletion-request-submission`: Fill in the `Purpose` section that currently reads `TBD - created by archiving change add-deletion-request-support. Update Purpose after archive.`
- `deletion-request-resolution`: Fill in the `Purpose` section that currently reads `TBD - created by archiving change add-deletion-request-support. Update Purpose after archive.`

## Impact

- **docs/CHANGELOG.md**: ~20-25 new lines added under 0.7.12 `Added` and `Changed` sections, plus date header fix
- **openspec/specs/deletion-request-submission/spec.md**: Purpose section filled in (1 line change)
- **openspec/specs/deletion-request-resolution/spec.md**: Purpose section filled in (1 line change)
- **openspec/changes/test-suite-hardening-0-7-12/**: Archived to `archive/` via `openspec archive`
- **No code changes, no API changes, no DB migrations** — purely documentation and specification metadata

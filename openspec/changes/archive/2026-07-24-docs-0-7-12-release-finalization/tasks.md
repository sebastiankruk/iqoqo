## 1. CHANGELOG — Date Header Finalization

- [x] 1.1 Update `docs/CHANGELOG.md` line 8 from `## [0.7.12] - TBD` to `## [0.7.12] - 2026-07-24`

## 2. CHANGELOG — Deletion Request Added Entries

- [x] 2.1 Add `- **Deletion Request Type**:` entry under `### Added` — documents new `request_type` column on `EscalationRequest` model (default `"correction"`, supports `"correction"` and `"deletion"`), with Alembic migration
- [x] 2.2 Add `- **Deletion Request Form**:` entry under `### Added` — documents request type selector (radio group) in escalation trigger dialog toggling between "Metadata Correction" and "Request Deletion" modes; form state clears on type switch
- [x] 2.3 Add `- **Accept & Delete Resolution**:` entry under `### Added` — documents that accepting a deletion-type request triggers actual entity deletion; requires `delete:manifestation` or `delete:item` permission in addition to `escalate:resolve`
- [x] 2.4 Add `- **Deletion Request UI Badges**:` entry under `### Added` — documents `RequestTypeBadge` component on admin queue and "My Help Requests" cards with distinct "Deletion" (destructive/warning) vs "Correction" (neutral) styling

## 3. CHANGELOG — Deletion Request Changed Entries

- [x] 3.1 Add `- **API Validation for Deletion Requests**:` entry under `### Changed` — documents `_validate_escalation_input()` accepting optional `request_type`; when `"deletion"`, `field_name`/`suggested_value` become optional but `note` becomes required (max 2048 chars); invalid types rejected with 400
- [x] 3.2 Add `- **Resolve Endpoint Permission Gating**:` entry under `### Changed` — documents `PATCH /api/escalations/<id>` checking entity-specific DELETE permissions (`delete:manifestation` or `delete:item`) when accepting deletion-type requests; rejection/duplicate actions exempt from DELETE checks; entity deletion and status update wrapped in single DB transaction
- [x] 3.3 Add `- **Admin Queue "Accept & Delete" Button**:` entry under `### Changed` — documents "Accept" button relabeled to "Accept & Delete" for deletion-type requests, disabled with permission tooltip when resolver lacks required DELETE permission
- [x] 3.4 Add `- **Deletion Request i18n Coverage**:` entry under `### Changed` — documents new `HelpRequests` namespace translation keys for "Request Deletion", "Accept & Delete", "Reason for deletion", "Deletion request submitted", and related labels in both `en.json` and `pl.json`

## 4. CHANGELOG — Lint Verification

- [x] 4.1 Run `make lint-docs` (or `npx markdownlint-cli2 docs/CHANGELOG.md`) and verify zero errors and zero warnings
- [x] 4.2 Visually verify all entries follow existing 0.7.12 formatting convention: bold lead-in (`- **Label**:`), followed by 1–2 explanatory sentences, proper ATX headings, no Setext-style underlines

## 5. OpenSpec Specs — Purpose Section Population

- [x] 5.1 Update `openspec/specs/deletion-request-submission/spec.md` Purpose section to: `Defines the user-facing submission flow for deletion requests within the escalation system: request type selection in the escalation trigger dialog, form adaptation between correction and deletion modes, API input validation for the \`request_type\` field, and i18n coverage for all deletion-related user labels.`
- [x] 5.2 Update `openspec/specs/deletion-request-resolution/spec.md` Purpose section to: `Defines the custodial resolution workflow for deletion-type escalation requests: request type visibility in the admin queue, permission-gated "Accept & Delete" action requiring entity-specific DELETE permissions, entity deletion execution on acceptance, rejection and duplicate handling without DELETE permission requirements, and deletion request display in the user's "My Help Requests" view.`
- [x] 5.3 Verify both files no longer contain the string `TBD` or `created by archiving change`

## 6. OpenSpec Changes — Archive Stale Change

- [x] 6.1 ~~Run `openspec archive test-suite-hardening-0-7-12 --yes`~~ **SKIPPED**: User requested `test-suite-hardening-0-7-12` be implemented, not archived. See test-suite-hardening-0-7-12 change.
- [x] 6.2 `openspec list` will show both active changes (expected per user decision to implement both)

## 7. Final Validation

- [x] 7.1 Run `openspec validate docs-0-7-12-release-finalization` to verify all artifacts are valid
- [x] 7.2 Review the full CHANGELOG 0.7.12 section for completeness — confirm all major features from the release branch are documented
- [x] 7.3 Verify `pyproject.toml` version (`0.7.12`) and `frontend/package.json` version (`0.7.12`) are correct (no changes needed, already set)

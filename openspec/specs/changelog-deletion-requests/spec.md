# changelog-deletion-requests Specification

## Purpose

Defines the requirements for documenting the deletion request feature in the project CHANGELOG under the 0.7.12 release section, following Keep a Changelog format with ATX-style headings, bold lead-in descriptions, and proper lint compliance.

## Requirements

### Requirement: CHANGELOG documents deletion request feature for 0.7.12

The `docs/CHANGELOG.md` file SHALL include comprehensive entries for the deletion request feature under the `## [0.7.12]` section. Entries SHALL follow Keep a Changelog format with ATX-style headings, bold lead-in descriptions followed by explanatory sentences, and SHALL be placed in the `### Added` and `### Changed` subsections. The date header SHALL be finalized from `TBD` to the actual release date (`2026-07-24`).

#### Scenario: CHANGELOG 0.7.12 date is finalized

- **WHEN** the release documentation is finalized for version 0.7.12
- **THEN** the header SHALL read `## [0.7.12] - 2026-07-24` (not `TBD`).

#### Scenario: Added entries document deletion request capabilities

- **WHEN** a reader views the `### Added` subsection under 0.7.12 in CHANGELOG.md
- **THEN** they SHALL find entries for: the `request_type` column on `EscalationRequest`, the deletion request form with request type selector, the "Accept & Delete" resolution flow with entity deletion, and the `RequestTypeBadge` component for admin queue and user view. Each entry SHALL use a bold lead-in (e.g., `- **Deletion Request Type**:`) followed by 1–2 explanatory sentences.

#### Scenario: Changed entries document modified behavior for deletion requests

- **WHEN** a reader views the `### Changed` subsection under 0.7.12 in CHANGELOG.md
- **THEN** they SHALL find entries for: API validation conditional field requirements per request type, resolve endpoint permission gating for deletion acceptance, admin queue "Accept" button relabeled to "Accept & Delete" with permission tooltip, and i18n coverage for deletion-related labels. Each entry SHALL use a bold lead-in followed by 1–2 explanatory sentences.

#### Scenario: CHANGELOG passes markdownlint

- **WHEN** `markdownlint-cli2` is run against `docs/CHANGELOG.md`
- **THEN** the file SHALL pass with zero errors and zero warnings.

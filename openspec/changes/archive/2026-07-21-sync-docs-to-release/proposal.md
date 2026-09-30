---
type: Concept
title: proposal
timestamp: 2026-07-22T10:18:49Z
---

## Why

The v0.7.11 release introduced significant architectural changes — format normalization, cross-FRBR filtering, virtual-to-physical item transitions, unauthorized route redirects, publisher facet fixes, and APScheduler hardening — but the project's canonical documentation (`docs/ARCHITECTURE.md`, `docs/RELEASE_PROCESS.md`, `docs/CONTRIBUTING.md`, `docs/INSTALL.md`) has not been updated to reflect them. The roadmap explicitly flags this as `[ ] is documentation up to date? #important` under v0.7.11. Closing this gap before the v0.7.11 release is critical for contributor onboarding and long-term maintainability.

## What Changes

- **ARCHITECTURE.md**: Add sections for UserWorkIntent (virtual wishlist items), @require_physical_item decorator, format normalization pipeline, make fix-physical-kinds CLI, faceted navigation and cross-FRBR filtering, @optional_auth decorator, ItemCustodyEvent/EntityAuditLog models, publisher metadata extraction, APScheduler context fix, and shared collection UI architecture.
- **RELEASE_PROCESS.md**: Add OpenSpec workflow integration, multi-agent tribal matrix review step, mempalace mine synchronization step, and a pre-release checklist.
- **CONTRIBUTING.md**: Add OpenSpec workflow overview, new Makefile targets (fix-physical-kinds, status, db-stamp, db-upgrade), format normalization conventions, and cross-FRBR filtering testing guidelines.
- **INSTALL.md**: Add make fix-physical-kinds command, `shared/format_mappings.yaml` configuration, and version requirement updates.
- **item_statuses.md**: Verify and update to include `unread` status if missing.
- **CHANGELOG.md**: Finalize the 0.7.11 section with the correct release date and any missing entries.

## Capabilities

### New Capabilities

- `docs-coverage-architecture`: Comprehensive update to docs/ARCHITECTURE.md covering all new v0.7.10-v0.7.11 architectural patterns (virtual items, format normalization, faceted navigation, custody/audit logs, decorators, publisher extraction, scheduler hardening, shared collections).
- `docs-coverage-release-process`: Update docs/RELEASE_PROCESS.md to document the OpenSpec workflow, multi-agent review, and mempalace synchronization as part of the release process.
- `docs-coverage-contributing`: Update docs/CONTRIBUTING.md with OpenSpec workflow overview, new Makefile targets, format normalization conventions, and cross-FRBR filtering testing guidelines.
- `docs-coverage-install`: Update docs/INSTALL.md with format mappings setup, fix-physical-kinds command, and version requirement clarifications.

### Modified Capabilities

<!-- No existing specs change -- this is a pure documentation update. -->

## Impact

- **Files modified**: `docs/ARCHITECTURE.md`, `docs/RELEASE_PROCESS.md`, `docs/CONTRIBUTING.md`, `docs/INSTALL.md`, `docs/item_statuses.md`, `docs/CHANGELOG.md`
- **Files reviewed**: All 17 `openspec/specs/` directories, all 121 `ai-memory/2026/07/` session files, roadmap, review notes
- **No API changes, no database changes, no dependency changes**
- **Risk**: Low — pure documentation, no code or deployment impact

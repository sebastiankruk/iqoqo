---
type: Concept
title: tasks
timestamp: 2026-07-22T10:18:49Z
---

## 1. Update ARCHITECTURE.md

- [x] 1.1 Add "Virtual Wishlist Items (UserWorkIntent)" sub-section under the Item section documenting negative-ID virtual items, UserWorkIntent model, and virtual-to-physical transition on tag mutation
- [x] 1.2 Add "FRBR Boundary Enforcement (require_physical_item)" sub-section under API Architecture documenting the @require_physical_item decorator, 400 Bad Request response format, and example usage
- [x] 1.3 Add "Format Normalization" sub-section under Operations & Maintenance documenting format_normalizer.py, format_mappings.yaml, unknown format placeholders, and the fix-physical-kinds CLI workflow
- [x] 1.4 Add "Faceted Navigation & Cross-FRBR Filtering" section documenting DataManager.get_faceted_stats, FRBR-level count distinctions, multi-select AND/OR logic, @optional_auth on stats/facets, and publisher extraction via func.coalesce
- [x] 1.5 Add "Item Custody & Entity Audit Logs" sub-section in the Database Schema area documenting ItemCustodyEvent (append-only Item-tier possession) and EntityAuditLog (Work/Expression/Manifestation curation) models and their CIDOC CRM rationale
- [x] 1.6 Update Authentication section to document the @optional_auth decorator pattern for hybrid public/authenticated endpoints
- [x] 1.7 Update Operations & Maintenance to document the APScheduler application context fix for cover cleanup watchdog jobs
- [x] 1.8 Update Social & Privacy Architecture section to document clean shared collection UI patterns (simplified navbar, hidden action buttons, token-based access)

## 2. Update RELEASE_PROCESS.md

- [x] 2.1 Add OpenSpec workflow section documenting the `openspec new change`, apply, and archive commands as part of the development cycle
- [x] 2.2 Add "Multi-Agent Tribal Matrix Review" step documenting the automated multi-persona PR review process (Ontologist, Security, DevOps, QA, TechComm, Code Quality)
- [x] 2.3 Add "Memory Graph Synchronization" step documenting `mempalace mine .context/notes/` after release merge
- [x] 2.4 Add "Pre-Release Checklist" covering: roadmap task verification, CHANGELOG finalization, version bumps, documentation currency check, and openspec spec synchronization

## 3. Update CONTRIBUTING.md

- [x] 3.1 Add OpenSpec workflow section in the Development Workflow area referencing openspec-propose and openspec-apply-change skills
- [x] 3.2 Add `make fix-physical-kinds`, `make status`, `make db-stamp`, and `make db-upgrade` to the Development Commands Quick Reference
- [x] 3.3 Add "Format Normalization Conventions" sub-section in Database Guidelines documenting format_mappings.yaml as git-tracked SSoT and the normalizer pipeline
- [x] 3.4 Add cross-FRBR filtering testing guidance in the Writing Tests section referencing test_api_status_filters.py patterns

## 4. Update INSTALL.md

- [x] 4.1 Add `shared/format_mappings.yaml` documentation in the configuration/environment section with commented mapping examples
- [x] 4.2 Add `make fix-physical-kinds` command reference with --audit, --interactive, --apply, and --dry-run modes
- [x] 4.3 Verify and update Prerequisites section to reflect Python 3.14+ and Node.js 20+ requirements

## 5. Verify and Finalize Remaining Docs

- [x] 5.1 Audit docs/item_statuses.md against app/db/core.py ITEM_STATUSES and update if any values are missing (verify unread status is present)
- [x] 5.2 Finalize docs/CHANGELOG.md 0.7.11 section date from TBD to the actual release date
- [x] 5.3 Run `make lint-docs` to validate all Markdown formatting compliance (ATX headings, bash code blocks, no Setext-style)
- [x] 5.4 Run `mempalace mine .context/notes/ --mode convos --wing iqoqo` to persist documentation updates to memory graph
- [x] 5.5 Check off `[ ] is documentation up to date? #important` in `.context/notes/🚧 iqoqo roadmap.md`

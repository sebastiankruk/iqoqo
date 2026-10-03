---
type: Concept
title: design
timestamp: 2026-07-22T10:18:49Z
---

## Context

The iqoqo project maintains five core documentation files in `docs/` totaling 3,313 lines across 16 markdown files. Since v0.7.6 (2026-07-06), the codebase has undergone rapid architectural evolution through releases 0.7.6→0.7.11, introducing format normalization, cross-FRBR faceted filtering, virtual-to-physical item transitions, authentication redirects, publisher facet fixes, APScheduler hardening, and shared collection UI improvements. These changes are captured in CHANGELOG.md and 121 session memory files but not propagated to the canonical architecture, release process, contributing, or installation guides.

The roadmap under v0.7.11 explicitly lists `[ ] is documentation up to date? #important` as an open task.

## Goals / Non-Goals

**Goals:**

- Update `docs/ARCHITECTURE.md` with all new architectural patterns from v0.7.10 and v0.7.11
- Update `docs/RELEASE_PROCESS.md` to reflect OpenSpec and multi-agent workflows
- Update `docs/CONTRIBUTING.md` with OpenSpec workflow, new CLI tools, and testing conventions
- Update `docs/INSTALL.md` with format mappings and CLI tool references
- Verify `docs/item_statuses.md` reflects current canonical status values
- Finalize `docs/CHANGELOG.md` v0.7.11 release date

**Non-Goals:**

- Rewriting or restructuring existing documentation content
- Creating new documentation files
- Updating OpenSpec spec files (these are code-level specs, not user-facing docs)
- Modifying inline code comments or TSDoc/API docstrings
- Translating documentation to other languages

## Decisions

- **ARCHITECTURE.md additions follow existing section structure**: New sub-sections will be added under existing major sections (e.g., "Virtual Wishlist Items" under the Item section, "Faceted Navigation" as a new section after Social Architecture). This maintains continuity.
- **Format normalizer gets its own section**: The `app/core/format_normalizer.py` + `shared/format_mappings.yaml` + `make fix-physical-kinds` toolchain is novel enough to warrant a dedicated "Format Normalization" subsection under Operations & Maintenance.
- **RELEASE_PROCESS.md rewrite to include AI-assisted steps**: Since OpenSpec and tribal matrix review are now integral to all releases, the release process document should document the full workflow rather than just the mechanical steps.
- **CONTRIBUTING.md receives minimal updates**: Only add OpenSpec workflow pointer, new `make` commands, and format normalization conventions. The existing structure is sound.
- **INSTALL.md receives targeted additions**: Add `make fix-physical-kinds` and `shared/format_mappings.yaml` references in existing configuration sections.
- **CHANGELOG.md date**: Set to the release date (TBD → actual date when release is finalized).
- **item_statuses.md**: Audit against `app/db/core.py` ITEM_STATUSES and update if stale. Based on review, it appears current — only verification needed.

## Risks / Trade-offs

- **Documentation drift risk**: If documentation is updated before all v0.7.11 changes have landed, it may become stale again. → Mitigation: Only document features already merged to `release/0.7.11`.
- **Overscope risk**: ARCHITECTURE.md is already 725 lines. Adding 10+ new sections could make it unwieldy. → Mitigation: Keep new sections concise, use cross-references to existing sections where possible.
- **Missing context risk**: Some implementation details may only be clear to the original implementers. → Mitigation: Cross-reference the 17 openspec/specs directories which contain formal specifications for most new features.

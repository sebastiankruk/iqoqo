# ai-cover-cli-docs Specification

## Purpose
TBD - created by archiving change release-0713-ux-docs-polish. Update Purpose after archive.
## Requirements
### Requirement: AI Cover Generation Documentation

The system SHALL include comprehensive documentation for the AI Cover generation CLI tools, specifically `scripts/generate_ai_covers.py`. The documentation MUST detail all available operational flags including `--batch-all-unwatermarked`, `--dry-run`, `--watermark-only`, and `--force-retry`. Documentation SHALL be available in a dedicated `docs/AI_COVERS.md` file, summarized in `README.md`, and reflected in relevant `Makefile` targets.

#### Scenario: Developer consults AI Cover generation documentation

- **WHEN** a developer looks for information on generating AI covers
- **THEN** they find a dedicated `docs/AI_COVERS.md` file explaining the script usage and operational flags

#### Scenario: Developer uses Makefile to run AI cover generation

- **WHEN** a developer uses `make help` or looks at the `Makefile`
- **THEN** they see documented targets for AI cover generation that use the underlying script flags


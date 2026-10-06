## ADDED Requirements

### Requirement: AI Covers Integration Documentation

The batch watermarking documentation SHALL explicitly cover its integration with the AI cover generation process. Specifically, the system SHALL document how the `scripts/generate_ai_covers.py` script leverages batch watermarking capabilities through flags such as `--batch-all-unwatermarked`, `--dry-run`, `--watermark-only`, and `--force-retry`.

#### Scenario: Operator references watermarking docs for AI covers

- **WHEN** an operator needs to apply watermarks to generated AI covers
- **THEN** the documentation (e.g., in `docs/AI_COVERS.md` or `README.md`) clearly explains the appropriate CLI flags to use

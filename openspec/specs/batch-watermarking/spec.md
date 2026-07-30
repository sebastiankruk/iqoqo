# batch-watermarking Specification

## Purpose
Specify batch cover watermarking execution, corner overlay application, and failure tracking circuit breakers.
## Requirements
### Requirement: Batch watermarking runs as a standalone CLI outside the request path

The system SHALL provide a standalone batch watermarking entrypoint built on `app/utils/images.py` primitives, invocable from the command line (e.g. `python -m app.utils.images watermark-batch`), which processes existing stored cover art without running inside the web request lifecycle.

#### Scenario: CLI processes a covers directory

- **WHEN** an operator invokes the batch watermark CLI against a covers directory
- **THEN** every eligible image file SHALL have the standard watermark applied and be saved in place (or to a configurable output location)

### Requirement: Batch watermarking is idempotent

Re-running the batch watermarking process over an already-processed directory SHALL NOT re-watermark files, detected via a perceptual-hash-based skip mechanism or equivalent watermark-detection check.

#### Scenario: Second run is a no-op

- **WHEN** the batch watermark CLI runs twice over the same directory
- **THEN** the second run SHALL skip all previously watermarked files and leave their bytes unchanged

### Requirement: Batch watermarking is invocable via Makefile

The batch watermarking process SHALL be exposed as a `Makefile` batch target (e.g. `make batch-watermark`) consistent with existing batch operations such as `fix-physical-kinds` and `validate-yaml`, supporting a dry-run mode.

#### Scenario: Makefile target invokes the CLI

- **WHEN** an operator runs `make batch-watermark`
- **THEN** the Makefile SHALL invoke the watermark batch entrypoint inside the project virtual environment

#### Scenario: Dry run reports without writing

- **WHEN** the process is invoked with the dry-run flag
- **THEN** it SHALL report the files it would process without modifying any file on disk

### Requirement: Batch watermarking ships with test coverage

The batch watermarking capability SHALL ship with pytest coverage of the CLI behavior (processing, idempotent skip, dry-run) and BATS coverage of the Makefile target, matching the testing precedent of other Makefile batch operations.

#### Scenario: Test suite guards the batch operation

- **WHEN** the test suite runs
- **THEN** at least one pytest SHALL verify idempotent reprocessing behavior and at least one BATS test SHALL verify the Makefile target invokes the CLI

### Requirement: AI Cover Generator Circuit Breaker

The AI cover generation script (`scripts/generate_ai_covers.py`) SHALL track failures to prevent infinite retry loops that waste LLM tokens and risk rate limits. When a generation fails, the system SHALL increment a `failed_llm_attempts` counter in the manifestation's `meta` JSON. If an item exceeds a defined threshold (e.g. 3 attempts), the script SHALL skip the item on future runs unless explicitly overridden with a `--force-retry` flag.

#### Scenario: Script skips repeatedly failing items

- **WHEN** the batch script processes an item that has `failed_llm_attempts >= 3` in its `meta` payload
- **THEN** the script SHALL skip generation for that item and proceed to the next, conserving LLM tokens

#### Scenario: Script retries on force flag

- **WHEN** the operator invokes the script with `--force-retry`
- **THEN** the script SHALL ignore the `failed_llm_attempts` counter and attempt to generate the cover

### Requirement: AI Covers Integration Documentation

The batch watermarking documentation SHALL explicitly cover its integration with the AI cover generation process. Specifically, the system SHALL document how the `scripts/generate_ai_covers.py` script leverages batch watermarking capabilities through flags such as `--batch-all-unwatermarked`, `--dry-run`, `--watermark-only`, and `--force-retry`.

#### Scenario: Operator references watermarking docs for AI covers

- **WHEN** an operator needs to apply watermarks to generated AI covers
- **THEN** the documentation (e.g., in `docs/AI_COVERS.md` or `README.md`) clearly explains the appropriate CLI flags to use


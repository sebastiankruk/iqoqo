# batch-watermarking Specification

## Purpose
TBD - created by archiving change release-0-7-13. Update Purpose after archive.
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

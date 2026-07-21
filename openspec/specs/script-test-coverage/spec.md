# script-test-coverage

## Purpose

TBD

## Requirements

### Requirement: fix_physical_kinds.py has BATS test coverage

The system SHALL have a BATS test file that verifies the `scripts/fix_physical_kinds.py` script for audit mode, interactive mode, apply mode, and error conditions.

#### Scenario: Script exits successfully in audit mode

- **WHEN** `scripts/fix_physical_kinds.py` is executed with the audit flag
- **THEN** the script SHALL exit with code 0
- **THEN** the output SHALL include an audit report of physical kinds

#### Scenario: Script handles interactive mode

- **WHEN** `scripts/fix_physical_kinds.py` is executed with the interactive flag
- **THEN** the script SHALL prompt the user for mapping decisions

#### Scenario: Script applies mappings in apply mode

- **WHEN** `scripts/fix_physical_kinds.py` is executed with the apply flag and valid mappings
- **THEN** the script SHALL exit with code 0
- **THEN** the output SHALL indicate that physical kinds were updated

#### Scenario: Script dry-run reports without applying

- **WHEN** `scripts/fix_physical_kinds.py` is executed with `--dry-run` flag
- **THEN** the script SHALL report changes without modifying data
- **THEN** the exit code SHALL be 0

#### Scenario: Script fails on invalid target

- **WHEN** `scripts/fix_physical_kinds.py` is executed with an invalid target kind
- **THEN** the script SHALL exit with a non-zero code
- **THEN** the output SHALL contain an error message

#### Scenario: Script warns on empty mappings

- **WHEN** `scripts/fix_physical_kinds.py` is executed and format_mappings.yaml contains no entries
- **THEN** the script SHALL print a warning
- **THEN** the script SHALL exit without making changes

### Requirement: refetch_metadata.py has BATS test coverage

The system SHALL have a BATS test file that verifies the `scripts/refetch_metadata.py` script for gap detection, rate limiting, dry-run, force flag, and skip logic.

#### Scenario: Script detects metadata gaps

- **WHEN** `scripts/refetch_metadata.py` is executed in gap-detection mode
- **THEN** the script SHALL identify items with missing metadata fields

#### Scenario: Script respects rate limiting

- **WHEN** `scripts/refetch_metadata.py` processes multiple items
- **THEN** requests SHALL be spaced according to the configured rate limit

#### Scenario: Script dry-run makes no changes

- **WHEN** `scripts/refetch_metadata.py` is executed with `--dry-run`
- **THEN** the script SHALL report what would be fetched without writing to the database
- **THEN** the exit code SHALL be 0

#### Scenario: Force flag overrides skip logic

- **WHEN** `scripts/refetch_metadata.py` is executed with `--force` on an item that was recently checked
- **THEN** the script SHALL refetch metadata regardless of the last-checked timestamp

#### Scenario: Script skips already-checked items

- **WHEN** `scripts/refetch_metadata.py` is executed on an item that was recently checked
- **THEN** the script SHALL skip that item without refetching

#### Scenario: Script never overwrites existing data

- **WHEN** `scripts/refetch_metadata.py` encounters an item that already has metadata
- **THEN** the script SHALL NOT overwrite existing metadata with external source data

### Requirement: format_mappings.yaml validation is tested

The system SHALL have BATS tests that verify format_mappings.yaml is valid YAML and contains expected mapping structure.

#### Scenario: format_mappings.yaml is valid YAML

- **WHEN** format_mappings.yaml is parsed as YAML
- **THEN** the file SHALL parse without syntax errors

#### Scenario: format_mappings.yaml has expected structure

- **WHEN** format_mappings.yaml is loaded
- **THEN** the file SHALL contain mapping entries with source and target physical kinds

#### Scenario: format_mappings.yaml is not empty

- **WHEN** format_mappings.yaml is loaded
- **THEN** the file SHALL contain at least one mapping entry

### Requirement: Makefile targets for tooling scripts are tested

The system SHALL have BATS tests that verify the Makefile targets for `fix-physical-kinds` and `refetch-metadata` are defined and invoke the correct scripts.

#### Scenario: make fix-physical-kinds target exists

- **WHEN** `make -n fix-physical-kinds` is executed
- **THEN** the output SHALL include invocation of `scripts/fix_physical_kinds.py`
- **THEN** the exit code SHALL be 0

#### Scenario: make refetch-metadata target exists

- **WHEN** `make -n refetch-metadata` is executed
- **THEN** the output SHALL include invocation of `scripts/refetch_metadata.py`
- **THEN** the exit code SHALL be 0

#### Scenario: make targets pass flags to scripts

- **WHEN** `make -n fix-physical-kinds AUDIT=1` is executed
- **THEN** the output SHALL include the `--audit` flag passed to the script

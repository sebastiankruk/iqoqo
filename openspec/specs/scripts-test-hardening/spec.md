## ADDED Requirements

### Requirement: validate_yaml.py has unit and integration test coverage
The `scripts/validate_yaml.py` script SHALL have a pytest unit test covering valid YAML, invalid YAML syntax, missing file, and the YAML content validation logic. A BATS test SHALL verify the `make validate-yaml` target invokes the script correctly.

#### Scenario: validate_yaml returns success for valid YAML
- **WHEN** `validate_yaml()` is called with a path to a valid YAML file
- **THEN** the function SHALL return a truthy value or exit code 0

#### Scenario: validate_yaml returns failure for invalid YAML syntax
- **WHEN** `validate_yaml()` is called with a path to a malformed YAML file
- **THEN** the function SHALL return a falsy value or exit code non-zero

#### Scenario: validate_yaml handles missing file gracefully
- **WHEN** `validate_yaml()` is called with a path to a non-existent file
- **THEN** the function SHALL return a falsy value or exit code non-zero without throwing an unhandled exception

#### Scenario: make validate-yaml invokes the script
- **WHEN** `make validate-yaml` is executed
- **THEN** the `validate_yaml.py` script SHALL be invoked

### Requirement: sync_version.py CLI modes are unit tested
The `scripts/sync_version.py` script SHALL have pytest unit tests for the `--bump patch`, `--bump minor`, `--bump major`, `--set <version>`, and default sync CLI modes. Tests SHALL mock file I/O and verify the correct version string is written to all target files.

#### Scenario: --bump patch increments patch version
- **WHEN** `sync_version.py --bump patch` is invoked with current version `0.7.12`
- **THEN** the new version SHALL be `0.7.13`

#### Scenario: --bump minor increments minor and resets patch
- **WHEN** `sync_version.py --bump minor` is invoked with current version `0.7.12`
- **THEN** the new version SHALL be `0.8.0`

#### Scenario: --bump major increments major and resets minor and patch
- **WHEN** `sync_version.py --bump major` is invoked with current version `0.7.12`
- **THEN** the new version SHALL be `1.0.0`

#### Scenario: --set overrides version explicitly
- **WHEN** `sync_version.py --set 2.0.0` is invoked
- **THEN** the new version SHALL be `2.0.0` regardless of current version

### Requirement: json_extract dialect helper is unit tested
The `json_extract()` helper function in `scripts/refetch_metadata.py` SHALL have pytest unit tests verifying it produces correct SQL for both SQLite and PostgreSQL dialects.

#### Scenario: json_extract produces SQLite syntax
- **WHEN** `json_extract()` is called with dialect `sqlite` for a JSON field
- **THEN** the returned SQL SHALL use SQLite-compatible JSON extraction syntax

#### Scenario: json_extract produces PostgreSQL syntax
- **WHEN** `json_extract()` is called with dialect `postgresql` for a JSON field
- **THEN** the returned SQL SHALL use PostgreSQL-compatible JSON extraction syntax

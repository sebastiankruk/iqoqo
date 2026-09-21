## Purpose

Provides test coverage for migration downgrade scenarios to ensure safe rollback procedures when upgrades fail or need to be reverted.

## Requirements

### Requirement: Migration downgrade test for F3 column promotion
The system SHALL have a test that validates the downgrade of `v0_7_19_f3_column_promotion` migration, moving data from promoted columns back to JSONB meta field.

#### Scenario: Successful downgrade

- **WHEN** downgrade migration is executed
- **THEN** data from isbn13, publisher, format_type columns is moved back to meta JSONB field

#### Scenario: Downgrade preserves data integrity

- **WHEN** downgrade migration completes
- **THEN** all data is preserved without loss or corruption

#### Scenario: Downgrade handles NULL values

- **WHEN** downgrade migration encounters NULL values in promoted columns
- **THEN** NULL values are handled gracefully without errors

### Requirement: Downgrade rollback procedure test
The system SHALL have a test that validates the complete rollback procedure including backup restoration.

#### Scenario: Rollback from backup

- **WHEN** migration fails and rollback is initiated
- **THEN** system restores from backup to pre-migration state

#### Scenario: Rollback verification

- **WHEN** rollback completes
- **THEN** system verifies data integrity matches pre-migration state

### Requirement: Downgrade with data conflicts test
The system SHALL have a test that validates downgrade handles data conflicts (e.g., meta field already has conflicting data).

#### Scenario: Downgrade with existing meta data

- **WHEN** downgrade migration encounters existing data in meta field
- **THEN** migration handles conflict according to defined strategy (overwrite, merge, or fail)

### Requirement: Downgrade performance test
The system SHALL have a test that validates downgrade completes within acceptable time limits for large datasets.

#### Scenario: Downgrade of 10000+ records

- **WHEN** downgrade migration runs on dataset with 10000+ records
- **THEN** migration completes within acceptable time limit (e.g., < 5 minutes)

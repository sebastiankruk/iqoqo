## ADDED Requirements

### Requirement: Database connectivity pre-flight check

The backup script SHALL verify database connectivity before attempting any database dump operations.

#### Scenario: Successful connectivity check

- **WHEN** the backup script begins database operations
- **THEN** the script SHALL execute a connectivity test query (`SELECT 1`) against the PostgreSQL database
- **THEN** if the query succeeds, the script SHALL proceed with the database dump
- **THEN** the script SHALL log the successful connectivity check

#### Scenario: Failed connectivity check

- **WHEN** the backup script begins database operations
- **AND** the connectivity test query fails
- **THEN** the script SHALL initiate retry logic (see retry requirement)
- **THEN** the script SHALL log the specific error message from the failed connection attempt

### Requirement: Database role existence verification

The backup script SHALL verify that the configured PostgreSQL role exists before attempting database dump operations.

#### Scenario: Role exists

- **WHEN** the backup script performs pre-flight checks
- **THEN** the script SHALL query `pg_roles` to verify the configured role exists
- **THEN** if the role exists, the script SHALL proceed with the database dump
- **THEN** the script SHALL log successful role verification

#### Scenario: Role does not exist

- **WHEN** the backup script performs pre-flight checks
- **AND** the configured role does not exist in `pg_roles`
- **THEN** the script SHALL exit immediately with exit code 1
- **THEN** the script SHALL log a clear error message indicating the role does not exist
- **THEN** the script SHALL NOT attempt retry logic (permanent configuration error)
- **THEN** the script SHALL suggest checking `POSTGRES_USER` environment variable

### Requirement: Retry logic with exponential backoff

The backup script SHALL implement retry logic with exponential backoff for transient database connection failures.

#### Scenario: Successful retry after transient failure

- **WHEN** a database connectivity check fails
- **AND** the failure is transient (connection timeout, temporary unavailability)
- **THEN** the script SHALL retry the operation up to 3 times
- **THEN** the script SHALL wait 5 seconds before the first retry
- **THEN** the script SHALL wait 10 seconds before the second retry
- **THEN** the script SHALL wait 20 seconds before the third retry
- **THEN** if any retry succeeds, the script SHALL proceed with the database dump
- **THEN** the script SHALL log each retry attempt with the attempt number and delay

#### Scenario: All retries exhausted

- **WHEN** a database connectivity check fails
- **AND** all 3 retry attempts fail
- **THEN** the script SHALL exit with exit code 1
- **THEN** the script SHALL log a detailed error message including all attempted connection errors
- **THEN** the script SHALL suggest checking database container status and network connectivity

#### Scenario: Permanent failure without retry

- **WHEN** a database operation fails with a permanent error (authentication failure, role does not exist, invalid credentials)
- **THEN** the script SHALL NOT retry the operation
- **THEN** the script SHALL exit immediately with a clear error message
- **THEN** the script SHALL distinguish permanent errors from transient errors in log output

### Requirement: Database container status verification

The backup script SHALL verify the database container is running before attempting database operations.

#### Scenario: Container is running

- **WHEN** the backup script begins database operations
- **THEN** the script SHALL check if the database container is in running state
- **THEN** if the container is running, the script SHALL proceed with connectivity checks

#### Scenario: Container is not running

- **WHEN** the backup script begins database operations
- **AND** the database container is not in running state
- **THEN** the script SHALL initiate retry logic to wait for container startup
- **THEN** if the container does not start within the retry period, the script SHALL exit with error
- **THEN** the script SHALL log the container status and suggest checking Docker service

### Requirement: Configurable retry parameters

The backup script SHALL support configurable retry parameters via environment variables.

#### Scenario: Custom retry configuration

- **WHEN** the `BACKUP_RETRY_ATTEMPTS` environment variable is set
- **THEN** the script SHALL use the specified number of retry attempts
- **WHEN** the `BACKUP_RETRY_DELAY_BASE` environment variable is set
- **THEN** the script SHALL use the specified base delay for exponential backoff calculation

#### Scenario: Default retry configuration

- **WHEN** retry environment variables are not set
- **THEN** the script SHALL use default values: 3 attempts, 5-second base delay
- **THEN** delays SHALL be calculated as: base_delay \* 2^(attempt-1)

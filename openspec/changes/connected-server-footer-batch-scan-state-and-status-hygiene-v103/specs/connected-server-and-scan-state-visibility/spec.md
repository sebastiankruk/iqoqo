## ADDED Requirements

### Requirement: Footer Shows Connected Server

The shared `Footer` SHALL display the host of the server the UI is connected to.

#### Scenario: Footer names the server

- **GIVEN** the instance URL is `https://library.example.com`
- **WHEN** any page renders the footer
- **THEN** the footer MUST show `library.example.com`.

### Requirement: Unmistakable Batch-Scan State

The `/scan` page SHALL show a textual ON/OFF batch-scan indicator that does not rely on color alone and is announced to assistive technology on change.

#### Scenario: Default is OFF

- **WHEN** `/scan` first loads
- **THEN** the indicator MUST read OFF.

#### Scenario: Toggle announced

- **WHEN** batch scan is toggled on
- **THEN** the indicator MUST read ON and an `aria-live` region MUST announce the change.

### Requirement: Preview Restart Reaches a Clean State

`iqoprerest` SHALL wait for the backend health endpoint (bounded retry) and the observability dependencies to be ready before probing or running `make status`, SHALL NOT print transient connection errors during the wait, and SHALL exit non-zero only if the stack never becomes healthy.

#### Scenario: Slow start produces no error noise

- **GIVEN** a backend that becomes healthy after several seconds
- **WHEN** `iqoprerest` runs
- **THEN** no health error output MUST be printed before the healthy result.

#### Scenario: Stack never healthy

- **GIVEN** a backend that never becomes healthy within the bound
- **WHEN** `iqoprerest` runs
- **THEN** it MUST exit non-zero with a clear message.

### Requirement: OTel Export Check Ignores Startup Races

`make status` SHALL count OTel collector export failures only after the collector's start-up grace window and SHALL still report `fail` for sustained failures.

#### Scenario: Startup race not an error

- **GIVEN** export failures that all occurred within the grace window after collector start
- **WHEN** `make status` runs
- **THEN** the check MUST NOT report `fail`.

#### Scenario: Sustained failure reported

- **GIVEN** export failures occurring after the grace window
- **WHEN** `make status` runs
- **THEN** the check MUST report `fail`.

### Requirement: Environment Variables Are Classified

`make status` SHALL classify every variable in `.env.example` as `default`, `optional`, or `required` using a committed classification file, SHALL report only absent `required` variables as warnings, and SHALL report absent `default` and `optional` variables as informational.

#### Scenario: Defaulted variable is informational

- **GIVEN** `APP_PORT` is classified `default` and absent from the env file
- **WHEN** `make status` runs
- **THEN** it MUST NOT appear under the warning "Missing" line.

#### Scenario: Required variable warns

- **GIVEN** a variable classified `required` is absent
- **WHEN** `make status` runs
- **THEN** it MUST appear in the warning line.

#### Scenario: Unclassified key fails the test suite

- **GIVEN** a key in `.env.example` with no classification
- **WHEN** the classification test runs
- **THEN** the test MUST fail naming the key.

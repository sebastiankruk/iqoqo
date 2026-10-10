## ADDED Requirements

### Requirement: Allegro Status Inspection & Healthcheck Accuracy
The status check tooling and system health endpoints SHALL accurately determine Allegro token lifecycle states and report diagnostic outcomes without false-positive authentication warnings.

#### Scenario: Active Allegro token reported as pass
- **WHEN** an operator runs `make status` (or `make status prod`)
- **AND** valid Allegro credentials and an active or refreshable token exist in instance settings
- **THEN** the status check outputs a passing check for Allegro API without warnings.

#### Scenario: Unconfigured Allegro credentials reported as info
- **WHEN** an operator runs `make status` on an instance without Allegro credentials configured
- **THEN** the status check outputs an informational note stating Allegro is not configured.

#### Scenario: Probe or database error reported distinctly from authentication failure
- **WHEN** the status script fails to connect to the database or execute the internal probe
- **THEN** the status check reports an explicit probe failure rather than claiming an OAuth handshake is pending.

## MODIFIED Requirements

### Requirement: Observability Documentation and Diagnostic SQL Accuracy

The system documentation in `docs/MONITORING.md` SHALL accurately describe all 8 instrumented layers, default port topologies, RUM token workflow, ad-blocker resilience, and provide functional SQL queries for OpenObserve diagnostics. Every variable name, port, and command it documents SHALL be one the repository actually reads or binds, and it SHALL distinguish values bound at build time from values read at request time.

#### Scenario: Reviewing OpenObserve diagnostic queries

- **WHEN** an SRE consults `docs/MONITORING.md` or SRE expert guidelines
- **THEN** the provided ANSI SQL queries for 5xx errors, worker tracebacks, and container resource metrics execute without syntax or schema errors against OpenObserve endpoints.

#### Scenario: Following a documented port on a multi-stack host

- **WHEN** an operator copies a documented endpoint from `docs/MONITORING.md` on a host that overrides the OpenObserve host port to avoid a collision
- **THEN** the documented command SHALL use the configured host port rather than the default, so it reaches the intended instance instead of a different one on the same host.

#### Scenario: Looking up a RUM configuration variable

- **WHEN** an operator reads `docs/MONITORING.md` to configure browser RUM
- **THEN** the documented variable names SHALL be the names the code reads
- **THEN** the documentation SHALL state which are read by the server at request time and which, if any, are compiled into the client bundle at build time
- **THEN** a variable name that no code path reads SHALL NOT appear as though it were functional.

#### Scenario: Following a documented Make target

- **WHEN** an operator runs a Make target quoted from `docs/MONITORING.md`
- **THEN** the target SHALL exist in the `Makefile`.

#### Scenario: Assessing the RUM credential's exposure

- **WHEN** an operator reviews the browser RUM section
- **THEN** it SHALL state that the client token is delivered to the browser and grants unauthenticated write access to the RUM stream, including session replay and log ingestion
- **THEN** it SHALL record the retention configuration of that stream, stating explicitly where none is configured
- **THEN** it SHALL name the credential used by the provisioning step and the limitation that no RUM-scoped service account exists in the pinned OpenObserve image.

#### Scenario: Checking the health endpoint name

- **WHEN** an operator checks OpenObserve health using the documented path
- **THEN** the documented path SHALL be the path the repository's own diagnostic script queries.
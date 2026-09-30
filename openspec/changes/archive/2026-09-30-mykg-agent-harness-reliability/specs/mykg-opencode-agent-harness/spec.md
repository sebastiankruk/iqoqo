## MODIFIED Requirements

### Requirement: OpenCode Daemon Task Processing

The `opencode_daemon.py` SHALL import shared task-dispatch, timeout-negotiation, sanitization, and answer-writing logic from `daemon_core.py` instead of implementing its own copies, and SHALL delegate to the shared `compute_effective_timeout` function which honors the task payload's `timeout_seconds` field.

The daemon SHALL invoke the opencode CLI using the opencode v2 invocation contract: `opencode run --auto -m <provider/model#variant>`. The daemon SHALL NOT pass flags that the installed opencode major version no longer accepts; specifically it SHALL NOT pass a purity flag or a standalone variant flag. The reasoning-variant selector SHALL be carried as a suffix on the model identifier.

The daemon SHALL deliver the provider credential to the CLI through the provider's declared environment variable, sourcing the key from the read-only credential mount. It SHALL NOT stage credentials as the only delivery mechanism, because the installed opencode version does not read them from the staged file.

The daemon SHALL record the underlying CLI error text in the failure envelope so that a failure is diagnosable from pipeline state alone.

#### Scenario: Task dispatched and answered via opencode CLI

- **WHEN** a `.task.json` file appears in the agent inbox directory
- **THEN** the daemon SHALL invoke `opencode run --auto` with the task prompt and the configured model
- **AND** write a `.answer.json` envelope containing the task ID and LLM response text to the outbox
- **AND** create a `.done` sentinel file in the outbox to signal completion to the mykg pipeline

#### Scenario: Concurrent task processing with configurable workers

- **WHEN** multiple `.task.json` files are present in the inbox simultaneously
- **THEN** the daemon SHALL process up to the configured number of concurrent workers (default: 2)
- **AND** each task SHALL be dispatched to a separate `opencode run` subprocess

#### Scenario: Task-level timeout honored from task payload

- **WHEN** a `.task.json` file contains `"timeout_seconds": 1800`
- **THEN** the daemon SHALL use `daemon_core.compute_effective_timeout` to derive an effective timeout that is at least 1,800 seconds
- **AND** the subprocess SHALL NOT be killed before the effective timeout has elapsed

#### Scenario: Invocation uses the v2 contract with no removed flags

- **WHEN** the daemon dispatches a task
- **THEN** the CLI arguments SHALL contain an auto-approval flag and a model selector
- **AND** SHALL NOT contain a purity flag or a standalone variant flag
- **AND** the model selector value SHALL carry any requested variant as a suffix on the model identifier

#### Scenario: Variant is carried as a model suffix

- **WHEN** a reasoning effort that maps to a specific variant is requested
- **THEN** the model selector SHALL be rendered as the provider-qualified model with that variant appended after a `#`
- **AND** an already-present variant in the configured model SHALL be replaced rather than duplicated

#### Scenario: Provider credential is delivered via environment

- **WHEN** a task is dispatched for a provider that declares an environment variable for its API key
- **AND** the read-only credential mount contains a key for that provider
- **THEN** the child CLI process SHALL receive that key in the declared environment variable
- **AND** the key SHALL NOT appear in the process argument vector
- **AND** the key SHALL NOT be written to any log line

#### Scenario: An explicitly provided environment key takes precedence

- **WHEN** the provider's environment variable is already set in the daemon's own environment
- **THEN** that value SHALL be used
- **AND** the credential mount SHALL NOT override it

#### Scenario: Absent or malformed credential does not fabricate a key

- **WHEN** the credential mount is missing or unparseable and no environment key is set
- **THEN** the daemon SHALL proceed without setting a provider key
- **AND** SHALL NOT raise an error

#### Scenario: Failure envelope records the underlying error

- **WHEN** the CLI exits non-zero
- **THEN** the failure envelope SHALL include the exit code
- **AND** SHALL include the most recent line of the CLI's error output

## ADDED Requirements

### Requirement: Per-Model Variant Degradation

Reasoning effort SHALL map to an ordered preference list of variant names rather than a single fixed name, because variant names are published per model and an unavailable variant is a fatal error in opencode v2. Each preference list SHALL terminate in the absence of a variant, which every model accepts.

The daemon SHALL walk the preference list when the CLI reports a variant as unavailable, and SHALL NOT retry the ladder for any other class of failure. An unknown or absent effort SHALL resolve to sending no variant.

#### Scenario: Unavailable variant degrades to the next candidate

- **WHEN** the CLI rejects a requested variant as unavailable for the selected model
- **THEN** the daemon SHALL retry the same task with the next candidate in the preference list
- **AND** SHALL record the successful answer if a later candidate succeeds

#### Scenario: Ladder terminates at no variant

- **WHEN** every candidate variant is rejected as unavailable
- **THEN** the daemon SHALL make a final attempt with no variant specified
- **AND** SHALL report the task as failed only if that final attempt also fails

#### Scenario: Unrelated failures are not retried

- **WHEN** the CLI fails for a reason other than variant unavailability
- **THEN** the daemon SHALL NOT issue further attempts for that task
- **AND** SHALL record the failure with its cause

#### Scenario: Every ladder terminates safely

- **WHEN** an effort level maps to a preference list
- **THEN** the final entry of that list SHALL be the absence of a variant
- **AND** an unknown or absent effort SHALL produce a list whose only entry is the absence of a variant

### Requirement: Sandboxed Model Probe

The system SHALL provide a way to test whether specific models are usable from inside the AI sandbox, without mutating any mykg session state. The probe SHALL exercise the same sandbox configuration, image, filesystem hardening, egress policy, and credential delivery as the extraction daemon, and SHALL invoke the same credential-delivery path as the daemon so it cannot drift from production behaviour.

The probe SHALL run a control call outside the sandbox first, so that a failure can be attributed either to the model or credential, or to the sandbox environment. The probe SHALL NOT reference session inbox or outbox directories and SHALL NOT run the extraction pipeline.

A successful probe SHALL correspond to a real, billable model call.

#### Scenario: Probe reports per-model results without touching session state

- **WHEN** the probe is run for one or more models
- **THEN** it SHALL report a pass or fail result per model
- **AND** SHALL print the underlying error reason for each failure
- **AND** SHALL NOT create, modify, or delete any file in a mykg session inbox or outbox

#### Scenario: Probe distinguishes a broken harness from a bad model

- **WHEN** the probe is run
- **THEN** it SHALL first attempt the first model outside the sandbox and report that result as a control
- **AND** WHEN the control succeeds but the sandboxed attempt fails, it SHALL indicate the failure is an environment problem rather than a model-selection problem

#### Scenario: Probe uses the daemon credential path

- **WHEN** the probe dispatches a model call inside the sandbox
- **THEN** it SHALL obtain the provider credential through the same mechanism the extraction daemon uses
- **AND** SHALL NOT use a separately constructed credential mechanism

#### Scenario: Probe exit status reflects failures

- **WHEN** one or more models fail
- **THEN** the probe SHALL exit with a non-zero status
- **AND** SHALL list the failing model identifiers

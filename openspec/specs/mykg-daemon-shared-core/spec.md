# mykg-daemon-shared-core Specification

## Purpose

Provides a shared core library for myKG agent daemon harnesses, unifying task discovery, timeout negotiation, payload sanitization, security guardrail injection, answer-envelope writing, and worker-pool lifecycle management so that agent-specific daemons (agy, opencode) only implement CLI invocation differences.

## Requirements

### Requirement: Task-Level Timeout Negotiation
The shared daemon core SHALL compute an effective subprocess timeout by reading the `timeout_seconds` field from the task JSON payload and using it as a floor, combined with a dynamic bonus based on prompt size, so that the daemon never kills a subprocess before the myKG orchestrator's own patience expires.

#### Scenario: Task with explicit timeout_seconds is honored

- **WHEN** a `.task.json` file contains `"timeout_seconds": 1800`
- **AND** the combined prompt is 72,000 characters long
- **THEN** the effective subprocess timeout SHALL be `max(1800, 600 + 72)` = `1800` seconds
- **AND** the subprocess SHALL NOT be killed before 1,800 seconds have elapsed

#### Scenario: Task without timeout_seconds uses dynamic formula

- **WHEN** a `.task.json` file does not contain a `timeout_seconds` field
- **AND** the combined prompt is 10,000 characters long
- **THEN** the effective subprocess timeout SHALL be `max(300, 600 + 10)` = `610` seconds

#### Scenario: Small task uses base timeout floor

- **WHEN** a `.task.json` file does not contain a `timeout_seconds` field
- **AND** the combined prompt is 500 characters long
- **THEN** the effective subprocess timeout SHALL be `max(300, 600 + 0)` = `600` seconds

### Requirement: Unified Payload Sanitization
The shared daemon core SHALL provide a single sanitization function that redacts exfiltration URLs, googleapis domains, Google Docs/Drive/Script domains, base64 data URIs, and long binary blobs from task payloads before they are passed to any agent CLI.

#### Scenario: Task containing googleapis URL is sanitized

- **WHEN** a task prompt contains `https://storage.googleapis.com/bucket/object`
- **THEN** the sanitization function SHALL replace it with `[REDACTED_GOOGLEAPIS_URL]`

#### Scenario: Task containing base64 data URI is sanitized

- **WHEN** a task prompt contains a `data:image/png;base64,` URI with 100+ characters of base64 payload
- **THEN** the sanitization function SHALL replace it with `[REDACTED_DATA_URI_BLOB]`

### Requirement: Unified Security Guardrail Injection
The shared daemon core SHALL provide a function that constructs the combined prompt by prepending a security guardrail policy statement, followed by the system instructions and user prompt from the task payload.

#### Scenario: Security guardrail prepended to every prompt

- **WHEN** the core constructs a combined prompt from a task payload
- **THEN** the prompt SHALL begin with the security policy text prohibiting data exfiltration and external network requests
- **AND** the system instructions and user prompt SHALL follow

### Requirement: Unified Answer Envelope Writing
The shared daemon core SHALL provide a function that atomically writes the answer envelope (`.answer.json`) and done sentinel (`.done`) to the outbox directory, using a temporary file and atomic rename to prevent partial reads.

#### Scenario: Successful answer written atomically

- **WHEN** an agent CLI returns a successful response
- **THEN** the core SHALL write a `.answer.json.tmp` file first
- **AND** atomically rename it to `.answer.json`
- **AND** create a `.done` sentinel file

#### Scenario: Already-completed task is skipped

- **WHEN** a task's `.done` and `.answer.json` files already exist in the outbox
- **THEN** the core SHALL skip the task without invoking the agent CLI

### Requirement: Unified JSON Fence Stripping
The shared daemon core SHALL provide a function that strips markdown code fences (```` ```json ``` ````) from agent CLI output before parsing it as JSON.

#### Scenario: JSON wrapped in markdown fences is cleaned

- **WHEN** agent CLI output begins with `` ```json `` and ends with `` ``` ``
- **THEN** the function SHALL return only the JSON content between the fences

### Requirement: Unified Worker Pool and Task Discovery
The shared daemon core SHALL provide a daemon run-loop that watches the inbox directory for `.task.json` files, dispatches tasks to a configurable thread pool, and handles SIGINT/SIGTERM for graceful shutdown.

#### Scenario: New task discovered and dispatched

- **WHEN** a `.task.json` file appears in the inbox directory without a corresponding `.done` file in the outbox
- **THEN** the daemon SHALL submit the task to the thread pool for processing

#### Scenario: Graceful shutdown on SIGTERM

- **WHEN** the daemon receives a SIGTERM signal
- **THEN** the daemon SHALL stop accepting new tasks and wait for in-progress tasks to complete

### Requirement: Error Envelope Lifecycle
The shared daemon core SHALL write error envelopes atomically with size limits, using a temp-file-then-rename pattern, and SHALL sanitize and truncate error text to prevent disk exhaustion and information disclosure.

An error envelope SHALL carry the number of attempts made for that task. Writing an error envelope SHALL increment that count rather than refusing to overwrite, until a configurable retry budget is exhausted; once the budget is spent, further writes SHALL be refused and the existing terminal envelope preserved. Envelopes written before attempt counting existed SHALL be treated as having a single attempt, so they benefit from the retry budget rather than being stranded.

#### Scenario: First failure records attempt one

- **WHEN** a task fails for the first time
- **THEN** the system SHALL write an error envelope recording an attempt count of one

#### Scenario: Subsequent failures increment the attempt count

- **WHEN** a task fails again while its retry budget remains
- **THEN** the system SHALL overwrite the envelope with an incremented attempt count and the new error text

#### Scenario: Terminal error is frozen once the budget is spent

- **WHEN** a task fails after the retry budget is exhausted
- **THEN** the system SHALL NOT overwrite the existing envelope
- **AND** SHALL preserve the error text of the attempt that exhausted the budget

#### Scenario: Legacy envelopes count as a single attempt

- **WHEN** an error envelope exists with no attempt count field
- **THEN** the system SHALL treat it as a single attempt

#### Scenario: Invalid task identifiers are rejected

- **WHEN** a task identifier fails validation
- **THEN** the system SHALL NOT write an error envelope
- **AND** SHALL report the invalid identifier without disclosing path details

### Requirement: Retry-Aware Task Completion Gate
The shared daemon core SHALL determine task completion from the presence of a valid answer envelope, or from a failure marker whose retry budget is exhausted. A failure marker within an unexhausted budget SHALL NOT mark the task done, so that transient failures are retried on a later run.

A task SHALL be retried across runs only up to the configured budget, so that a permanently failing task does not consume unbounded resources.

#### Scenario: Answered task is done

- **WHEN** both an answer envelope and a done sentinel exist for a task
- **THEN** the system SHALL report the task as done

#### Scenario: Transient failure is not done

- **WHEN** a task has a failure marker with an attempt count below the retry budget and no answer
- **THEN** the system SHALL report the task as not done
- **AND** a subsequent agent run SHALL attempt it again

#### Scenario: Exhausted budget is terminal

- **WHEN** a task has a failure marker whose attempt count has reached the retry budget and no answer
- **THEN** the system SHALL report the task as done
- **AND** the system SHALL NOT attempt it again

#### Scenario: Answer takes precedence over a failure marker

- **WHEN** a task has both a valid answer envelope and a failure marker within budget
- **THEN** the system SHALL report the task as done

#### Scenario: Retry budget is configurable

- **WHEN** the retry budget is configured to a different value
- **THEN** the system SHALL use that value as the number of attempts after which a failure becomes terminal

### Requirement: Successful Recovery Clears Failure Record
When a task that previously failed is subsequently answered, the system SHALL remove its failure marker as part of writing the answer, so that the outbox does not simultaneously report a task as both failed and complete.

#### Scenario: Recovered task no longer advertises a failure

- **WHEN** a task with an existing failure marker is answered successfully
- **THEN** the system SHALL remove the failure marker
- **AND** SHALL report the task as done

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

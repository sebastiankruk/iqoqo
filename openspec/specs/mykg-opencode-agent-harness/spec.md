# mykg-opencode-agent-harness Specification

## Purpose

Harness for running and evaluating OpenCode agents against myKG daemons.

## Requirements

### Requirement: OpenCode Daemon Task Processing
The `opencode_daemon.py` SHALL import shared task-dispatch, timeout-negotiation, sanitization, and answer-writing logic from `daemon_core.py` instead of implementing its own copies, and SHALL delegate to the shared `compute_effective_timeout` function which honors the task payload's `timeout_seconds` field.

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

### Requirement: OpenCode Daemon Prompt Sanitization
The opencode daemon SHALL use the shared `sanitize_task_payload` function from `daemon_core.py` to sanitize incoming task payloads before constructing the CLI invocation.

#### Scenario: Incoming task containing exfiltration URLs is sanitized

- **WHEN** a task prompt contains URLs pointing to `googleapis.com`, Google Drive, Google Docs, cloud storage endpoints, or unbroken base64 data URIs
- **THEN** the daemon SHALL redact those patterns before passing the prompt to the opencode CLI

#### Scenario: Security guardrail prepended to every prompt

- **WHEN** the daemon constructs the prompt invocation for `opencode run`
- **THEN** the prompt SHALL include the same explicit security guardrail instructions prohibiting data exfiltration and external network requests

## MODIFIED Requirements

### Requirement: OpenCode Daemon Task Processing
The `opencode_daemon.py` SHALL watch the mykg agent inbox directory for `.task.json` files, dispatch each task to the opencode CLI via `opencode run --auto -m <provider/model>`, and write `.answer.json` plus `.done` sentinel files to the agent outbox directory upon successful completion. If the subprocess exits with a non-zero status or fails to start, the daemon SHALL write an `.error` sentinel file to the outbox to signal failure to the mykg pipeline.

#### Scenario: Task dispatched and answered via opencode CLI
- **WHEN** a `.task.json` file appears in the agent inbox directory
- **THEN** the daemon SHALL invoke `opencode run --auto` with the task prompt and the configured model
- **AND** write a `.answer.json` envelope containing the task ID and LLM response text to the outbox
- **AND** create a `.done` sentinel file in the outbox to signal completion to the mykg pipeline

#### Scenario: Concurrent task processing with configurable workers
- **WHEN** multiple `.task.json` files are present in the inbox simultaneously
- **THEN** the daemon SHALL process up to the configured number of concurrent workers (default: 2)
- **AND** each task SHALL be dispatched to a separate `opencode run` subprocess

#### Scenario: Hard failure writes error sentinel
- **WHEN** the opencode subprocess exits with a non-zero status or an unhandled exception occurs during dispatch
- **THEN** the daemon SHALL create a `.error` (or `.error.json`) sentinel file in the outbox
- **AND** the daemon SHALL NOT create a `.done` sentinel for that task

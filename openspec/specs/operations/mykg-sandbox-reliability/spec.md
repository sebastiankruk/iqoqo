# operations/mykg-sandbox-reliability Specification

## Purpose

Provides orchestration reliability guarantees for the myKG agent sandbox, including startup synchronization with proxy dependencies and fail-fast protocol support for immediate terminal errors.

## Requirements

### Requirement: Synchronous Proxy Health Checks
The myKG sandbox orchestration SHALL ensure that any agent daemon container does not attempt to start or connect to the network until its required egress proxy dependency is fully healthy.

#### Scenario: Daemon waits for proxy health

- **WHEN** the sandbox environment is started via the Makefile (`make mykg-update` or similar)
- **THEN** the daemon container deployment SHALL block on the `sandbox-egress-proxy` service reaching a healthy state
- **AND** the daemon SHALL NOT encounter `connection refused` errors to port 3128 on startup

### Requirement: Agent Adapter Fail-Fast Sentinel Protocol
The myKG agent adapter SHALL monitor the filesystem outbox for both `.done` and `.error` (or `.error.json`) sentinels, immediately aborting the polling loop if an error sentinel is detected instead of waiting for the maximum timeout duration.

#### Scenario: Orchestrator detects error sentinel and fails fast

- **WHEN** an agent daemon writes a `.error` (or `.error.json`) sentinel file for a task to the outbox
- **THEN** the orchestrator's agent adapter SHALL immediately detect the sentinel during its polling loop
- **AND** the adapter SHALL raise an exception detailing the failure without waiting for the task's timeout to expire

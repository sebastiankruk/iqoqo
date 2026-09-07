# ai-sandbox-egress-filtering Specification

## Purpose

Restricts autonomous AI sandbox container network egress exclusively to Google Gemini, Google OAuth, and Antigravity ecosystem endpoints, preventing arbitrary data exfiltration and internal network lateral movement.

## Requirements

### Requirement: Gemini-Only Network Egress Isolation
The AI sandbox container environment SHALL restrict all outbound network traffic exclusively to authorized Google Gemini API, Google OAuth authentication endpoints, and Antigravity verification domains. All other outbound public Internet traffic SHALL be blocked.

#### Scenario: Outbound connection to Google Gemini API succeeds

- **WHEN** the autonomous daemon inside the AI sandbox initiates an HTTPS connection to `generativelanguage.googleapis.com`, `cloudcode-pa.googleapis.com`, `daily-cloudcode-pa.googleapis.com`, `autopush-cloudcode-pa.sandbox.googleapis.com`, `oauth2.googleapis.com`, `accounts.google.com`, `antigravity-unleash.goog`, `antigravity.google`, `www.googleapis.com`, `play.googleapis.com`, `lh3.googleusercontent.com`, or `fonts.gstatic.com`
- **THEN** the connection SHALL be permitted through the egress filter and succeed

#### Scenario: Outbound connection to unauthorized external host is blocked

- **WHEN** any process inside the AI sandbox attempts an outbound TCP or UDP connection to an unauthorized external IP, domain, or port, including unauthenticated storage or form services like `storage.googleapis.com` or `docs.google.com`
- **THEN** the connection SHALL be rejected or dropped by the network egress policy

### Requirement: Internal Network Lateral Movement Prevention
The AI sandbox container environment SHALL NOT be permitted to establish direct network connections to internal application services, PostgreSQL databases, Redis instances, or host RFC1918 network interfaces.

#### Scenario: Outbound connection to internal services is blocked

- **WHEN** any process inside the AI sandbox attempts to connect to internal application container IPs or private RFC1918 subnets
- **THEN** the connection SHALL be blocked and prohibited from communicating with internal infrastructure

### Requirement: Automated Egress Verification Suite
The test suite SHALL include automated regression tests verifying that the sandbox environment configuration enforces network egress restrictions and fails closed against unauthorized destinations.

#### Scenario: Regression test validates egress firewall enforcement

- **WHEN** the Bats test suite executes the sandbox network isolation tests
- **THEN** the test suite verifies that network isolation and egress restrictions are defined and reject unauthorized outbound destinations

### Requirement: Inbound Daemon Prompt Sanitization and Egress Guardrails
The `mykg-agy-daemon` SHALL sanitize incoming task payloads and inject explicit egress guardrail instructions to prevent prompt-injection driven data exfiltration and buffer stall.

#### Scenario: Incoming task containing googleapis.com or exfiltration URLs is sanitized

- **WHEN** a task prompt delivered to the daemon contains URLs pointing to `googleapis.com`, Google Drive, Google Docs, cloud storage endpoints, or unbroken base64 data URIs/binary blobs
- **THEN** the daemon SHALL redact or neutralize the domains and binary blobs prior to executing the `agy` CLI process

#### Scenario: Prompt execution includes security policy guardrail

- **WHEN** the daemon constructs the prompt invocation for `agy`
- **THEN** the prompt SHALL include explicit security guardrail instructions directing the agent never to transmit data or credentials to external network addresses

### Requirement: Autonomous AI Sandbox Daemon Lifecycle and Clean Shutdown
The AI sandbox daemon container orchestration (`mykg-agy-daemon`) SHALL manage container lifecycle events gracefully, ensuring pre-flight container removal and trapping termination signals (`SIGINT`, `SIGTERM`, and `EXIT`) to cleanly tear down daemon processes and prevent container name collisions.

#### Scenario: Daemon environment handles SIGINT interruption without container leakage

- **WHEN** a running `mykg` index or update process receives a `SIGINT` (Ctrl+C) or `SIGTERM` signal
- **THEN** the signal trap SHALL catch the signal and invoke teardown commands (`docker compose down` and removal of `mykg-agy-daemon`)
- **AND** the Docker container `mykg-agy-daemon` SHALL NOT remain in running or stopped collision states

#### Scenario: Pre-flight container collision prevention

- **WHEN** an autonomous `mykg` indexing or update operation begins
- **THEN** any preexisting or dangling `mykg-agy-daemon` container SHALL be forcibly removed prior to spawning the new container instance
- **AND** subsequent container creation SHALL NOT fail due to container name collision errors

#### Scenario: Teardown executes on normal exit

- **WHEN** the `mykg` index or update process completes normally with success or non-zero exit code
- **THEN** the signal trap SHALL execute container teardown and exit with the original process exit code

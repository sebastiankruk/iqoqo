# ai-sandbox-egress-filtering Specification

## Purpose

Restricts autonomous AI sandbox container network egress exclusively to Google Gemini, Google OAuth, and Antigravity ecosystem endpoints, preventing arbitrary data exfiltration and internal network lateral movement.

## Requirements

### Requirement: Gemini-Only Network Egress Isolation
The AI sandbox container environment SHALL restrict all outbound network traffic exclusively to authorized Google Gemini API, Google OAuth authentication endpoints, and Antigravity verification domains. All other outbound public Internet traffic SHALL be blocked.

#### Scenario: Outbound connection to Google Gemini API succeeds

- **WHEN** the autonomous daemon inside the AI sandbox initiates an HTTPS connection to `generativelanguage.googleapis.com`, `oauth2.googleapis.com`, `accounts.google.com`, `*.googleusercontent.com`, or `*.google.com`
- **THEN** the connection SHALL be permitted through the egress filter and succeed

#### Scenario: Outbound connection to unauthorized external host is blocked

- **WHEN** any process inside the AI sandbox attempts an outbound TCP or UDP connection to an unauthorized external IP, domain, or port
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

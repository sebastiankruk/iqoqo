# operational-guardrails Specification

## Purpose

Defines requirements for operational script safety prompts, containerized migration lifecycle separation, test suite isolation, and agent governance rule hardening to prevent defects from re-appearing.

## Requirements

### Requirement: Destructive Operational Script Safeguards
The system SHALL require interactive typed confirmation and environment checks before performing irreversible database deletions or table drops in operational maintenance scripts.

#### Scenario: Executing database reset command

- **WHEN** an operator initiates a database reset or table drop script in a non-test environment
- **THEN** the script pauses and requires explicit typed confirmation of the database name before proceeding

### Requirement: Isolated Migration Service and Secure Configuration
The system SHALL isolate database migrations into a dedicated one-shot container in Docker Compose architectures and require mandatory environment variables for monitoring credentials.

#### Scenario: Launching production Docker Compose stack

- **WHEN** the container stack starts
- **THEN** database migrations run to completion in a dedicated service prior to web API containers starting

### Requirement: Test Suite Concurrency and Fixture Stability
The system SHALL resolve frontend test library imports at module top-level and isolate test database fixtures to prevent test runner race conditions.

#### Scenario: Running automated test suites concurrently

- **WHEN** frontend and backend test runners execute concurrently in CI
- **THEN** all tests complete deterministically without module loading race conditions or unclosed database handles

### Requirement: Agent Governance Rules and Skill Hardening
The system SHALL enforce persistent development standards in agent rules and skills to prevent regression of secret leaks, unbatched database queries, unwired UI controls, and tangled migration branches.

#### Scenario: Agent assisting with implementation or code review

- **WHEN** an AI agent analyzes or implements architectural features
- **THEN** agent standards enforce secret encryption, SQL-level pagination, dead control prevention, and migration DAG linear discipline

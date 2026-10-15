## Context

Follows the release audit gate pattern established in v0.7.18 and v0.8.4.

## Goals / Non-Goals

**Goals:**
- Guarantee zero regression in security, stability, and observability before v0.9.1 tag.

**Non-Goals:**
- Spinning up external Mastodon/BookWyrm docker containers in CI.

## Decisions

### In-Process Mock Server
* **Decision**: Simulate remote peer using local WSGI/mock server.
* **Rationale**: Fast, deterministic, zero-network test execution.

## Risks / Trade-offs

- ('[Risk] Flaky mock server port allocation in CI', 'Mitigation: Use ephemeral dynamic socket ports.')

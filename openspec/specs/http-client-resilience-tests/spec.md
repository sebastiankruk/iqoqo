# http-client-resilience-tests Specification

## Purpose

Provide pytest test coverage for the SSRF-safe HTTP client's resilience behaviors: DNS resolution timeouts, `str()` type coercion in the redirect loop, and ThreadPoolExecutor lifecycle.

## Requirements

### Requirement: DNS resolution timeout enforcement test

The system SHALL have pytest tests verifying that `_resolve_with_timeout()` enforces a strict 5-second timeout on `socket.getaddrinfo()` calls and properly shuts down the ThreadPoolExecutor.

#### Scenario: DNS resolution completes within timeout

- **WHEN** `_resolve_with_timeout()` is called with a hostname that resolves within 5 seconds
- **THEN** the function SHALL return the DNS resolution results

#### Scenario: DNS resolution exceeds timeout

- **WHEN** `_resolve_with_timeout()` is called with a hostname that takes longer than 5 seconds to resolve
- **THEN** the function SHALL raise `SSRFError` with message containing "DNS resolution timed out"
- **AND** the ThreadPoolExecutor SHALL be shut down with `wait=False`

### Requirement: str() type coercion test for redirect loop

The system SHALL have pytest tests verifying that `str()` type coercion is applied to `current_url` and `next_url` before `urljoin()` in the `safe_get()` redirect loop.

#### Scenario: Redirect with non-string URL object

- **WHEN** `safe_get()` follows a redirect and the location header value or current URL is not a native Python string
- **THEN** `str()` coercion SHALL prevent `TypeError` from `urljoin()`

### Requirement: ThreadPoolExecutor lifecycle test

The system SHALL have pytest tests verifying that `_resolve_with_timeout()` calls `executor.shutdown(wait=False)` to prevent worker thread starvation.

#### Scenario: Executor shutdown after successful resolution

- **WHEN** DNS resolution completes successfully
- **THEN** the ThreadPoolExecutor SHALL be shut down in the `finally` block

#### Scenario: Executor shutdown after timeout

- **WHEN** DNS resolution times out
- **THEN** the ThreadPoolExecutor SHALL be shut down in the `finally` block before raising `SSRFError`

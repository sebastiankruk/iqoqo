## ADDED Requirements

### Requirement: Type-safe redirect URL joining

The system SHALL enforce `str()` coercion on both `current_url` and `next_url` arguments before calling `urllib.parse.urljoin()` within the `safe_get()` redirect loop to prevent `TypeError` crashes caused by non-string redirect header values.

#### Scenario: Redirect with well-formed string Location header

- **WHEN** an external URL returns HTTP 302 with a valid string `Location` header
- **THEN** the system SHALL join the current URL and redirect target using `urljoin(str(current_url), str(next_url))` and proceed with the next hop validation

#### Scenario: Redirect with non-string Location header value

- **WHEN** an external URL returns a redirect response where `response.headers.get("location")` yields a non-string type (e.g., bytes or mock object)
- **THEN** the system SHALL coerce the value to a string via `str()` before passing to `urljoin()`, preventing a `TypeError` crash in the Celery worker

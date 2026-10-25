## MODIFIED Requirements

### Requirement: BoardGameGeek2 Strategy Resilience

The system SHALL query BoardGameGeek via `boardgamegeek2` with rate-limiting backoff (`Retry-After` header support and exponential backoff inside the retry loop), single-request game metadata extraction, and defused XML parsing, and SHALL restrict active external Twitch OAuth probing (`GET /api/system/status?probe=true`) to authenticated administrators.

#### Scenario: BGG rate limit triggers backoff

- **WHEN** BGG API returns HTTP 429 Too Many Requests
- **THEN** The client waits with exponential backoff and retries up to 3 times.

#### Scenario: BGG retry loop sleeps between attempts and honors Retry-After

- **WHEN** `BGGClient._execute_with_backoff` encounters a rate-limit or `429` error with a `Retry-After` duration
- **THEN** The client sleeps for the requested duration (or exponential backoff `base_backoff * (2 ** attempt)`) before the next retry attempt inside the loop.

#### Scenario: Non-admin user requests system status with probe=true

- **WHEN** An unauthenticated or non-admin user requests `GET /api/system/status?probe=true`
- **THEN** The endpoint does NOT execute a live Twitch OAuth token refresh or mutate `InstanceSettings`, returning cached/passive status instead.

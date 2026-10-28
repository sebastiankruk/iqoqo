# bgg2-and-twitch-igdb-integrations Specification

## Purpose
Maintain resilient BoardGameGeek strategy integration and complete Twitch/IGDB health reporting.

## Requirements

### Requirement: BoardGameGeek Strategy Resilience

The system SHALL query BoardGameGeek via maintained `boardgamegeek` (`>=0.13.0`, retaining compatibility with `requests-cache >= 1.0` where legacy `boardgamegeek2` fails with `requests_cache.core` import errors) with defused XML parsing, single-layer rate-limiting backoff (`Retry-After` capped at `10.0` seconds without stacked client retries), and `InstanceSettings` fallback resolution for `BGG_API_TOKEN`, while persisting Twitch/IGDB OAuth token files atomically via `os.replace()` and passing operational status-check parameters via environment variables rather than inline shell-interpolated Python code.

#### Scenario: BGG rate limit triggers backoff

- **WHEN** the BoardGameGeek API returns HTTP `429 Too Many Requests` (including large `Retry-After` headers such as `3600`)
- **THEN** the HTTP adapter sleeps at most `10.0` seconds per attempt and executes a single bounded retry loop up to 3 times rather than multiplying library and adapter retries

#### Scenario: Twitch/IGDB token cache updates atomically without partial reads

- **WHEN** an administrator or lookup refreshes the Twitch OAuth token cache `.igdb_token.json` concurrently with status checks
- **THEN** the token payload is written to a `0600` temporary sibling file and atomically replaced via `os.replace()` so concurrent readers never observe a truncated JSON file

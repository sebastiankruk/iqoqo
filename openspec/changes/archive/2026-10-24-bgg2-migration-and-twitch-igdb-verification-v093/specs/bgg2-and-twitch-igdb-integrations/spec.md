## Purpose
Migrate BoardGameGeek strategy to boardgamegeek2 and complete Twitch/IGDB health reporting.

## ADDED Requirements

### Requirement: BoardGameGeek2 Strategy Resilience

The system SHALL query BoardGameGeek via boardgamegeek2 with rate-limiting backoff and defused XML parsing.

#### Scenario: BGG rate limit triggers backoff
- **WHEN** BGG API returns HTTP 429 Too Many Requests
- **THEN** The client waits with exponential backoff and retries up to 3 times.


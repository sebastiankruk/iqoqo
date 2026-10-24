## Why
The legacy `boardgamegeek` package has unhandled rate-limit crashes and XML parsing issues; Twitch/IGDB integration requires deterministic health reporting matching Allegro standards.
## What Changes

- Migrate `app/utils/bgg.py` and `app/strategies/boardgame.py` to `boardgamegeek2`.
- Add XML safety (`defusedxml`), exponential backoff, and outbound OTel telemetry spans to BGG calls.
- Verify Twitch OAuth token refresh and expose 4-state health status (`DISABLED`, `CONFIGURED_VALID`, `EXPIRED_NEEDS_REFRESH`, `AUTH_ERROR`) in `app/api/system.py`.
- Update `scripts/iqoqo-status.sh` to report BGG and Twitch/IGDB status.

## Capabilities

### New Capabilities
- `bgg2-and-twitch-igdb-integrations`: Migrate BoardGameGeek strategy to boardgamegeek2 and complete Twitch/IGDB health reporting

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

Updates external API strategies, requirements.txt, and operational status scripts.

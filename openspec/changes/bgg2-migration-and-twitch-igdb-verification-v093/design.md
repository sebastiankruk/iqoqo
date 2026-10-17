## Context

Addresses BGG reliability issues noted in development roadmap.

## Goals / Non-Goals

**Goals:**
- Eliminate ingestion crashes caused by BGG upstream rate limiting.

**Non-Goals:**
- Full local caching of BGG XML dump.

## Decisions

### Boardgamegeek2 Library
* **Decision**: Adopt maintained `boardgamegeek2` fork.
* **Rationale**: Includes built-in retry handling and modern Python typing.

## Risks / Trade-offs

- ('[Risk] Upstream BGG API latency spikes', 'Mitigation: Enforce 15-second provider timeout budget.')

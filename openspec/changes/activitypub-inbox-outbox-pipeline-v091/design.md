## Context

Adapts Phase 4 of federation plan to dedicated Celery worker architecture.

## Goals / Non-Goals

**Goals:**
- Async message ingestion without blocking HTTP request threads.

**Non-Goals:**
- Client-to-server (C2S) ActivityPub API.

## Decisions

### Queue Isolation
* **Decision**: Use dedicated Celery queue `federation`.
* **Rationale**: Prevents slow peer timeouts from starving local ETL or barcode scanning.

## Risks / Trade-offs

- ('[Risk] Remote instance DDoS via inbox flood', 'Mitigation: Rate limiting + 100KB payload cap + signature rejection before DB queries.')

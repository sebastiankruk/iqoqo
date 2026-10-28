## Context

Delivers 'DevOps: Asynchronous Transition Ingestion' from the roadmap.

## Goals / Non-Goals

**Goals:**
- Sub-50ms write latency for catalog and inventory transitions.

**Non-Goals:**
- Replacing PostgreSQL FTS with Elasticsearch/Meilisearch.

## Decisions

### Redis Debounce Coalescing
* **Decision**: Coalesce multiple rapid updates to the same entity ID within a 5-second window.
* **Rationale**: Reduces redundant FTS index writes by up to 80%.

## Risks / Trade-offs

- ('[Risk] Eventual consistency search lag', 'Mitigation: Search updates reflect within 1-5 seconds; UI updates immediately via local state.')

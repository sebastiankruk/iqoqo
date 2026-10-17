## Context

Resolves roadmap target 'SPARQL vs Access Rights' and finalizes Fuseki evaluation.

## Goals / Non-Goals

**Goals:**
- Strict privacy enforcement with minimal snapshot generation overhead.

**Non-Goals:**
- Full graph row-level security inside standard rdflib memory store.

## Decisions

### Retain sparql-runner over Fuseki
* **Decision**: Keep dedicated `sparql-runner` container from v0.8.3 instead of Fuseki.
* **Rationale**: Fuseki requires high JVM RAM unsuitable for Oracle Free Tier tier constraints.

## Risks / Trade-offs

- ('[Risk] Slow snapshot generation on large libraries', 'Mitigation: Use optimized SQLAlchemy keyset filters and streaming serializers.')

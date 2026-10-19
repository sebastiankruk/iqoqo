## Context

Preparation for v1.0.0 mobile clients and agent ecosystem.

## Goals / Non-Goals

**Goals:**
- Single source of truth for all API consumers.

**Non-Goals:**
- Auto-generating frontend TypeScript types at runtime (types remain checked in).

## Decisions

### OpenAPI 3.1 Standard
* **Decision**: Target OpenAPI 3.1.0.
* **Rationale**: Supports full JSON Schema 2020-12 alignment and type arrays.

## Risks / Trade-offs

- ('[Risk] Maintenance overhead of docstrings', 'Mitigation: Automated CI contract test in `test_openapi_contract_completeness.py`.')

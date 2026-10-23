## Context

Maintains ontological purity (FRBR + ActivityStreams + CIDOC CRM) per iqoqo Global Project Rules.

## Goals / Non-Goals

**Goals:**
- Standards-compliant Linked Open Data for social library interactions.

**Non-Goals:**
- Proprietary custom social schemas.

## Decisions

### CIDOC CRM for Custody
* **Decision**: Use `crm:E10_Transfer_of_Custody` for physical media loans.
* **Rationale**: True museum/library archival standard.

## Risks / Trade-offs

- ('[Risk] SHACL performance impact', 'Mitigation: Optimize shape targets to avoid full-graph scans.')

## Context

Combines social networking with physical media circulation.

## Goals / Non-Goals

**Goals:**
- Seamless friend connections and transparent physical custody tracking.

**Non-Goals:**
- Automated postal shipping integration.

## Decisions

### ActivityStreams Offer Pattern
* **Decision**: Loan requests use `as:Offer` targeting the physical Item IRI.
* **Rationale**: Complies with standard ActivityStreams social exchange models.

## Risks / Trade-offs

- ('[Risk] Disputed loans', 'Mitigation: Immutable audit logging in `ItemCustodyEvent`.')

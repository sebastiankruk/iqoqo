## Why
Guarantee zero privacy leakage: private items, non-consented users, and restricted collections must never appear in public RDF or cross-instance SPARQL snapshots.
## What Changes

- Update `app/core/item_access.py` and `app/core/sparql_service.py` to enforce `is_public`, `default_item_visibility`, `FederationConsent`, and friend permissions.
- Ensure `sparql-runner` worker snapshots strictly exclude inaccessible entities.
- Allow authenticated callers to query their own items and authorized friend graphs in bounded snapshots.
- Document architectural decision record in `docs/SPARQL_EXECUTION_SERVICE.md` confirming `sparql-runner` over Apache Fuseki.

## Capabilities

### New Capabilities
- `sparql-federated-access-rights`: Enforce privacy boundaries across SPARQL runner snapshots and public RDF exports, and record Fuseki evaluation ADR

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

Locks down data visibility in SPARQL service and RDF serializers.

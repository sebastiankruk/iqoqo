## Why
Allows federated instances to safely share catalog metadata without risk of spam or unwanted clobbering, routing ambiguous peer updates to the Custodian Merge UI.
## What Changes

- Implement instance trust levels (`untrusted`, `pending`, `trusted`, `blocked`).
- Implement periodic instance health checks in `app/core/scheduler.py` via `app/core/federation_discovery.py`.
- Refactor `app/core/federation_sync.py` to auto-fill empty fields from `trusted` peers with `meta['_provenance']` (`prov:wasDerivedFrom`).
- Route updates from `pending` peers into the Custodian Provider Merge queue (`ProviderMergeDialog`).
- Support linking remote Manifestations to local Expressions and remote Expressions to local Works.

## Capabilities

### New Capabilities
- `federation-trust-graph-sync`: Peer instance Trust Graph, health probes, provenance tracking, and Custodian Provider Merge queue integration

### Modified Capabilities
<!-- No existing capability requirements modified -->

## Impact

Integrates peer federation sync with v0.8.4 Custodian Merge architecture.

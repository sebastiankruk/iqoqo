## MODIFIED Requirements

### Requirement: Coalesced Key Rotation Re-Fetch andTombstone Session Safety
`verify_request` in `app/core/http_signatures.py` SHALL enforce a minimum staleness cooldown before re-fetching a remote actor's public key on signature failure and SHALL persist newly verified rotated keys. `get_entity_tombstone` in `app/core/frbr_merge.py` SHALL detach (`expunge`) the `EntityAuditLog` instance from `db.session` before mutating `diff` in memory for multi-hop resolution.

#### Scenario: Rotated remote public key is persisted and cooldown prevents amplification
- **WHEN** an inbound signed request fails verification against a cached `FederationActor.public_key_pem`
- **THEN** `verify_request` only re-fetches the remote actor document if `last_fetched_at` is older than 60 seconds (or unset), and if the refreshed key verifies the signature, updates `public_key_pem` and `last_fetched_at` in the database

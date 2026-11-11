# Delta Specification: Federation Peering Directionality UX (`C108c`)

## ADDED Requirements

### Requirement: Hostname-Anchored Inbound Activity Detection and Distinct Query (`M-04`)

`get_federation_instances`, `add_federation_instance`, and `update_instance_trust` in `app/api/admin.py` MUST determine `has_inbound_activity` using exact hostname matching on distinct `FederationActivity.actor_uri` values rather than unanchored substring checks.

#### Scenario: Prevent false-positive substring match across peer domains

- **GIVEN** a registered federation instance with domain `"books.org"` and an inbound activity from `"https://notbooks.org/ap/users/alice"`
- **WHEN** `GET /api/admin/federation/instances` or `PUT /api/admin/federation/instances/<id>` computes `has_inbound_activity` for `"books.org"`
- **THEN** `has_inbound_activity` MUST evaluate to `False` (matching only when the parsed `actor_uri` hostname equals `"books.org"`).

#### Scenario: Require `trusted` status before reporting `reciprocal` peering direction

- **GIVEN** a federation instance with `trust_level="untrusted"`, a valid `shared_inbox_url`, and `has_inbound=True`
- **WHEN** `compute_peering_direction(trust_level, shared_inbox_url, has_inbound)` is called
- **THEN** it MUST return `"inbound_only"` rather than `"reciprocal"`.

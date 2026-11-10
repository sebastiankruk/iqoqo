# federation-peering-directionality-ux Specification

## Purpose

Clarify unilateral vs. bilateral federation peering in `/admin/federation` and `/help` by displaying peering directionality and an effective capabilities matrix.

## Requirements

### Requirement: Peering Directionality Badge & Effective Capabilities Matrix

The Admin Federation Instances view (`/admin/federation`) and `/help` documentation SHALL explicitly distinguish between unilateral outbound trust and bilateral reciprocal peering, and SHALL display which catalog and social capabilities (`auto_metadata_sync`, `custodian_merge_queue`, `friend_follows`, `cross_instance_loans`) are active for each peer.

#### Scenario: Admin adds a new peer instance unilaterally

- **GIVEN** an administrator registers `https://peer.example.com` with `trust_level="trusted"` before `peer.example.com` has interacted with the local instance
- **WHEN** `federation-instances.tsx` renders the peer row
- **THEN** it displays the directionality state (`Outbound Only`) and explains that outbound trust enables automatic FRBR metadata enrichment from `peer.example.com`, while reciprocal peering on `peer.example.com` is needed for two-way friend loans.

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

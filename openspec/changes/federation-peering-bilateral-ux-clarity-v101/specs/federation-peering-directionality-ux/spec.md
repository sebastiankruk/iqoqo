## Purpose
Clarify unilateral vs. bilateral federation peering in `/admin/federation` and `/help` by displaying peering directionality and an effective capabilities matrix.

## ADDED Requirements

### Requirement: Peering Directionality Badge & Effective Capabilities Matrix

The Admin Federation Instances view (`/admin/federation`) and `/help` documentation SHALL explicitly distinguish between unilateral outbound trust and bilateral reciprocal peering, and SHALL display which catalog and social capabilities (`auto_metadata_sync`, `custodian_merge_queue`, `friend_follows`, `cross_instance_loans`) are active for each peer.

#### Scenario: Admin adds a new peer instance unilaterally
- **GIVEN** an administrator registers `https://peer.example.com` with `trust_level="trusted"` before `peer.example.com` has interacted with the local instance
- **WHEN** `federation-instances.tsx` renders the peer row
- **THEN** it displays the directionality state (`Outbound Only`) and explains that outbound trust enables automatic FRBR metadata enrichment from `peer.example.com`, while reciprocal peering on `peer.example.com` is needed for two-way friend loans.

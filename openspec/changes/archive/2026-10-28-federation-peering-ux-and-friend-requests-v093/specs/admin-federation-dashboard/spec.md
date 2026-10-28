## ADDED Requirements

### Requirement: Reciprocal Peering Guidance and Asymmetric Trust Indication

The Admin Federation Dashboard (`/admin/federation` and `federation-instances.tsx`) SHALL explain to administrators that ActivityPub peering is unilateral and requires reciprocal peering configuration on the remote instance for mutual trusted federation and follow auto-acceptance.

#### Scenario: Admin views federation instances with peering explanation banner

- **WHEN** an administrator views the Federation Instances panel at `/admin/federation`
- **THEN** the interface renders an informative callout banner explaining that adding a peer establishes local outbound trust only, and that the remote peer administrator must also add this instance to establish reciprocal trust and enable automatic follow acceptance

#### Scenario: Add Instance dialog displays reciprocal peering note

- **WHEN** an administrator opens the "Add Instance" modal dialog
- **THEN** the dialog displays a helper notice clarifying that peering is not automatically bidirectional and requires remote instance registration

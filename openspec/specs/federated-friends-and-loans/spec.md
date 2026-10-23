# federated-friends-and-loans Specification

## Purpose
Cross-instance friend following, collection/wishlist discovery, and ActivityPub loan request workflows.

## Requirements

### Requirement: Cross-Instance Loan Workflows

The system SHALL allow users to request loans from federated friends and dispatch ActivityPub Accept/Reject responses.

#### Scenario: Remote loan request approved

- **WHEN** Owner approves an incoming loan Offer from a remote friend
- **THEN** Item status changes to lent, ItemCustodyEvent is created, and as:Accept is delivered.

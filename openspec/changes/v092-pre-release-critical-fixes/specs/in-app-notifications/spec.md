## ADDED Requirements

### Requirement: Notification Deep-Link Routing for Loans and Escalations
The system SHALL set `target_iri="/item/<id>"` on all loan notifications (`loan_request`, `loan_approved`, `loan_rejected`), emit `loan_approved` / `loan_rejected` notifications upon receiving inbound ActivityPub `Accept` / `Reject` responses to loan `Offer`s, and activate the Escalations tab in `FeedbackPage` when navigated to with `?tab=escalations` or `?tab=my-escalations`.

#### Scenario: Clicking an escalation_resolved notification opens the Escalations tab
- **WHEN** a user clicks an `escalation_resolved` notification linking to `/feedback?tab=my-escalations`
- **THEN** `FeedbackPage` initializes with the Curator Escalations tab active

## ADDED Requirements

### Requirement: Actionable Friend and Follow Notification Routing
The system SHALL set `target_iri="/profile?tab=incoming#friends"` on all incoming `follow_request` and `friend_request` notifications, SHALL include the requester's identity (display name, username, and origin instance domain) in the notification payload message, and SHALL render actionable interaction controls (deep-link navigation to the incoming friends tab and direct response actions) in the Notification Center popover.

#### Scenario: Inbound follow activity generates actionable deep-linked notification
- **WHEN** an ActivityPub `Follow` activity is received for a local user
- **THEN** the system creates a `follow_request` notification with `target_iri="/profile?tab=incoming#friends"`, a payload containing the actor's username, display name, and domain, and the Notification Center renders it with an active navigation link to the incoming friends management tab.

#### Scenario: Responding directly to friend or follow request from notification center
- **WHEN** a user views a pending `friend_request` or `follow_request` in the Notification Center and clicks Accept or Reject
- **THEN** the system executes the response action via API, updates the friendship status, and marks the notification as read without requiring navigation away from the current page.

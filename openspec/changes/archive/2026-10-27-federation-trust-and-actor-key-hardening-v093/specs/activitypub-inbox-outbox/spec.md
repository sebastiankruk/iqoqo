## ADDED Requirements

### Requirement: Opt-In Follow Auto-Accept and Canonical Peer Domain Resolution

The ActivityPub inbound `Follow` handler and actor resolution pipeline SHALL treat follow auto-acceptance as strictly opt-in (`false` by default), evaluate dynamic administrator configuration at runtime, normalize remote peer domains with non-standard ports consistently, and clamp default peer trust to non-privileged levels (`untrusted` or `pending`).

#### Scenario: Inbound Follow defaults to pending approval when auto-accept is unset or disabled

- **WHEN** a remote actor from an `untrusted` or `pending` instance delivers a signed `Follow` activity and `FEDERATION_AUTO_ACCEPT_FOLLOWS` is unset or `false`
- **THEN** the system records the follow relationship as `pending`, emits an in-app follow-request notification to the target local user, and does NOT dispatch an automatic `Accept` activity

#### Scenario: Inbound Follow auto-accepts only when explicitly enabled in settings

- **WHEN** an administrator explicitly sets `FEDERATION_AUTO_ACCEPT_FOLLOWS` to `true` and a remote actor from a non-blocked instance delivers a signed `Follow` activity to a consented user
- **THEN** the system records the follow relationship as `accepted` and dispatches a signed `Accept` activity to the follower's inbox

#### Scenario: Blocked peer on non-standard port cannot bypass blocklist via inbound activities

- **WHEN** an administrator has set trust level `blocked` on `malicious.example:8443` and an inbound signed activity arrives from `https://malicious.example:8443/u/attacker`
- **THEN** actor/instance resolution preserves `:8443` during domain normalization, matches the blocked `malicious.example:8443` instance record, and rejects the activity without creating a portless `malicious.example` record

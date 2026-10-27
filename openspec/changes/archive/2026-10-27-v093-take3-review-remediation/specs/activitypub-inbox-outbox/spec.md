## ADDED Requirements

### Requirement: Strict Opt-In Follow Auto-Accept, Follow State Preservation, and Port-Preserving Handler Enforcement

The ActivityPub inbound inbox and activity handlers (`Follow`, `Create`, `Update`, `Delete`, and `Announce`) SHALL normalize sender actor domains with non-standard ports preserved (`clean_instance_domain`), SHALL auto-accept inbound `Follow` requests ONLY when both `FEDERATION_AUTO_ACCEPT_FOLLOWS` is `true` AND the sender's peer instance has trust level `trusted`, and SHALL preserve existing `accepted` or `rejected` follow states when duplicate `Follow` activities arrive.

#### Scenario: Trusted peer Follow remains pending when auto-accept is disabled

- **WHEN** `FEDERATION_AUTO_ACCEPT_FOLLOWS` is `false` and a remote actor on a `trusted` peer instance sends a signed `Follow` activity to a consented local user
- **THEN** the system records the follow relationship as `pending` for local user approval and does NOT auto-accept or grant `friends_only` visibility

#### Scenario: Untrusted peer Follow remains pending even when auto-accept is enabled

- **WHEN** `FEDERATION_AUTO_ACCEPT_FOLLOWS` is `true` and a remote actor on an `untrusted` or `pending` peer instance sends a signed `Follow` activity
- **THEN** the system records the follow relationship as `pending` and does NOT auto-accept the untrusted follow request

#### Scenario: Duplicate Follow does not overwrite existing rejected or accepted relationship

- **WHEN** a remote actor whose previous follow request is already `rejected` (or already `accepted`) sends another `Follow` activity
- **THEN** a `rejected` relationship remains `rejected` without re-notifying, and an already `accepted` relationship remains `accepted` without being downgraded to `pending`

#### Scenario: Blocked or non-standard-port peer cannot bypass inbox or handler trust checks

- **WHEN** a peer registered as `blocked` on `evil.example:8443` sends any signed activity to `/inbox` or `/api/federation/inbox`, or an unprivileged service on `trusted.example:8443` sends `Create`/`Update`/`Delete`/`Announce` while `trusted.example` (port 443) is `trusted`
- **THEN** the inbox and handlers resolve `evil.example:8443` as `blocked` (`403`) and resolve `trusted.example:8443` independently of `trusted.example`

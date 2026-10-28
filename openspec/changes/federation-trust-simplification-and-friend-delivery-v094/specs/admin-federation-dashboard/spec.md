## MODIFIED Requirements

### Requirement: Admin Federation Instance Management

The admin panel SHALL allow administrators to view, discover, block, and set trust levels for remote Fediverse instances using a 3-category trust model: `trusted`, `untrusted`, and `blocked`.

#### Scenario: Changing instance trust level

- **WHEN** An administrator changes instance trust from `untrusted` to `trusted`
- **THEN** The backend updates `trust_level` to `trusted` and future catalog activities auto-merge empty metadata fields while allowing users who opted into auto-accept to automatically accept follow requests from that peer.

#### Scenario: Peer instance row displays single clear trust selector without redundant pending badge

- **WHEN** an administrator views the Federation Instances list at `/admin/federation`
- **THEN** each peer instance row displays its trust level exclusivamente via the 3-option trust selector (`Trusted`, `Untrusted`, `Blocked`) without rendering a separate `"Pending Review"` status pill next to the selector

### Requirement: Reciprocal Peering Guidance and Asymmetric Trust Indication

The Admin Federation Dashboard (`/admin/federation` and `federation-instances.tsx`) SHALL explain in simple, plain language how peering works, why adding a peer is a one-way setting on this server, and what each of the 3 trust levels (`Trusted`, `Untrusted`, `Blocked`) controls for friend requests, collection/loan requests, and catalog metadata.

#### Scenario: Admin views federation instances with peering explanation banner

- **WHEN** an administrator views the Federation Instances panel at `/admin/federation`
- **THEN** the interface renders a plain-language callout banner explaining that:
  1. Adding a peer sets how **your** server treats requests and data coming from that peer (the other server's admin must also add your domain on their side),
  2. **Trusted** allows catalog metadata to auto-fill empty fields, allows friend & loan requests, and lets local users optionally auto-accept follow requests from this peer,
  3. **Untrusted** (the default for new peers) still allows users to send/receive friend and loan requests with manual approval, while holding incoming catalog edits for custodian review, and
  4. **Blocked** rejects all incoming and outgoing friend requests, loan/collection requests, and catalog updates with that peer

#### Scenario: Add Instance dialog displays reciprocal peering note

- **WHEN** an administrator opens the "Add Instance" modal dialog
- **THEN** the dialog displays a clear, plain-language note that new peers start as **Untrusted** and that the remote server's administrator must also register this server on their end

### Requirement: Localized and Tested Admin Federation Dashboard

The Admin Federation Dashboard (`/admin/federation`, `federation-instances.tsx`, `federation-activity.tsx`, and `instance-settings.tsx`) SHALL use `useTranslations("AdminFederation")` for all user-visible labels, provide `aria-label` attributes on icon-only controls, remove global `FEDERATION_DEFAULT_TRUST` and `FEDERATION_AUTO_ACCEPT_FOLLOWS` controls from the global Admin Settings UI (`instance-settings.tsx`), expose localized controls for Instance Actor Key provisioning and remote peer key fingerprint inspection, and be covered by Vitest unit tests.

#### Scenario: Admin federation components render localized labels and constrained trust selector

- **WHEN** an administrator views `/admin/federation` or the Federation section of `/admin/settings` in English or Polish
- **THEN** all headings, table columns, filters, key fingerprint controls, and dialogs render localized strings from `AdminFederation`, peer trust selectors expose only `Trusted`, `Untrusted`, and `Blocked`, and global `FEDERATION_DEFAULT_TRUST` / `FEDERATION_AUTO_ACCEPT_FOLLOWS` controls are omitted from Admin Settings in favor of per-user profile consent settings

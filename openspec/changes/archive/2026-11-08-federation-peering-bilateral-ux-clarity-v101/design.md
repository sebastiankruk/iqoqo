## Context

In ActivityPub federation, instance trust (`FederationInstance.trust_level`: `trusted | untrusted | blocked`) is configured locally on each node. When an admin adds a peer on Instance A, Instance B does not automatically mark Instance A as `trusted`. While `C87f` and `C89c` simplified trust to 3 levels, the UI still needs to show whether a peer relationship is **Unilateral** or **Bilateral (Reciprocal)** and what capabilities each state unlocks.

## Goals / Non-Goals

**Goals:**
- Compute and expose peering directionality (`outbound_only`, `inbound_seen`, `reciprocal`, `blocked`) on `/api/v1/admin/federation/instances`.
- Render a clear Directionality badge and Effective Capabilities Matrix in `frontend/components/admin/federation-instances.tsx` and `/help` without exceeding button density limits ($\le 4$ buttons per container).

**Non-Goals:**
- Changing the underlying 3-state trust model (`trusted | untrusted | blocked`) established in `C89c`.

## Decisions

### Deriving Directionality from `FederationInstance` + `FederationActivity` / `FederationFollower`
* **Decision:** Mark a peer instance as `reciprocal` when the peer is reachable (`is_reachable=True`, `trust_level != "blocked"`) and we have observed verified signed inbound ActivityPub traffic or accepted follow/instance-actor handshakes from that domain; otherwise label newly added peers as `outbound_only` with a one-line explanation of how the remote admin can reciprocate.
* **Rationale:** Gives admins immediate certainty on whether cross-instance friend follows and loans will succeed end-to-end.

## REMOVED Requirements

### Requirement: Synchronous Proxy Health Checks

**Reason**: The `sandbox-egress-proxy` service and its health-gated daemon startup are deleted with the myKG harness in v0.8.3.

**Migration**: None.

### Requirement: Agent Adapter Fail-Fast Sentinel Protocol

**Reason**: The `.done` / `.error` outbox sentinel protocol existed only for the myKG daemon adapters, which are deleted.

**Migration**: None.

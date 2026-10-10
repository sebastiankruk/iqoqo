## REMOVED Requirements

### Requirement: Gemini-Only Network Egress Isolation

**Reason**: The AI sandbox and its egress-filtering proxy existed solely to run the myKG extraction daemons. With myKG decommissioned in v0.8.3 the sandbox has no consumer, so `docker-compose.ai_sandbox.yml`, `deploy/sandbox_proxy/`, and their allowlists are removed.

**Migration**: None. There is no replacement sandbox; no production or developer workflow depended on this container network.

### Requirement: Internal Network Lateral Movement Prevention

**Reason**: The sandbox that this requirement constrained is removed with myKG.

**Migration**: None.

### Requirement: Automated Egress Verification Suite

**Reason**: The `tests/bash/mykg_tooling.bats` and `tests/test_sandbox_proxy.py` suites that verified the sandbox are removed with it.

**Migration**: None.

### Requirement: Inbound Daemon Prompt Sanitization and Egress Guardrails

**Reason**: The `mykg-agy-daemon` / `mykg-opencode-daemon` task-processing path is removed. The sanitization and guardrail logic lived in `.agents/skills/iqoqo-mykg/scripts/daemon_core.py`, which is deleted.

**Migration**: None.

### Requirement: Autonomous AI Sandbox Daemon Lifecycle and Clean Shutdown

**Reason**: The daemon lifecycle logic lived in `scripts/mykg_sync.sh` and the removed daemon scripts; both are deleted with myKG.

**Migration**: None.

## REMOVED Requirements

### Requirement: OpenCode Daemon Task Processing

**Reason**: `opencode_daemon.py` and the sandbox that ran it are deleted with the myKG harness in v0.8.3.

**Migration**: None.

### Requirement: OpenCode Daemon Prompt Sanitization

**Reason**: The OpenCode myKG daemon is deleted with the harness.

**Migration**: None.

### Requirement: Per-Model Variant Degradation

**Reason**: The variant-degradation ladder lived in `opencode_daemon.py`, which is deleted with the harness.

**Migration**: None.

### Requirement: Sandboxed Model Probe

**Reason**: `scripts/probe_opencode_harness.sh` and `probe_model.py` are deleted with the harness; the `make mykg-probe` target is removed.

**Migration**: None.

## REMOVED Requirements

### Requirement: Bounded Queue Drain Before Sandbox Teardown

**Reason**: `scripts/mykg_sync.sh`, which owned the drain loop and the sandbox teardown, is deleted with the myKG harness in v0.8.3.

**Migration**: None.

### Requirement: Failed Task Re-queueing

**Reason**: `retry_failed.py` and the `make mykg-retry` target are deleted with the harness.

**Migration**: None.

### Requirement: Session Discovery Through Symlinked Storage

**Reason**: The `mykg_sessions/` store and its symlink handling are removed with the harness.

**Migration**: None.

# Proposal: Fix myKG Background Container SIGINT Cleanup

## Why

During autonomous knowledge graph indexing (`make mykg-update` and `make mykg-index`), a background Docker container (`mykg-agy-daemon`) runs in the AI sandbox to process agent inbox tasks asynchronously. If a developer or automation run interrupts execution with `SIGINT` (Ctrl+C) or `SIGTERM`, the Makefile process terminates abruptly before reaching the sequential teardown commands at the end of the recipe.

As a result, the `mykg-agy-daemon` container remains running or persists in Docker's local namespace. Subsequent executions fail immediately with container name collisions (`The container name "/mykg-agy-daemon" is already in use`), silently failing daemon initialization due to `|| true` suppressions and leaving pending extraction tasks unprocessed. Fixing this ensures reproducible, resilient local-first background runs.

## What Changes

- **Signal Traps for Teardown**: Introduce POSIX-compliant shell signal traps (`trap ... EXIT INT TERM`) within `mykg-update` and `mykg-index` Makefile targets to guarantee that sandbox teardown (`docker compose -f docker-compose.ai_sandbox.yml down` and `docker rm -f mykg-agy-daemon`) executes on abnormal exit, termination signals, or normal completion.
- **Pre-Flight Name Collision Cleanup**: Add pre-flight removal of any preexisting `mykg-agy-daemon` container prior to `docker compose run` invocation, ensuring clean container allocation even if a prior run suffered an uncatchable `SIGKILL` or host system reset.
- **Bats Test Hardening**: Add automated unit tests to `tests/bash/mykg_tooling.bats` verifying that Makefile recipes define pre-flight container removal, trap EXIT/INT/TERM signals, and clean up orphaned containers.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `ai-sandbox-egress-filtering`: Adds requirements for background container lifecycle resilience, ensuring `mykg-agy-daemon` performs pre-flight collision prevention and traps SIGINT/SIGTERM/EXIT signals for reliable teardown.

## Impact

- **Affected Systems**: `Makefile` targets (`mykg-update`, `mykg-index`), AI sandbox orchestration (`docker-compose.ai_sandbox.yml`), and Bats test suite (`tests/bash/mykg_tooling.bats`).
- **APIs and Dependencies**: No changes to external APIs or package dependencies.
- **Breaking Changes**: None. Teardown behavior is purely corrective.

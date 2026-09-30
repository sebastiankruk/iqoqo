## ADDED Requirements

### Requirement: Autonomous AI Sandbox Daemon Lifecycle and Clean Shutdown
The AI sandbox daemon container orchestration (`mykg-agy-daemon`) SHALL manage container lifecycle events gracefully, ensuring pre-flight container removal and trapping termination signals (`SIGINT`, `SIGTERM`, and `EXIT`) to cleanly tear down daemon processes and prevent container name collisions.

#### Scenario: Daemon environment handles SIGINT interruption without container leakage
- **WHEN** a running `mykg` index or update process receives a `SIGINT` (Ctrl+C) or `SIGTERM` signal
- **THEN** the signal trap SHALL catch the signal and invoke teardown commands (`docker compose down` and removal of `mykg-agy-daemon`)
- **AND** the Docker container `mykg-agy-daemon` SHALL NOT remain in running or stopped collision states

#### Scenario: Pre-flight container collision prevention
- **WHEN** an autonomous `mykg` indexing or update operation begins
- **THEN** any preexisting or dangling `mykg-agy-daemon` container SHALL be forcibly removed prior to spawning the new container instance
- **AND** subsequent container creation SHALL NOT fail due to container name collision errors

#### Scenario: Teardown executes on normal exit
- **WHEN** the `mykg` index or update process completes normally with success or non-zero exit code
- **THEN** the signal trap SHALL execute container teardown and exit with the original process exit code

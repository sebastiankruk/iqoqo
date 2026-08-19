# rclone-preflight-check Specification

## Purpose

Ensure the rclone configuration directory exists before any application service
starts in a container, preventing silent backup job failures on fresh deployments
where no host bind-mount of the rclone config is present.

Implemented via `deploy/docker-entrypoint.sh`, which runs `mkdir -p ${HOME}/.config/rclone`
before exec-ing the container command. Synced from change `v0716-alembic-migration-sre`.

## Requirements

### Requirement: Pre-start rclone configuration directory check

The container entrypoint SHALL create `${HOME}/.config/rclone` directory if it does
not exist before starting any application services, preventing silent backup job
failures on fresh deployments.

#### Scenario: Fresh container deployment without rclone directory

- **WHEN** a container starts for the first time and `${HOME}/.config/rclone` does not exist
- **THEN** the entrypoint SHALL create the directory with appropriate permissions
- **AND** backup jobs SHALL be able to write rclone configuration files

#### Scenario: Existing container with rclone directory already present

- **WHEN** a container restarts and `${HOME}/.config/rclone` already exists
- **THEN** the entrypoint SHALL not fail or modify existing directory contents
- **AND** the check SHALL be idempotent (safe to run on every start)

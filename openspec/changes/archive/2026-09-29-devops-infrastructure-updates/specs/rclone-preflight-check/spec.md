## Purpose

Retires the in-container rclone requirements that `devops-infrastructure-updates`
made untrue. Superseded by `infrastructure/devops-v082`, which replaces the
`rclone` CLI with boto3 (`app/core/s3_service.py`) inside `web` and `worker`.

The exposure these requirements once described is real and is now closed: the
containers bind-mounted a **plaintext `rclone.conf` containing the S3 secret**
into the process that parses untrusted input. Four bind-mounts across
`docker-compose.yml` and `docker-compose.prebuilt.yml` are removed, and no
container mounts a credential file at all.

## REMOVED Requirements

### Requirement: Pre-start rclone configuration directory check

Removed. The container entrypoint no longer creates `${HOME}/.config/rclone`.

The directory existed only so the in-container `rclone` binary would find a config
to read. With boto3 the credential comes from environment variables, so there is
no config file for a directory to hold. Creating it anyway would imply to an
operator that a mount is expected, and would keep a plaintext S3 secret one bind
mount away.

`deploy/docker-entrypoint.sh` now runs a different pre-start check: it warns when
S3 storage is **half-configured** (a bucket named with no credentials, or
credentials with no bucket), because either way every remote operation silently
no-ops. It also reports a leftover `rclone.conf` so the operator knows to drop the
bind-mount.

#### Scenario: Fresh container deployment

- **WHEN** a container starts and `${HOME}/.config/rclone` does not exist
- **THEN** the entrypoint SHALL NOT create it
- **AND** remote storage SHALL be configured from environment variables alone

#### Scenario: Half-configured S3 storage

- **WHEN** a container starts with `S3_BUCKET_BACKUP` set but no `AWS_ACCESS_KEY_ID`
- **THEN** the entrypoint SHALL warn that remote backups and the shared cover cache will be skipped
- **AND** the entrypoint SHALL name the variable that is missing

#### Scenario: Leftover rclone.conf is reported

- **WHEN** a container starts and `${HOME}/.config/rclone/rclone.conf` exists
- **THEN** the entrypoint SHALL report that the file is no longer used
- **AND** it SHALL tell the operator to remove the bind-mount

## ADDED Requirements

### Requirement: No container mounts a remote-storage credential file

No application service SHALL bind-mount a remote-storage credential file into a
container. Remote storage configuration SHALL be supplied through environment
variables.

#### Scenario: Starting the full stack

- **WHEN** the compose stack starts
- **THEN** no service SHALL mount `rclone.conf`, an AWS credentials file, or any other remote-storage secret from the host
- **AND** remote storage SHALL function from the `AWS_*` and `S3_*` variables alone

#### Scenario: A stale bind-mount is left in place

- **WHEN** a deployment still bind-mounts `rclone.conf` after upgrading
- **THEN** the container SHALL still start
- **AND** the entrypoint SHALL report the file as unused so the mount can be removed

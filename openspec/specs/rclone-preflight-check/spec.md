# rclone-preflight-check Specification

## Purpose

Ensure no application container mounts a remote-storage credential file, and
that a half-configured setup is reported at container start.

Superseded from `rclone-preflight-check` by `devops-infrastructure-updates`. The
original requirement created `${HOME}/.config/rclone` so the in-container
`rclone` binary would find a config to read. With boto3
(`app/core/s3_service.py`) the credential comes from environment variables, so
there is no config file for a directory to hold — and creating one would imply a
mount is expected, keeping a plaintext S3 secret one bind-mount away.

`deploy/docker-entrypoint.sh` now warns when S3 storage is half-configured (a
bucket with no credentials, or credentials with no bucket), because either way
every remote operation silently no-ops and the first symptom is a backup archive
that never appears. It also reports a leftover `rclone.conf` so the operator
knows to drop the bind-mount.

## Requirements

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

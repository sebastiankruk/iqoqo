## Why

To ensure robust disaster recovery and secure infrastructure operations, our backup and deployment processes need formal lifecycle management and hardening. Currently, backups may accumulate indefinitely or lack off-site cold storage, and our deployment/container scripts contain potential security gaps or unused variables (like `DEPLOY_TOKEN`) that cause confusion and increase the attack surface.

## What Changes

- Configure automated retention policy management in `app/core/tasks.py` for backups.
- Implement rules to retain 7 daily and 5 weekly backups locally or in Dropbox.
- Implement logic to transition monthly, quarterly, and yearly archives to AWS S3 Glacier.
- Investigate the usage of `DEPLOY_TOKEN` in the `make stats` process. If it is genuinely unused and doesn't cause failures, remove it to reduce unnecessary secrets management overhead.
- Harden Docker containers and bash scripts against common vulnerabilities (e.g., dropping privileges, setting read-only file systems where applicable, removing unnecessary shell utilities).

## Capabilities

### New Capabilities

- `automated-backup-retention`: A structured backup lifecycle management system that automatically rotates short-term backups (Dropbox) and archives long-term backups (AWS S3 Glacier).
- `deploy-token-cleanup`: Resolution of the `DEPLOY_TOKEN` dependency in the `make stats` workflow.
- `container-hardening`: Security enhancements for Dockerfiles and deployment scripts.

### Modified Capabilities

## Impact

- `app/core/tasks.py` (backup scheduling and rotation logic).
- `Makefile` and associated scripts (related to `make stats` and `DEPLOY_TOKEN`).
- `Dockerfile` definitions (for security hardening).
- Cloud storage configurations (Dropbox, AWS S3).

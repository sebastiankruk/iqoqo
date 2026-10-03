## Context

Our application requires a reliable backup lifecycle and hardened deployment scripts. Currently, the backup strategy lacks formal automated retention policies for long-term storage, which can lead to runaway storage costs or data loss if not managed properly. Furthermore, there's confusion around the `DEPLOY_TOKEN` environment variable in the `make stats` process, and our Docker containers need a security review to ensure they follow best practices (like running as non-root).

## Goals / Non-Goals

**Goals:**

- Automate the retention of database/file backups (7 daily, 5 weekly in Dropbox).
- Automate the transition of older backups (monthly, quarterly, yearly) to AWS S3 Glacier via `app/core/tasks.py`.
- Investigate and potentially remove the `DEPLOY_TOKEN` from the `Makefile` if it serves no active purpose.
- Harden Dockerfiles (e.g., dropping root privileges) and deployment scripts.

**Non-Goals:**

- Migrating the primary application database hosting to AWS (only backups are moving to S3 Glacier).
- Completely rewriting the build pipeline (focusing only on the `DEPLOY_TOKEN` and script hardening).

## Decisions

### 1. Backup Retention Strategy

- **Decision**: We will implement a Celery task in `app/core/tasks.py` that runs daily to manage backup rotation. It will use the `boto3` library to interface with AWS S3 Glacier for long-term archives and the Dropbox API for short-term storage.
- **Rationale**: Centralizing the logic in Python/Celery allows for better error handling, logging, and integration with the application's existing ecosystem compared to a pure bash cron job.

### 2. `DEPLOY_TOKEN` Cleanup

- **Decision**: We will audit the `Makefile` and related scripts. If `DEPLOY_TOKEN` is found to be obsolete, we will remove it completely. If it is optional, we will document its purpose clearly and ensure `make stats` handles its absence gracefully.
- **Rationale**: Removing dead code and unused secrets reduces confusion and potential security risks.

### 3. Container Hardening

- **Decision**: We will modify the Dockerfiles to create a dedicated non-root user (e.g., `appuser`) and run the application process under that user. We will also ensure that sensitive files are not world-readable.
- **Rationale**: Running as a non-root user is a fundamental container security best practice to mitigate container escape vulnerabilities.

## Risks / Trade-offs

- [Risk] **AWS S3 Glacier transition logic deletes active backups** → Mitigation: Implement a "dry run" mode and extensive unit tests for the retention logic before enabling it in production.
- [Risk] **Permissions issues when running containers as non-root** → Mitigation: Thoroughly test the hardened containers locally, especially volume mounts and log file generation, to ensure the `appuser` has the correct access rights.

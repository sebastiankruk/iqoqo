## Context

Closes out 'Migrate rclone to S3' from the technical debt roadmap.

## Goals / Non-Goals

**Goals:**
- Eliminate rclone config synchronization overhead.

**Non-Goals:**
- Multi-cloud concurrent replication.

## Decisions

### Native boto3 Client
* **Decision**: Use standard `boto3` / AWS SDK compatible with Oracle Object Storage, AWS S3, Cloudflare R2, and MinIO.
* **Rationale**: Maximum cloud flexibility.

## Risks / Trade-offs

- ('[Risk] Backup script failure on older S3 providers', 'Mitigation: Verified in BATS test suite.')

## Why

Address critical findings from PR #258 reviews (Copilot, QA, SRE, Ontologist, Security). We need to fix IDOR vulnerabilities, migration failure risks on SQLite, subprocess command injections, missing ontology mappings, and deployment configurations before or shortly after merging the release to maintain security and stability.

## What Changes

- **Deployment**: Set `ENV HOME=/home/appuser` in `deploy/Dockerfile` and apply secure permissions (`0700` and `0600`) for rclone config in `deploy/docker-entrypoint.sh`. Add `RCLONE_FEEDBACK_REMOTE` variable to `.env.example`.
- **Database**: Add missing PostgreSQL dialect check in Alembic migration `f65648a6aaf4_add_feedback_comments_schema.py` to prevent failures on SQLite. Fix N+1 problem in `app/db/social.py` for `FeedbackItem.comments` by changing to `lazy="selectin"`.
- **Security**: Fix IDOR in `app/api/feedback.py` screenshot download endpoint by adding ownership/admin checks and basename sanitization.
- **Security**: Add missing POSIX `--` delimiter in `app/utils/images.py` for subprocess calls to prevent command injection.
- **Ontology**: Update `docs/ontology/iqoqo.ttl` and `docs/ontology/iqoqo-shapes.ttl` for `boardgame_mechanics` and `social.feedback_comments`.

## Capabilities

### New Capabilities

- `pr-258-fixes`: Comprehensive security, stability, and ontology fixes corresponding to the 0.7.16 PR reviews.

### Modified Capabilities

## Impact

- Database migrations (must handle SQLite safely)
- API endpoint `GET /api/feedback/...`
- Docker setup and SRE scripts
- Ontology definitions

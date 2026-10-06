## Context

PR #258 introduced several improvements but security and architectural reviews revealed specific missing protections and database migration constraints that must be resolved to ensure safe operation.

## Goals / Non-Goals

**Goals:**

- Eliminate IDOR on screenshot downloads.
- Protect subprocess calls from injection.
- Make Alembic migrations compatible with SQLite.
- Prevent Docker container entrypoint failure by managing rclone config permissions correctly.
- Add missing ontology definitions to support linked open data expansion.

**Non-Goals:**

- Completely rewriting the feedback API or data model.
- Refactoring the entire Docker setup beyond the `rclone` initialization.

## Decisions

- **SQLite Compatibility:** Wrap PostgreSQL specific DDL inside a check `if context.get_bind().dialect.name == "postgresql":`. This allows `flask db upgrade` to succeed on SQLite (which doesn't require these specific JSONB adjustments).
- **IDOR Prevention:** In `app/api/feedback.py`, after authenticating, we must query the database to verify the currently logged-in user (or admin) has access to the feedback ticket associated with the requested screenshot filename. We will extract the filename using `werkzeug.utils.secure_filename` or just basename extraction to prevent directory traversal.
- **Subprocess Hardening:** Append `--` to the `subprocess.run` arguments just before the user-supplied file path or URL in `app/utils/images.py` to stop argument injection.
- **N+1 Fix:** In `app/db/social.py`, change `FeedbackItem.comments` relationship to `lazy="selectin"` instead of `"dynamic"`. When `to_dict` is called, it will count the length of the loaded list rather than querying `.count()` on the relationship.

## Risks / Trade-offs

- **Risk:** Database dialect checks in Alembic migrations might be brittle if other dialects are introduced.
  - **Mitigation:** The codebase currently officially targets only PostgreSQL (production) and SQLite (testing/local), so this check is sufficient.

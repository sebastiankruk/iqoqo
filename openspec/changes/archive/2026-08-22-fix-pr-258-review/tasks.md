## 1. Environment & Infrastructure

- [x] 1.1 Update `deploy/Dockerfile` to set `ENV HOME=/home/appuser` before switching to `USER appuser`.
- [x] 1.2 Update `deploy/docker-entrypoint.sh` to create `${HOME}/.config/rclone` with `0700` permissions and ensure its config file has `0600` permissions if it is created/copied.
- [x] 1.3 Add `RCLONE_FEEDBACK_REMOTE` with a placeholder to `.env.example`.

## 2. API Security & Hardening

- [x] 2.1 Update `app/api/feedback.py` screenshot download endpoint to ensure the caller has permissions (ownership or admin) over the feedback ticket containing the requested file, and sanitize the filename.
- [x] 2.2 Update `app/utils/images.py` to append `--` before file paths in `subprocess.run` calls.

## 3. Database Updates

- [x] 3.1 Update Alembic migration `f65648a6aaf4_add_feedback_comments_schema.py` to wrap PostgreSQL DDL operations inside a `if context.get_bind().dialect.name == "postgresql":` block.
- [x] 3.2 Update `app/db/social.py` `FeedbackItem.comments` relationship to use `lazy="selectin"` and adjust `to_dict()` logic to calculate length from the loaded list.

## 4. Ontology Definitions

- [x] 4.1 Update `docs/ontology/iqoqo.ttl` to include `skos:Concept` mappings for `boardgame_mechanics` and the property `iqoqo:has_mechanic`.
- [x] 4.2 Update `docs/ontology/iqoqo.ttl` and `docs/ontology/iqoqo-shapes.ttl` to map feedback comments to `sioc:Post` and `sioc:Thread`.

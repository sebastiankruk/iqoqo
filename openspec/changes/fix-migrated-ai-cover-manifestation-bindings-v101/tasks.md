## 1. AI Cover Binding Diagnostic & Repair Script

- [ ] 1.1 Create `scripts/verify_ai_cover_bindings.py` using SQLAlchemy 2.0 `select(Manifestation)` pagination (`LIMIT`/`OFFSET`) to inspect AI-generated `cover_url` bindings against `Manifestation.isbn13`, `Manifestation.id`, and `Item.manifestation_id`.
- [ ] 1.2 Implement `--dry-run` (default diagnostic table output) and `--apply` (unbinds mismatched `cover_url`, logs to `EntityAuditLog`, and optionally queues fresh cover resolution) with `FLASK_ENV=production` interactive confirmation guard.
- [ ] 1.3 Add `fix-ai-covers` target to `Makefile` respecting `IQOQO_AI_MODE=1`.

## 2. Verification & Tests

- [ ] 2.1 Author unit and integration tests in `tests/scripts/test_verify_ai_cover_bindings.py` reproducing a post-migration `item_<wrong_id>_gemini.jpg` / mismatched ISBN binding and verifying both `--dry-run` detection and `--apply` repair.
- [ ] 2.2 Run `IQOQO_AI_MODE=1 make lint` and `IQOQO_AI_MODE=1 make test`.

## 1. Backend Serialization & Normalization

- [ ] 1.1 Add `normalize_authors_list` in `app/core/frbr_service.py` to convert strings, stringified JSON, and lists into sanitized `list[str]`; verify with pytest in `tests/test_frbr_author_normalization.py`
- [ ] 1.2 Update `app/api/manifestations.py` to use `normalize_authors_list` for all author serialization; verify that manifestation loads successfully even with malformed author meta
- [ ] 1.3 Ensure `update_work` synchronizes `work.meta["authors"]` with `WorkContribution` rows; verify with roundtrip update test

## 2. Data Repair & Frontend Layout

- [ ] 2.1 Implement `scripts/repair_frbr_authors.py` with `--dry-run` and `--apply` flags to sanitize legacy author JSONB values; verify script against test fixture database
- [ ] 2.2 Fix level selector CSS container styling in `frontend/components/admin/frbr-editor.tsx` to align cleanly with the editor boundary; verify layout via Vitest/RTL
- [ ] 2.3 Verify author editing in FRBR editor and subsequent manifestation loading end-to-end

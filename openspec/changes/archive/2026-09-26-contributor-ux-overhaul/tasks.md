## 1. Backend Name Capitalization & Structured Agent Parsing

- [x] 1.1 Implement `normalize_contributor_name` in `app/core/frbr_service.py` to normalize whitespace, format multi-word and hyphenated names, capitalize initials, and preserve interior lowercase cultural particles ("van", "von", "de", "da", "del", "di", "le", "la"), verifying with unit tests in `tests/test_frbr_events.py`
- [x] 1.2 Implement `parse_agent_input` in `app/core/frbr_service.py` to parse structured list-of-dicts and legacy string payloads into normalized `{"name": str, "role": str, "sequence": int}` contributor dicts, verifying with pytest in `tests/test_frbr_events.py`
- [x] 1.3 Implement `sync_entity_contributions` in `app/core/frbr_service.py` to reconcile and persist `WorkContribution`, `ExpressionContribution`, and `ManifestationContribution` rows, and integrate into `update_work`, `update_expression`, and `update_manifestation`, verifying with unit tests in `tests/test_frbr_events.py`

## 2. Admin API Contributor Integration

- [x] 2.1 Update `get_frbr_tree` in `app/api/admin.py` to serialize entity contributions into `data.work.contributions`, `data.expression.contributions`, and `data.manifestation.contributions` with fallback to legacy `meta` fields, verifying with `pytest tests/test_admin_frbr.py`
- [x] 2.2 Update `update_work`, `update_expression`, and `update_manifestation` endpoints in `app/api/admin.py` to accept structured `contributions` and invoke `sync_entity_contributions`, verifying with endpoint tests in `tests/test_admin_frbr.py`
- [x] 2.3 Run backend test suite via `pytest tests/test_admin_frbr.py tests/test_frbr_events.py` to verify contribution persistence and backward compatibility

## 3. Frontend Contributor Form Rows & Name Normalization

- [x] 3.1 Implement client-side `normalizeContributorName` helper in `frontend/components/admin/frbr-editor.tsx` matching backend capitalization rules, verifying formatting with unit tests in `frontend/__tests__/components/admin/frbr-editor.test.tsx`
- [x] 3.2 Update API client interfaces in `frontend/lib/api/admin.ts` to include structured `contributions` on `FrbrTree`, `WorkFormData`, `ExpressionFormData`, and `ManifestationFormData`, verifying with `npm --prefix frontend run type-check`
- [x] 3.3 Replace JSON textareas and dynamic metadata inputs with structured contributor rows (Role dropdown scoped by FRBR level, Agent Name input with onBlur normalization, add/remove row controls) in `FrbrEditor` (`frontend/components/admin/frbr-editor.tsx`), verifying with component tests in `frontend/__tests__/components/admin/frbr-editor.test.tsx`

## 4. End-to-End Verification & Change Validation

- [x] 4.1 Run frontend test suite, linting, and type checking via `npm --prefix frontend run test && npm --prefix frontend run lint && npm --prefix frontend run type-check` to verify zero regressions
- [x] 4.2 Validate OpenSpec change compliance and schema consistency by running `openspec validate contributor-ux-overhaul`

## 1. Backend Bug Fixes

- [x] 1.1 Add `kind` parameter to `PUT /api/admin/frbr/expression/{id}` in `app/api/admin.py`: read `data.get("kind")` and pass it to `frbr_service.update_expression()`. Map empty string `""` to `None` (studio/default). Preserve existing behavior when `kind` is absent from the request body.
- [x] 1.2 Add `"change_type"` to the accepted `request_type` set in `_validate_escalation_input()` in `app/api/social.py` so the existing `change_type` handler at line 559 becomes reachable.

## 2. Backend Tests

- [x] 2.1 Add pytest: `PUT /api/admin/frbr/expression/{id}` with `{"kind": "live_performance"}` updates the Expression's kind and returns success.
- [x] 2.2 Add pytest: `PUT /api/admin/frbr/expression/{id}` with `{"kind": ""}` clears the Expression's kind to `None`.
- [x] 2.3 Add pytest: `PUT /api/admin/frbr/expression/{id}` without `kind` key leaves existing kind unchanged.
- [x] 2.4 Add pytest: escalation submission with `request_type: "change_type"` passes validation and stores the request.
- [x] 2.5 Add pytest: `PUT /api/admin/frbr/expression/{id}` with invalid `kind` value returns error with valid values listed.

## 3. Frontend Expression Kind Dropdown

- [x] 3.1 Add `kind?: string` to the `Expression` interface in `frontend/types/frbr.ts`.
- [x] 3.2 Add `EXPRESSION_KINDS` constant (or import from generated taxonomy types) and render a `<select>` dropdown for `kind` on the Expression tab of `frontend/components/admin/frbr-editor.tsx`, populated with all valid kinds plus an empty "Studio / Default" option. Pre-select the current value. Include `kind` in the form submission payload.
- [x] 3.3 Add frontend Vitest/RTL test: kind dropdown renders with correct options, pre-selects current value, and includes `kind` in the submitted payload.

## 4. Cleanup

- [x] 4.1 Remove `scripts/fix_manifestation_1984.py` and its test file `tests/test_data_correction.py` (the correction is superseded by the general type-change mechanism).

## 5. Validation

- [x] 5.1 Run `make lint` and confirm all checks pass.
- [x] 5.2 Run backend pytest suite (`make test-backend-unit`) and confirm no regressions.
- [x] 5.3 Run frontend Vitest suite (`make test-frontend-unit`) and confirm no regressions.
- [x] 5.4 Verify on dev instance: admin can set `expression.kind` to `live_performance` via the FRBR editor UI and the change persists.

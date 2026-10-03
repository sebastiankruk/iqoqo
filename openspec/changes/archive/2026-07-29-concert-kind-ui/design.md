## Context

Release 0.7.13 (PR #176) built the complete backend for concert modeling:

- `Expression.kind` column exists with `live_performance` in the controlled vocabulary
- `frbr_service.update_expression()` accepts `kind` and validates it against `EXPRESSION_KINDS`
- `frbr_service.is_live_performance()` helper exists
- Concert ingestion detection auto-creates `Expression(kind='live_performance')` with Performance Event contributions
- `update_frbr_entity_type()` handles content-type propagation with upward/downward sync

The FRBR UI type change (frbr-ui-type-change) added a `content_type` dropdown to the editor and a `change_type` escalation route. However, three gaps prevent anyone from setting `expression.kind`:

1. `app/api/admin.py` `update_expression` endpoint receives `data.get("kind")` but never passes it to the service function. The `kind` parameter is silently dropped.
2. `app/api/social.py` `_validate_escalation_input()` rejects `change_type` — only `correction` and `deletion` are accepted. The handler for `change_type` exists downstream (line 559) but is unreachable dead code.
3. `frbr-editor.tsx` has no `kind` field — the editor only exposes `content_type` changes. The expression-kind vocabulary (studio vs live_performance) is invisible to the UI.

## Goals / Non-Goals

**Goals:**

- Admins can set `expression.kind` via `PUT /api/admin/frbr/expression/{id}` with `{"kind": "live_performance"}`.
- Non-admin users can request type changes through the escalation system (the `change_type` request type works end-to-end).
- The FRBR editor shows a `kind` dropdown next to the existing `content_type` dropdown on the Expression tab, populated from `EXPRESSION_KINDS`.
- Remove `scripts/fix_manifestation_1984.py` — superseded by the general type-change mechanism.

**Non-Goals:**

- No changes to `frbr_service.py` — the service layer already supports `kind` correctly.
- No changes to concert ingestion detection — auto-detection at ingest time is already wired.
- No changes to facet computation or badges — they read `expression.kind` already.
- No new expression kinds (only `live_performance` from `EXPRESSION_KINDS` is exposed).

## Decisions

1. **Pass `kind` through the admin endpoint, not add a separate route.** The existing `PUT /api/admin/frbr/expression/{id}` already handles `work_id`, `content_type`, `language`, `meta`. Adding `kind` to the same endpoint is the minimal, correct fix. Alternative considered: separate `PUT /frbr/expression/{id}/kind` route — rejected as unnecessary API surface duplication.

2. **Accept `change_type` in escalation validation.** The `_validate_escalation_input()` function hardcodes `{"correction", "deletion"}`. Adding `"change_type"` to the set is a one-word fix. Alternative considered: add a separate `kind_change` request type — rejected; `change_type` already covers entity type changes including `content_type` and `kind`.

3. **Kind dropdown parallels content_type dropdown in the Expression tab.** The `frbr-editor.tsx` already renders a `<select>` for `content_type` on the Expression tab. Adding a second `<select>` for `kind` (populated from a constant) follows the exact same pattern. The dropdown shows `""` (empty string = studio/default) and each valid kind. Alternative considered: radio buttons or a toggle — rejected; a dropdown is consistent with the existing UI pattern and scales when more kinds are added.

4. **Remove fix_manifestation_1984.py at release time, not in this change.** The script is a one-off correction for a specific production record. It was needed before the general type-change mechanism existed. With `update_frbr_entity_type` and the escalation system working, the same correction can be done through the UI. The script should be removed from the release branch before merge to `main`, not kept as permanent tooling.

## Risks / Trade-offs

- [Risk] Admin sets `kind` on an Expression whose child Manifestations have conflicting content types. → Mitigation: `kind` and `content_type` are independent axes. A concert CD (`content_type=Music`, `kind=live_performance`) and a concert BluRay (`content_type=Movie`, `kind=live_performance`) are both valid. The service layer does not enforce cross-field validation because FRBR allows these combinations. This is documented in the frbr-ontology spec.
- [Risk] Clearing `kind` (setting to `""`) is ambiguous with setting it to `null`. → Mitigation: The admin endpoint maps `""` to `None` (studio), and the frontend dropdown shows an explicit "Studio / Default" option with value `""`.
- [Risk] The escalation handler for `change_type` assumes `suggested_value` is a content type string, not a kind string. → Mitigation: The `_handle_type_change_acceptance` handler currently calls `update_frbr_entity_type` which handles content types. For `kind` changes, the escalation payload uses `correction` type with `field_name: "kind"` and `suggested_value: "live_performance"` — the standard metadata correction path handles it.

## Migration Plan

1. Apply the code fixes on the `release/0.7.13` branch (admin.py, social.py, frbr-editor.tsx).
2. Add backend tests and frontend tests.
3. Remove `scripts/fix_manifestation_1984.py`.
4. Verify PR #176 CI passes.
5. Merge release/0.7.13 to main.

## Open Questions

- None. All decisions are grounded in the existing code patterns from release-0-7-13 and frbr-ui-type-change.

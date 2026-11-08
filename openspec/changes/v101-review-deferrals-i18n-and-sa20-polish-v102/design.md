# Design: v1.0.1 Review Deferrals — React Hook Test Wrappers, LEGO/Maps i18n, SQLAlchemy 2.0 & Config Hygiene (`C111` — Target: `v1.0.2`)

## Context

This change groups the 5 Low-severity (`🟢 LOW`) findings (`L-01`–`L-05`) from the `v1.0.1` Principal Code Review into a clean, self-contained `v1.0.2` polish batch (`C111`).

## Technical Decisions

1. **React Rules of Hooks Compliance (`L-01`)**:
   - Call `const createEscalation = useCreateNewMediaTypeEscalation();` unconditionally at the top of `RequestNewTypeModal`.
   - Update unit tests that render `RequestNewTypeModal` (directly or via `ManualEntryForm` / `HelpContent`) to provide a `QueryClientProvider` test harness.
2. **Bilingual EN/PL Translation Keys (`L-02`)**:
   - Add namespaces `ItemDetail.lego`, `ItemDetail.maps`, `MapViewer`, and `Escalation.newMediaType` to both `frontend/messages/en.json` and `frontend/messages/pl.json` with 100% key parity.
3. **SQLAlchemy 2.0 `select()` Syntax (`L-03`)**:
   - Replace remaining `.query` calls in `app/api/manifestations.py`, `app/api/scanner.py`, and `app/api/social.py` with `db.session.execute(select(...))`.
4. **Scoped `sanitize_credential_string` (`L-04`)**:
   - Apply quote unwrapping in `ConfigService.get()` only when the key belongs to `SENSITIVE_SETTING_KEYS` or matches credential naming conventions, preserving raw JSON strings untouched.
5. **Test Lint Cleanup (`L-05`)**:
   - Remove the unused `nextIntl` binding in `frontend/__tests__/components/i18n-provider.test.tsx:20`.

## MODIFIED Requirements

### Requirement: React Hook Compliance, Bilingual EN/PL i18n Parity, SQLAlchemy 2.0 Queries, and Scoped Credential Quote Stripping (`L-01`–`L-05`)

The deferred `v1.0.1` Low-severity findings MUST be resolved in `v1.0.2` (`C111`).

#### Scenario: `RequestNewTypeModal` calls hooks unconditionally (`L-01`)

- **GIVEN** `frontend/components/social/request-new-type-modal.tsx`
- **WHEN** `RequestNewTypeModal` renders inside a `QueryClientProvider`
- **THEN** `useCreateNewMediaTypeEscalation()` MUST be invoked at the top level of the component without a `try / catch` wrapper or `react-hooks/rules-of-hooks` suppression.

#### Scenario: Bilingual EN/PL translation coverage for LEGO, Maps, and New Media Type components (`L-02`)

- **GIVEN** a user viewing LEGO details, Cartographic Maps, Map Viewer Modal, or New Media Type escalation UI with locale set to `"pl"` or `"en"`
- **WHEN** the components render
- **THEN** all user-visible labels MUST resolve through `next-intl` translation keys present in both `frontend/messages/en.json` and `frontend/messages/pl.json`.

#### Scenario: SQLAlchemy 2.0 `select()` queries and scoped credential sanitization (`L-03`, `L-04`)

- **GIVEN** `app/api/manifestations.py`, `app/api/scanner.py`, `app/api/social.py`, and `app/core/config_service.py`
- **WHEN** database queries execute or non-credential settings (such as keys ending in `_URL`, `_DATA`, or non-client `_ID`) are fetched from `ConfigService.get()`
- **THEN** queries MUST use SQLAlchemy 2.0 `select()` syntax and `is_credential_or_sensitive_key()` MUST only match `is_sensitive_key(key)`, `SENSITIVE_SETTING_KEYS`, or keys ending with `("_KEY", "_SECRET", "_TOKEN", "_PASSWORD", "_CLIENT_ID")`.

# Proposal: v1.0.1 Review Deferrals — React Hook Test Wrappers, LEGO/Maps i18n, SQLAlchemy 2.0 & Config Hygiene (`C111` — Target: `v1.0.2`)

## Why

During the unified Principal & Gemini Release Review of `v1.0.1` (`.context/notes/review/1.0.1/principal-full-release-1.0.1-review.md` and `.context/notes/review/1.0.1/review-release-1.0.1-pr-405.md`), 7 Low-severity (`🟢 LOW`) quality, i18n, RDF, and code-style findings (`L-01`–`L-07`) were identified and intentionally postponed to **`v1.0.2`** so `v1.0.1` focuses strictly on Critical and Moderate functional/security fixes:

1. **`L-01` (React Rules of Hooks)**: `frontend/components/social/request-new-type-modal.tsx:76-82` wraps `useCreateNewMediaTypeEscalation()` inside a `try / catch` block with `// eslint-disable-next-line react-hooks/rules-of-hooks` to tolerate unit tests that mount the modal without a `QueryClientProvider`.
2. **`L-02` (i18n Completeness)**: Newly introduced `v1.0.1` components (`ExtendedMetadataLego`, `ExtendedMetadataMaps`, `MapViewerModal`, `EscalationQueue`, `MyEscalations`, and `ManualEntryForm`) contain hardcoded English labels instead of `next-intl` translation keys in `frontend/messages/{en,pl}.json`.
3. **`L-03` (SQLAlchemy 2.0 Modernization)**: Legacy `Model.query` / `db.session.query()` calls remain in touched `v1.0.1` routes (`app/api/manifestations.py`, `app/api/social.py`, `app/api/scanner.py`).
4. **`L-04` (`ConfigService` Quote Sanitization Scope)**: `ConfigService.get()` (`app/core/config_service.py`) calls `sanitize_credential_string()` on all string values rather than scoping quote-stripping to sensitive/credential keys or non-JSON strings.
5. **`L-05` (Test Lint Hygiene)**: Unused `nextIntl` variable warning in `frontend/__tests__/components/i18n-provider.test.tsx:20`.
6. **`L-06` (RDF Export Hygiene)**: Triplicated LEGO RDF triple emission blocks and double-slash relative `mapImageUrl` (`f"{base_url}/{safe_img}"`) in `build_collection_rdf_graph` (`app/core/frbr_service.py`).
7. **`L-07` (Help Header CTA & Roadmap Checkboxes)**: Ensure `<RequestNewTypeModal />` is accessible from `/help` header and tick off `[x]` for completed `v1.0.1` items in `.context/notes/iqoqo roadmap.md` and `.context/notes/iqoqo development notes.md`.

## What Changes

- **Unconditional Hook Call in `RequestNewTypeModal` (`L-01`)**: Remove the `try / catch` wrapper and `eslint-disable` comment around `useCreateNewMediaTypeEscalation()` in `frontend/components/social/request-new-type-modal.tsx`, and wrap unit test renders in a test `QueryClientProvider`.
- **Full EN/PL `next-intl` Extraction for LEGO, Maps & New Media Type UI (`L-02`)**: Extract hardcoded English strings in `extended-metadata-lego.tsx`, `extended-metadata-maps.tsx`, `map-viewer-modal.tsx`, `escalation-queue.tsx`, `my-escalations.tsx`, and `manual-entry-form.tsx` into `frontend/messages/en.json` and `frontend/messages/pl.json`.
- **SQLAlchemy 2.0 `select()` Migration in Touched Routes (`L-03`)**: Replace `Item.query`, `Manifestation.query`, and `db.session.query(User)` in `app/api/manifestations.py`, `app/api/scanner.py`, and `app/api/social.py` with `db.session.execute(select(...))`.
- **Scoped Credential Quote Sanitization (`L-04`)**: Scope `sanitize_credential_string()` in `app/core/config_service.py` to credential keys (`SENSITIVE_SETTING_KEYS` / `*_KEY` / `*_SECRET` / `*_TOKEN` / `*_ID` / `*_URL`) so structured JSON strings are never touched.
- **Clean Up Unused Test Import (`L-05`)**: Remove unused `nextIntl` declaration in `frontend/__tests__/components/i18n-provider.test.tsx:20`.

## Impact

- Target release: **`v1.0.2`** (`C111`).
- Affected specs: `v101-review-deferrals-and-polish`.
- Affected code (`v1.0.2`): `frontend/components/social/request-new-type-modal.tsx`, `frontend/components/item/extended-metadata-lego.tsx`, `frontend/components/item/extended-metadata-maps.tsx`, `frontend/components/item/map-viewer-modal.tsx`, `frontend/components/admin/escalation-queue.tsx`, `frontend/components/escalation/my-escalations.tsx`, `frontend/components/scanner/manual-entry-form.tsx`, `frontend/messages/{en,pl}.json`, `app/api/manifestations.py`, `app/api/scanner.py`, `app/api/social.py`, `app/core/config_service.py`, `frontend/__tests__/components/i18n-provider.test.tsx`.

# Tasks: v1.0.1 Review Deferrals (`C111` — Target: `v1.0.2`)

## 1. Frontend Hook, i18n & Test Polish (`L-01`, `L-02`, `L-05`)

- [x] 1.1 **`L-01`**: Remove `try / catch` around `useCreateNewMediaTypeEscalation()` in `frontend/components/social/request-new-type-modal.tsx` and wrap affected unit tests in `QueryClientProvider`.
- [x] 1.2 **`L-02`**: Extract hardcoded English UI strings in `extended-metadata-lego.tsx`, `extended-metadata-maps.tsx`, `map-viewer-modal.tsx`, `escalation-queue.tsx`, `my-escalations.tsx`, and `manual-entry-form.tsx` into `frontend/messages/en.json` and `frontend/messages/pl.json`.
- [x] 1.3 **`L-05`**: Remove unused `nextIntl` variable in `frontend/__tests__/components/i18n-provider.test.tsx:20`.

## 2. Backend SQLAlchemy 2.0, RDF Export & ConfigService Polish (`L-03`, `L-04`, `L-06`, `L-07`)

- [x] 2.1 **`L-03`**: Replace legacy `.query` / `db.session.query()` calls in `app/api/manifestations.py`, `app/api/scanner.py`, and `app/api/social.py` with SQLAlchemy 2.0 `select()` statements.
- [x] 2.2 **`L-04`**: Scope `sanitize_credential_string()` in `app/core/config_service.py` to credential/secret keys.
- [x] 2.3 **`L-06`**: Deduplicate LEGO/Cartographic RDF triple helper in `build_collection_rdf_graph` (`app/core/frbr_service.py`) and strip leading `/` when joining relative `mapImageUrl` / `cover_url` onto `base_url`.
- [x] 2.4 **`L-07`**: Ensure `<RequestNewTypeModal />` is mounted on `/help` and tick off `[x]` for completed `v1.0.1` checkboxes in `.context/notes/iqoqo roadmap.md` and `.context/notes/iqoqo development notes.md`.

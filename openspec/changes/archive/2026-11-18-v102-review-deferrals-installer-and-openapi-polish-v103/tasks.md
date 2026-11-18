# Tasks: v1.0.2 Review Deferrals (`C117` — Target: `v1.0.3`)

## 1. Installer, CI Packaging & `iqopresync` Polish (`L-01`, `L-02`, `L-03`)

- [x] 1.1 **`L-01` (`scripts/install.sh`)**: Remove `"feat/c110-store-submission-lts-audit-v102"` from `FALLBACK_BRANCHES` in `scripts/install.sh` line 89. Verify with `make lint`.
- [x] 1.2 **`L-02` (`.github/workflows/mobile-build.yml`)**: Add optional secret-gated Android/iOS release signing steps and standalone `scripts/iqoqo_installer.py` + `sha256sum` artifact packaging in GitHub Actions. Verify with `tests/test_infra_config.py`.
- [x] 1.3 **`L-03` (`scripts/iqoqo_installer.py`)**: Percent-encode `pg_pass` via `urllib.parse.quote(pg_pass, safe="")` when constructing `DATABASE_URL` in `configure_env_content()`, and add `/api/system/status` and `/.well-known/webfinger` probes to `run_presync_check()`. Verify with unit tests in `tests/scripts/test_iqoqo_installer.py`.

## 2. OpenAPI 3.1 Schema, Changelog & Offline Collection Filter Polish (`L-04`, `L-05`)

- [x] 2.1 **`L-04` (`app/api/docs.py`)**: Add `q`, `collection_status`, `format`, and `item_id` query parameter definitions to `GET /api/v1/admin/ownership/items` in `app/api/docs.py`. Verify with `tests/test_openapi_contract_completeness.py`.
- [x] 2.2 **`L-05` (`docs/CHANGELOG.md`, `frontend/messages/{en,pl}.json`, `frontend/app/collection/page.tsx`)**: Replace `FEDERATION_READ_ONLY_HEAD` with `FEDERATION_HEAD_MODE` in `docs/CHANGELOG.md` line 16, remove unused `Navbar.federationHubBanner` / `Navbar.federationHubExploreDirectory` / `Navbar.dismissBanner` keys from `en.json` and `pl.json`, and add `collectionFilters` matching to the offline predicate in `frontend/app/collection/page.tsx`. Verify with `IQOQO_AI_MODE=1 make lint` and `IQOQO_AI_MODE=1 make test-parallel`.

## Purpose

Resolve the 5 Low-severity (`L-01`–`L-05`) findings deferred from the `v1.0.2` Principal + Gemini Argon release audit (`C117`), covering bootstrap installer fallback branch hygiene, optional secret-gated CI signing and installer checksum packaging, `iqopresync` `/api/system/status` and WebFinger probes with URL-safe `DATABASE_URL` password encoding, OpenAPI 3.1 query parameter documentation for `GET /api/v1/admin/ownership/items`, and `CHANGELOG.md` / offline `collectionFilters` polish.

## ADDED Requirements

### Requirement: Installer Bootstrap Hygiene, URL-Encoded `DATABASE_URL`, and Extended `iqopresync` Probes (`L-01`, `L-02`, `L-03`)

The standalone bootstrap installer (`scripts/install.sh`), CLI wizard (`scripts/iqoqo_installer.py`), and CI workflows SHALL reference only canonical release branches, URL-encode special characters in `POSTGRES_PASSWORD` when constructing `DATABASE_URL`, probe `/api/system/status` and `/.well-known/webfinger` during `--presync-check`, and include optional secret-gated signing and installer checksum steps in GitHub Actions.

#### Scenario: Preserved `POSTGRES_PASSWORD` with special characters is safely URL-encoded (`L-03`)

- **GIVEN** an existing `.env` containing a `POSTGRES_PASSWORD` with URI-reserved characters (such as `@`, `:`, or `/`)
- **WHEN** `configure_env_content()` generates `DATABASE_URL` without rotating secrets
- **THEN** the password segment in `DATABASE_URL` MUST be percent-encoded via `urllib.parse.quote(pg_pass, safe="")`.

#### Scenario: `scripts/install.sh` fallback list excludes temporary feature branches (`L-01`)

- **GIVEN** `scripts/install.sh`
- **WHEN** `FALLBACK_BRANCHES` is inspected
- **THEN** it MUST only reference canonical release/main branches (`"main"`, `"release/1.0.2"`) and MUST NOT contain temporary feature branch names.

### Requirement: OpenAPI 3.1 Query Parameter Contract & Offline Collection Filter Parity (`L-04`, `L-05`)

The OpenAPI 3.1 specification (`app/api/docs.py`) SHALL document `q`, `collection_status`, `format`, and `item_id` query parameters on `GET /api/v1/admin/ownership/items`, `docs/CHANGELOG.md` SHALL reference `FEDERATION_HEAD_MODE`, and `/collection` offline filtering SHALL evaluate active `collection` filters locally.

#### Scenario: Inspecting OpenAPI 3.1 specification for ownership source items (`L-04`)

- **GIVEN** the generated OpenAPI 3.1 specification from `app/api/docs.py`
- **WHEN** `GET /api/v1/admin/ownership/items` parameters are inspected
- **THEN** `source_user_id`, `page`, `limit`, `q`, `collection_status`, `format`, and `item_id` are all declared in the operation parameter list.

## ADDED Requirements

### Requirement: Expression-Kind and Mixed-Media Concert Filtering in Shared Collections

All shared collection delivery surfaces (`GET /api/public/share/<token>`, `GET /share/<token>`, `GET /share/<token>/jsonld/<page>`, `GET /api/public/rdf/share/<token>`, RSS feeds, and wishlist `UserWorkIntent` projections) SHALL support `SharedCollection.filters["expression_kind"]` (`"live_performance"`, `"studio"`) alongside `tags`/`category`, `format`, `status`, and `query`. Empty `expression_kind: []` arrays MUST fail closed (returning zero items). When `filters["expression_kind"]` includes `"live_performance"` without a single-category restriction (or with `category`/`tags` spanning both `"music"` and `"movie"`), shared collections SHALL return both audio (`cd`, `vinyl`, `cd_dvd_combo`, `bluray_audio`, etc.) and video (`dvd`, `bluray`, `4k_uhd`, `vcd`, `vhs`, etc.) concert releases while excluding studio/non-concert items. Genuine multi-carrier formats (`cd_dvd_combo`) SHALL satisfy both `"music"` and `"movie"` category-filtered shares via `MIXED_MEDIA_FORMAT_CATEGORIES`, while single-carrier video formats (`dvd`, `bluray`, `vcd`, etc.) MUST remain excluded from pure `"music"`-only shares.

#### Scenario: Concert-filtered share includes both movie Blu-ray and audio CD concerts across JSON, JSON-LD, RDF, and RSS

- **GIVEN** User A owns a public live concert Blu-ray (`movie` / `live_performance` / `bluray`), a public live concert CD (`music` / `live_performance` / `cd`), a public studio CD (`music` / `NULL` / `cd`), and a public feature film DVD (`movie` / `NULL` / `dvd`), and creates a `SharedCollection` with `filters={"expression_kind": ["live_performance"]}`
- **WHEN** any caller fetches `/api/public/share/<token>`, `/share/<token>/jsonld/1`, `/api/public/rdf/share/<token>?format=turtle`, or `/api/public/share/<token>/feed.xml`
- **THEN** both the concert Blu-ray and the concert CD MUST be returned, and the studio CD and feature film DVD MUST be excluded

#### Scenario: Combined music+movie live_performance share excludes books and studio releases

- **GIVEN** User A creates a `SharedCollection` with `filters={"tags": ["music", "movie"], "expression_kind": ["live_performance"]}`
- **WHEN** shared items (including PostgreSQL FTS `query` searches and `UserWorkIntent` wishlist entries) are resolved
- **THEN** both audio and video live concerts MUST be included, while books, board games, studio albums, and non-concert movies MUST be excluded

#### Scenario: Empty expression_kind filter fails closed

- **GIVEN** a `SharedCollection` stores `filters={"expression_kind": []}`
- **WHEN** any share delivery surface evaluates the collection
- **THEN** zero items MUST be returned

#### Scenario: Pure music share still excludes single-carrier movie concert DVD while retaining cd_dvd_combo

- **GIVEN** User A owns a `cd_dvd_combo` concert (`music` / `live_performance` / `cd_dvd_combo`) and a single-carrier concert `dvd` (`movie` / `live_performance` / `dvd`), and creates a `SharedCollection` with `filters={"tags": ["music"]}`
- **WHEN** the share is evaluated
- **THEN** the `cd_dvd_combo` MUST be included and the single-carrier `dvd` MUST be excluded (whereas a share with `filters={"tags": ["movie"]}` includes both the `dvd` and the multi-carrier `cd_dvd_combo`)

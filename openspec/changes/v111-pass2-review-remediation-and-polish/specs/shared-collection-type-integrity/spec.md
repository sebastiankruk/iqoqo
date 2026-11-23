## MODIFIED Requirements

### Requirement: UserWorkIntent Wishlist Media-Type and Format Filtering Parity

When `SharedCollection.filters["status"]` includes `"wish_list"` or intent-level statuses (`want_to_read`, `want_to_listen`, `want_to_watch`, `want_to_play`, `want_to_build`), the share query pipeline SHALL apply the same normalized category (`tags`/`category`), carrier format (`format` including `include_null_fmt` support), `excluded_formats` (`FORMAT_TO_CATEGORY` consistency guard), and `query` filters to `UserWorkIntent` entries—constraining the `Expression`/`Manifestation` correlation strictly to `UserWorkIntent.expression_id` and `UserWorkIntent.manifestation_id` when bound (falling back to any expression/manifestation of the parent `Work` only when unbound), preserving conceptual F1/F2 `UserWorkIntent` entries whose `Work`/bound `Expression` has zero `Manifestation` rows when no explicit non-null `format` filter is active (or when `include_null_fmt` is true), and SHALL serialize `content_type` and `format` on returned wishlist items across JSON and JSON-LD/RDF projections.

#### Scenario: Music wishlist share excludes movie DVD and audiobook intents

- **GIVEN** User A has non-hidden `UserWorkIntent` records for a music `Work` (`want_to_listen`, `vinyl`), a movie DVD `Work` (`want_to_watch`, `dvd`), and an audiobook `Work` (`want_to_listen`, `audiobook_cd`)
- **WHEN** a `SharedCollection` with `filters={"status": ["wish_list"], "tags": ["music"]}` is requested
- **THEN** only the music `Work` intent MUST be returned, with top-level `content_type: "music"` and `format: "vinyl"`, while the movie DVD and audiobook intents MUST be excluded.

#### Scenario: Intent bound to a specific Manifestation filters by that Manifestation's format

- **GIVEN** a `Work` with both a `cd` manifestation and a `vinyl` manifestation (or a movie `dvd` manifestation and a music `cd` manifestation), and a `UserWorkIntent` bound via `intent.manifestation_id` to the `vinyl` (or `dvd`) manifestation
- **WHEN** a `SharedCollection` with `filters={"status": ["want_to_listen"], "tags": ["music"], "format": ["cd"]}` is requested
- **THEN** that `vinyl`-bound (or `dvd`-bound) `UserWorkIntent` MUST be excluded by the SQL `sa.exists` predicate (and included only when the bound manifestation itself satisfies `tags`, `format`, `include_null_fmt`, and `excluded_formats`).

#### Scenario: Category-filtered wishlist share preserves unmanifested conceptual Work intents

- **GIVEN** User A has a non-hidden `UserWorkIntent` (`status="want_to_listen"`, `manifestation_id=None`) for a music `Work` that has an `Expression(content_type="music")` but zero `Manifestation` rows in the catalog
- **WHEN** a `SharedCollection` with `filters={"status": ["want_to_listen"], "tags": ["music"]}` (or `filters={"status": ["want_to_listen"], "tags": ["music"], "format": ["unknown_audio"]}`) is requested
- **THEN** the unmanifested music `UserWorkIntent` MUST be included in the response rather than dropped by the `excluded_formats` manifestation subquery.

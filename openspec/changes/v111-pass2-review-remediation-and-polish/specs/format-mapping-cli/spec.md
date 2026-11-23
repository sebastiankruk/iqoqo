## MODIFIED Requirements

### Requirement: Deterministic raw_payload carrier recovery and ambiguous unknown_audio backfill

Both the linear Alembic backfill migration (`v1_1_1_norm_legacy_formats.py`, off `v1_1_0_serial_issn_issues`) and `scripts/fix_physical_kinds.py --apply` SHALL inspect `Manifestation.raw_payload` (passing `content_type` context for MusicBrainz `media[*].format`, Discogs `formats`/`format`, OpenLibrary, TMDb, and Allegro carrier parameters) whenever format columns contain legacy generic format values (`"music"`, `"audio"`, `"sound"`, `"movie"`, `"video"`, `"moving image"`) OR when all three format columns (`format`, `format_type`, `meta['format']`) are `NULL`/blank and `raw_payload` is present. Furthermore, when only a subset of the three format columns is populated with a canonical value (e.g., `format = NULL, format_type = NULL, meta['format'] = "vinyl"`) OR when any format column contains mixed-case characters (e.g., uniform `"Vinyl"`, `"Vinyl"`, `"Vinyl"`), both the migration and `--apply` SHALL synchronize all three columns to the lowercased canonical value, and whenever an unambiguous video or text carrier (`"dvd"`, `"bluray"`, `"vcd"`, `"book"`) is resolved on a row whose parent `Expression.content_type` was mis-tagged as `"music"`, both the migration and `--apply` SHALL repair `Expression.content_type` to match `FORMAT_TO_CATEGORY[target_fmt]`.

#### Scenario: MusicBrainz or Discogs raw_payload recovers specific carrier on backfill

- **GIVEN** an existing `Manifestation` with either `meta['format'] = "audio"` OR all three format columns (`format`, `format_type`, `meta['format']`) set to `NULL`, and `raw_payload` containing Discogs `formats: [{"name": "Vinyl"}]` or MusicBrainz `media: [{"format": "CD"}]`
- **WHEN** the Alembic backfill migration or `scripts/fix_physical_kinds.py --apply` runs
- **THEN** `Manifestation.format`, `Manifestation.format_type`, and `Manifestation.meta['format']` MUST be updated to `"vinyl"` (or `"cd"` respectively).

#### Scenario: Single-column canonical format backfills remaining NULL format columns

- **GIVEN** an existing `Manifestation` with `format = NULL`, `format_type = NULL`, and `meta['format'] = "vinyl"` (or `format_type = "dvd"` and `format = NULL`), or with uniform mixed-case `"Vinyl"` across all three format fields
- **WHEN** the Alembic backfill migration or `scripts/fix_physical_kinds.py --apply` runs
- **THEN** `Manifestation.format`, `Manifestation.format_type`, and `Manifestation.meta['format']` MUST all be synchronized to lowercased `"vinyl"` (or `"dvd"`).

#### Scenario: Ambiguous music/audio/sound row without raw_payload normalizes to unknown_audio

- **GIVEN** an existing `Manifestation` with `meta['format']` in `{"music", "audio", "sound"}` and `raw_payload = NULL`
- **WHEN** the Alembic backfill migration or `scripts/fix_physical_kinds.py --apply` runs
- **THEN** `Manifestation.format`, `Manifestation.format_type`, and `Manifestation.meta['format']` MUST be updated to `"unknown_audio"` (NEVER `"cd"`), and audit/report output SHALL surface remaining `unknown_audio` counts for optional custodian review.

#### Scenario: Unambiguous video or book carrier recovery repairs mis-tagged Expression.content_type in both migration and CLI

- **GIVEN** an existing `Manifestation` under an `Expression` with `content_type = "music"` whose format or `raw_payload` resolves to `"dvd"`, `"bluray"`, `"vcd"`, or `"book"`
- **WHEN** the Alembic backfill migration or `scripts/fix_physical_kinds.py --apply` runs
- **THEN** `Manifestation.format`, `Manifestation.format_type`, and `Manifestation.meta['format']` MUST be synchronized to the canonical carrier and the parent `Expression.content_type` MUST be updated to `"movie"` (or `"text"` for `"book"`).

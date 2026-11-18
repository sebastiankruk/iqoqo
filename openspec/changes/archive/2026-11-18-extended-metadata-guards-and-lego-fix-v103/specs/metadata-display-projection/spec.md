## ADDED Requirements

### Requirement: Suppress Zero-Metadata Extended Section Cards

Extended metadata section cards (Video Details, Game Details, Puzzle Details, LEGO Set Details, Maps & Cartography, and Audio Release Information) SHALL NOT render an empty box containing zero displayable metadata fields or covers. Provider attribution badges (such as `TMDB`, `BGG`, or `IGDB`) SHALL NOT alone trigger rendering an otherwise empty section card.

#### Scenario: Video manifestation with TMDB source and no cast, directors, runtime, or meta cover

- **WHEN** a video manifestation has `Source: "TMDB"` and no non-empty `cast`, `directors`, `runtime`, or `meta.cover_url`
- **THEN** the `Video Details` section card is not rendered

#### Scenario: Board game, puzzle, or LEGO manifestation with zero section fields

- **WHEN** a board game (with `Source: "BGG"` or `"IGDB"`), puzzle, or LEGO manifestation has no non-empty section fields and no meta cover
- **THEN** its dedicated extended section card is not rendered

#### Scenario: Cartographic map manifestation with no map details and read-only viewer

- **WHEN** a manifestation has `format: "cartographic_map"` or `"atlas"` with no scale, projection, insert status, or attachments and the viewer cannot edit
- **THEN** the `Maps & Cartography` section card is not rendered

### Requirement: Strict Non-Empty LEGO Section Detection and Field Rendering

The extended metadata view SHALL NOT infer LEGO classification from `null`, empty string (`""`), or whitespace-only values on `set_number` or `piece_count`, and SHALL NOT infer LEGO classification from metadata keys when the manifestation format belongs to another explicit category (video, audio, board game, or puzzle). Individual LEGO tiles (such as Piece Count or Minifigures) SHALL NOT render when their resolved value is `null`, `undefined`, or blank.

#### Scenario: DVD movie carrying null or empty LEGO keys from retail lookup

- **WHEN** a manifestation has `format: "DVD"` (or `"video"`) and `meta` contains `"set_number": null, "piece_count": null` or `"set_number": "", "piece_count": ""`
- **THEN** the `LEGO Set Details` section card is not rendered

#### Scenario: Manifestation detail consumes server display projection

- **WHEN** the manifestation detail page renders extended metadata for an API response that includes `display`
- **THEN** `ManifestationDetailClient` forwards `display` to `ExtendedMetadata`, matching item detail behavior

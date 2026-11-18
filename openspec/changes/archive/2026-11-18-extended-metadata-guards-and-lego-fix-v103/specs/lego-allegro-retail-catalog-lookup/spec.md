## ADDED Requirements

### Requirement: Non-LEGO Allegro Normalization Omits Absent LEGO Fields

Allegro product and offer normalizers SHALL NOT emit `set_number`, `piece_count`, or `theme` keys with `None` values when those fields were not extracted. The `Kod producenta` 4–6 digit heuristic SHALL NOT classify non-LEGO products as having a LEGO `set_number` during preview format normalization unless LEGO context or `piece_count` is present, and scanner preview normalization SHALL check for truthy non-empty `set_number` / `set_num` values rather than key existence before coercing `format` to `standard_set`.

#### Scenario: Allegro returns a movie or book without LEGO parameters

- **WHEN** `_normalize_allegro_product` or `_normalize_allegro_offer` normalizes a DVD or book whose parameters lack LEGO set number, piece count, and theme
- **THEN** the returned dictionary omits `set_number`, `piece_count`, and `theme` instead of setting them to `None`

#### Scenario: Scanner preview normalizes metadata with null set_number

- **WHEN** `_normalize_preview_meta` receives metadata containing `"set_number": None` and `format: "movie"` (or `format_hint="movie"`)
- **THEN** it does NOT coerce `format` to `"standard_set"`

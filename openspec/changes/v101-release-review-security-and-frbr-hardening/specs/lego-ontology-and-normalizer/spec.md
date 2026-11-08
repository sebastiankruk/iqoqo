# Delta Specification: LEGO Ontology and Format Normalizer (`C108c`)

## ADDED Requirements

### Requirement: Enforce FRBR F5 vs F3 Boundary on Physical LEGO `Item` Edits (`C-04`)

Editing a physical LEGO `Item` (`PUT /api/items/<id>` / `EditItemDialog`) MUST persist Item-level physical copy state (`build_status`, `missing_pieces_count`, `instructions_included`, `box_condition`) strictly on `Item.meta` (F5) and MUST NEVER merge those fields into `Manifestation.meta` (F3).

#### Scenario: Updating LEGO item completeness does not pollute `Manifestation.meta`

- **GIVEN** a physical LEGO `Item` linked to a shared `Manifestation`
- **WHEN** `PUT /api/items/<item.id>` is called with `build_status="incomplete"`, `missing_pieces_count=4`, and `instructions_included=False` (or via `EditItemDialog`)
- **THEN** `item.meta` MUST store `build_status="incomplete"`, `missing_pieces_count=4`, and `instructions_included=False`
- **AND** `item.manifestation.meta` MUST NOT contain `build_status`, `missing_pieces_count`, or `instructions_included`.

### Requirement: Complete Unknown Format Placeholders in `FormatNormalizer` (`M-02`)

`FormatNormalizer._category_to_unknown_placeholder` and `FormatNormalizer._UNKNOWN_FORMATS` MUST include all 7 canonical media categories' `unknown_*` format constants (`unknown_text`, `unknown_audiobook`, `unknown_audio`, `unknown_video`, `unknown_board_game`, `unknown_puzzle`, `unknown_lego`).

#### Scenario: Expand unknown format filter for LEGO, Board Game, Puzzle, and Audiobook

- **GIVEN** `FormatNormalizer.expand_format_filter(["unknown_lego"])` or `_category_to_unknown_placeholder("board_game")`
- **WHEN** format normalization or filter expansion runs
- **THEN** `unknown_lego`, `unknown_board_game`, `unknown_puzzle`, and `unknown_audiobook` MUST be recognized as canonical unknown format placeholders for their respective categories.

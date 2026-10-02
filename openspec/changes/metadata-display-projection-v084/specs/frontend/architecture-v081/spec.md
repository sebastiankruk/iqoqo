## MODIFIED Requirements

### Requirement: Item Metadata Display Sections

The item detail page SHALL render manifestation metadata as a set of labelled sections — description, categories, media format, release information, and additional details — and SHALL derive which keys belong in a dedicated section from a single declared vocabulary rather than from a separately maintained suppression list. When the server supplies a display projection, the page SHALL render from that projection instead of re-deriving the layout from raw metadata. The page SHALL render each field exactly once across all sections.

#### Scenario: Rendering an audio manifestation

- **WHEN** a manifestation has `format` and a description
- **THEN** the format is shown in the release information section and the description in its own section, each appearing once

#### Scenario: Rendering with the projection supplied

- **WHEN** item detail is fetched with a display projection present
- **THEN** the sections are rendered from the projection's field order and labels

#### Scenario: Rendering without the projection supplied

- **WHEN** item detail is fetched without a display projection, such as against an older server
- **THEN** the page still renders all sections from the raw metadata, with each field appearing once

#### Scenario: A record mixes casing conventions

- **WHEN** one record carries `Format` and `Authors` while another carries `format` and `authors`
- **THEN** both render the same set of sections with the same labels, and neither shows a duplicated value
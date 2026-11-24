## ADDED Requirements

### Requirement: Consistent Above-the-Fold Localized Graph Entry Across Work, Expression, and Manifestation Pages

The frontend SHALL provide a consistent, `iqoqo-ux-auditor`-compliant top utility bar on `/work/[id]`, `/expression/[id]`, and `/manifestation/[id]` containing the `[← Back]` navigation control on the left and the secondary `"Explore Graph"` entry link (`data-testid="explore-graph-link"`, `variant="outline"`, `size="sm"`, linking to `/graph?type=work&id=<id>`, `/graph?type=expression&id=<id>`, or `/graph?type=manifestation&id=<id>`) on the right alongside the optional FRBR tier badge (`hidden sm:inline-flex` on narrow mobile viewports). Every `"Explore Graph"` entry button across `/work/[id]`, `/expression/[id]`, and `/manifestation/[id]` MUST render using the localized `graph.exploreGraph` translation key (`"Explore Graph"` in `en.json`, sentence-case `"Eksploruj graf"` in `pl.json`), MUST remain visible above the fold on both mobile (`390x844`) and desktop (`1280x800`) viewports without being pushed below cover artwork, MUST keep its bar at `<= 4` visible buttons, and MUST preserve query-parameter routing compatible with `CAPACITOR_BUILD=true` static export.

#### Scenario: Work, Expression, and Manifestation pages surface localized Explore Graph above the fold

- **GIVEN** a user viewing `/work/<id>`, `/expression/<id>`, or `/manifestation/<id>` on a mobile (`390x844`) or desktop (`1280x800`) viewport
- **WHEN** the page renders
- **THEN** the top utility bar displays `[← Back]` and the localized `"Explore Graph"` link (`data-testid="explore-graph-link"`, text from `graph.exploreGraph`) above the fold prior to cover artwork and metadata sections
- **AND** the utility bar contains `<= 4` visible buttons with zero horizontal clipping on `390px` viewports

#### Scenario: Polish locale renders sentence-case graph entry label across entity pages

- **GIVEN** a user browsing `/work/<id>`, `/expression/<id>`, or `/manifestation/<id>` with the Polish (`pl`) locale active
- **WHEN** the entity detail page renders
- **THEN** `data-testid="explore-graph-link"` displays `"Eksploruj graf"` (never a hardcoded English `"Explore Graph"` string) and navigates to `/graph?type=<work|expression|manifestation>&id=<id>`

#### Scenario: Work hero action cluster stays focused on Work CTAs without graph crowding

- **GIVEN** an authenticated user viewing a serial `Work` (`/work/<id>` with `work_kind === "serial"`)
- **WHEN** the hero metadata section renders
- **THEN** `"Explore Graph"` resides in the top utility bar rather than between `"Add Issue"` and `"Add to Wishlist"`, keeping the hero action cluster uncluttered with a single clear primary CTA (`"Add Issue"`)

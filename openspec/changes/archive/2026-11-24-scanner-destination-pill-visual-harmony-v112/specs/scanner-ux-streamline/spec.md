## MODIFIED Requirements

### Requirement: Localized scanner top bar and clear policy naming

The scanner top bar SHALL present a single-line compact control row containing localized **Format**, **Destination Policy** ("Shelf", "Wishlist", "Catalog Only"), and optional **Batch Mode** controls, followed by a full-width (100%) unified lookup bar when active. All top bar headers, selector pills, menu options, and tooltips SHALL be fully translated in both English and Polish without horizontal clipping on mobile viewports (`>= 360px`). Passive selector pills on the control row—including **Format** (`format-selector-trigger`), **Destination Policy** (`policy-selector-trigger`), and inactive **Batch Mode** (`batch-scan-toggle` when disabled)—SHALL share a cohesive translucent dark-glass pill treatment over the scanner overlay backdrop rather than rendering **Destination Policy** as a solid white high-contrast button, reserving primary accent fill exclusively for active scanner toggle states (such as enabled **Batch Mode** or active **Flash**).

#### Scenario: User opens scanner and views top bar

- **WHEN** the user opens `/scan` on a mobile or desktop viewport
- **THEN** the top bar displays localized titles, the compact single-line control row with Format (`format-selector-trigger`), Destination Policy (`policy-selector-trigger`: "Shelf", "Wishlist", "Catalog Only"), and Batch Mode (`batch-scan-toggle`) with zero horizontal icon clipping
- **AND** the unified search input (`unified-lookup-input`) spans 100% of the available container width below the control row

#### Scenario: Destination policy pill harmonizes visually with sibling TopBar controls

- **WHEN** the scanner top bar renders with `format-selector-trigger`, `policy-selector-trigger`, and an inactive `batch-scan-toggle`
- **THEN** `policy-selector-trigger` uses the same translucent dark-glass pill styling (`bg-white/10`, white text, subtle translucent border, translucent hover state) as `format-selector-trigger` instead of a solid white (`bg-white` / `text-black`) fill
- **AND** text and chevron icon contrast remain clearly legible against the dark overlay backdrop across both mobile (`390x844`) and desktop (`1280x800`) viewports

#### Scenario: User changes policy mode

- **WHEN** the user opens the Destination Policy selector (`policy-selector-trigger`) and selects "Catalog Only", "Wishlist", or "Shelf"
- **THEN** the active policy pill updates immediately, displays localized guidance, and persists across scans without ambiguous terminology

#### Scenario: User switches media format via compact selector menu

- **WHEN** the user activates the Format selector pill (`format-selector-trigger`)
- **THEN** a localized menu opens displaying every registered format in `SCAN_FORMATS` with icon and full label
- **AND** selecting a format updates the active pill label immediately and closes the menu

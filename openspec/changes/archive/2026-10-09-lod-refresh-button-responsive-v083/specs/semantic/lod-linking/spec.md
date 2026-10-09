## MODIFIED Requirements

### Requirement: Manifestation Semantic Links UI
The system SHALL display an interactive Linked Open Data panel on manifestation detail pages and item detail views presenting resolved external entities with visual indicators, responsive action controls, and direct outbound links.

#### Scenario: Viewing resolved semantic links on manifestation detail page
- **WHEN** a user navigates to a manifestation detail page that has resolved LOD links
- **THEN** the page displays a "Linked Open Data" section rendering distinct badges for DBpedia concepts, WordNet synsets, and GeoNames publisher locations with authority badges and external link icons.

#### Scenario: Opening external authority link in new tab with security attributes
- **WHEN** a user clicks on an external authority badge (such as a DBpedia or GeoNames link)
- **THEN** the browser opens the external URL in a new tab with `target="_blank"` and `rel="noopener noreferrer"` attributes.

#### Scenario: Displaying empty or loading state when no links exist
- **WHEN** a manifestation has no resolved external links and a background task is not active
- **THEN** the semantic links section displays a subtle empty state with an option to trigger background reconciliation.

#### Scenario: Responsive scan button containment across screen sizes
- **WHEN** a user views the Linked Open Data card on a mobile or narrow display, or under languages with long localized scan button labels
- **THEN** the card header uses a responsive wrapping layout preventing button bounds from overflowing or breaking out of the container card frame
- **AND** the button label truncates safely while preserving full tooltip title information.

#### Scenario: Inspecting inherited semantic links on item detail views
- **WHEN** a user navigates to an Item holding detail page whose parent Manifestation has resolved or pending semantic links
- **THEN** the item view renders the Linked Open Data card displaying inherited links and providing an accessible trigger to run LOD reconciliation directly.

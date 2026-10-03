## ADDED Requirements

### Requirement: Feedback page mobile filters use collapsible drawer
The feedback page filter sidebar SHALL be wrapped in a collapsible bottom-sheet drawer on mobile viewports (< 768px) to prevent excessive scrolling past filter controls.

#### Scenario: Mobile viewport renders filter drawer collapsed

- **WHEN** a user opens the feedback page on a mobile viewport (width < 768px)
- **THEN** the filter controls SHALL be hidden inside a collapsed drawer/sheet
- **AND** a "Filters" button or icon SHALL be visible to expand the drawer

#### Scenario: User opens and applies filters on mobile

- **WHEN** a user taps the filter button to expand the drawer
- **AND** selects filter criteria and taps "Apply"
- **THEN** the drawer SHALL close
- **AND** the feedback list SHALL update with filtered results
- **AND** the entire interaction SHALL require fewer than 3 taps

#### Scenario: Desktop viewport renders filters inline

- **WHEN** a user opens the feedback page on a desktop viewport (width >= 768px)
- **THEN** the filter controls SHALL render inline in the sidebar (unchanged behavior)

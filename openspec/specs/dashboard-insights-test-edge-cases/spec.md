## ADDED Requirements

### Requirement: CollectionInsights renders during loading and error states

The `CollectionInsights` component SHALL render the insights section (including child skeletons/errors) when `useStats` returns `isLoading: true` or `isError: true`, and SHALL hide the section only when `data.total_items === 0`.

#### Scenario: Insights section renders during loading

- **WHEN** `CollectionInsights` renders with `useStats` returning `isLoading: true` and `data: undefined`
- **THEN** the `collection-insights` test-id SHALL be in the document

#### Scenario: Insights section renders on error

- **WHEN** `CollectionInsights` renders with `useStats` returning `isError: true` and `data: undefined`
- **THEN** the `collection-insights` test-id SHALL be in the document

### Requirement: VelocityChart renders empty state for zero-acquisition data

The `VelocityChart` component SHALL render an empty state message when velocity data is an empty array, distinct from loading and error states.

#### Scenario: Empty data array shows empty state message

- **WHEN** `VelocityChart` renders with `data: []`
- **THEN** an empty state message SHALL be displayed rather than an empty chart

### Requirement: TypeDistributionChart renders empty state for zero-distribution data

The `TypeDistributionChart` component SHALL render an empty state message when both `by_type` and `by_format` are empty arrays.

#### Scenario: Empty distribution shows empty state message

- **WHEN** `TypeDistributionChart` renders with `data: {by_type: [], by_format: []}`
- **THEN** an empty state message SHALL be displayed

### Requirement: Backend velocity and distribution endpoints return valid empty responses

The `/api/profile/insights/velocity` and `/api/profile/insights/distribution` endpoints SHALL return valid response shapes when the authenticated user has zero items.

#### Scenario: Velocity returns empty array for user with no items

- **WHEN** a user with zero items calls `GET /api/profile/insights/velocity`
- **THEN** the response SHALL return 200 with `{velocity: []}`

#### Scenario: Distribution returns empty arrays for user with no items

- **WHEN** a user with zero items calls `GET /api/profile/insights/distribution`
- **THEN** the response SHALL return 200 with `{by_type: [], by_format: []}`

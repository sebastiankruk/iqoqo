# Collector Insights

## Purpose

Provide authenticated users with analytics and visualizations about their collection: acquisition velocity over time, distribution by media type and format, rendered as responsive charts on the dashboard.

## Requirements

### Requirement: Item Acquisition Velocity API

The system SHALL provide an authenticated API endpoint that returns the number of items added to the user's collection per month. The response MUST cover at least the last 12 months and use GROUP BY aggregate queries for performance.

#### Scenario: Authenticated user requests velocity data

- **WHEN** an authenticated user sends a GET to `/api/profile/insights/velocity`
- **THEN** the system SHALL return a JSON array of objects, each containing `month` (ISO date string for the first day of the month) and `count` (integer), ordered chronologically, covering the last 12 months.

#### Scenario: User with no items requests velocity data

- **WHEN** an authenticated user with zero items sends a GET to `/api/profile/insights/velocity`
- **THEN** the system SHALL return an array of 12 objects with `count: 0` for each month.

#### Scenario: Unauthenticated user requests velocity data

- **WHEN** an unauthenticated user sends a GET to `/api/profile/insights/velocity`
- **THEN** the system SHALL return HTTP 401 with error `"Token missing"`.

### Requirement: Media Type Distribution API

The system SHALL provide an authenticated API endpoint that returns the distribution of the user's items grouped by media type (content type) and optionally by format sub-category. The response MUST use GROUP BY aggregate queries.

#### Scenario: Authenticated user requests type distribution

- **WHEN** an authenticated user sends a GET to `/api/profile/insights/distribution`
- **THEN** the system SHALL return a JSON object containing `by_type` (array of `{type, count}` objects grouped by `Expression.content_type`) and `by_format` (array of `{format, count}` objects grouped by the normalized format from `Manifestation.meta.format`).

#### Scenario: User with items across multiple types

- **WHEN** an authenticated user with books, music CDs, and board games requests the distribution
- **THEN** the system SHALL return distinct entries for each content type (e.g., `"text"`, `"music"`, `"board_game"`) with accurate counts.

#### Scenario: Empty collection distribution

- **WHEN** an authenticated user with zero items requests the distribution
- **THEN** the system SHALL return empty arrays for both `by_type` and `by_format`.

### Requirement: Dashboard Velocity Chart

The system SHALL render a bar or line chart on the authenticated user's dashboard showing item acquisition velocity (items added per month) over the last 12 months. The chart MUST be read-only and responsive.

#### Scenario: User views dashboard with acquisition history

- **WHEN** an authenticated user with items added across multiple months navigates to the dashboard
- **THEN** the system SHALL render a chart showing monthly acquisition counts, with the X-axis representing months and the Y-axis representing item counts.

#### Scenario: User views dashboard on mobile viewport

- **WHEN** an authenticated user views the dashboard on a mobile device (viewport < 640px)
- **THEN** the velocity chart SHALL resize responsively without horizontal scrolling or text overflow.

### Requirement: Dashboard Type Distribution Chart

The system SHALL render a chart (donut, pie, or horizontal bar) on the authenticated user's dashboard showing the distribution of items by media type. The chart MUST display the type name and count for each segment.

#### Scenario: User views distribution chart

- **WHEN** an authenticated user navigates to the dashboard
- **THEN** the system SHALL render a media type distribution chart below or alongside the existing `StatsCards`, with each segment labeled by content type and count.

#### Scenario: User with single media type

- **WHEN** an authenticated user whose collection contains only books views the dashboard
- **THEN** the distribution chart SHALL render a single segment representing 100% of the collection.

### Requirement: Insights Loading and Error States

The system SHALL display loading skeletons while analytics data is being fetched and graceful error indicators if the API request fails. Analytics errors MUST NOT break the existing dashboard (StatsCards) rendering.

#### Scenario: Analytics API is loading

- **WHEN** the dashboard is rendered and analytics data has not yet loaded
- **THEN** the system SHALL display animated skeleton placeholders in place of the charts.

#### Scenario: Analytics API returns an error

- **WHEN** the analytics API request fails with a server error
- **THEN** the system SHALL display a non-intrusive error indicator in the analytics section without affecting the `StatsCards` component above.

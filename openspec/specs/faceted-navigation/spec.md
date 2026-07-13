# OpenSpec Specification: Faceted Navigation and Cross-Filtering

This specification locks in the behavioral requirements, cross-filtering rules, and empty-state handling for iqoqo's multi-faceted library navigation interface.

## 1. Cross-Filtering Logic

The navigation layout allows users to narrow down their collection using multiple facets simultaneously.

- **Intra-Facet Selection (OR):** Multiple selections within a single facet category (e.g., Format: `Book` and `Vinyl`) must behave as an `OR` operation. The system displays items that are either Books or Vinyls.
- **Inter-Facet Selection (AND):** Selections across different facet categories (e.g., Format: `Book` and Language: `Polish`) must behave as an `AND` operation. The system displays only items that are Books AND written in Polish.
- **Supported Facet Keys:** The navigation panel must support filtering by:
  - Format (Manifestation type)
  - Language
  - Availability (Lent vs. Available vs. Wishlisted)
  - Storage Location (Shelf, Box, Room)
  - User Tags

## 2. Empty-State Requirements

When active filter combinations yield zero matching records:

- **No Crash / Blank Page:** The application must never render an empty page, raw JSON, or crash.
- **Empty State Component:** The UI must display a dedicated, styled empty-state component explaining:
  - "No items match your active filters."
- **Reset Trigger:** Provide a clear "Clear all filters" button that resets all active facet checkboxes and returns the user to the default unfiltered collection view.
- **Action Fallback:** Offer a secondary button to "Add manual entry" or "Scan new barcode" to encourage collection growth.

## 3. Performance & DB Aggregations

To prevent application lag and server-side overload:

- **No N+1 Queries:** Do not compute facet counts by executing multiple separate queries or using client-side/Python dictionary comprehensions over active records.
- **Group By Aggregates:** The backend API must fetch facet counts using efficient SQL `GROUP BY` aggregation queries in a single database request.

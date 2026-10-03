## Why

We need to address direct user requests from previous releases, specifically focusing on gathering bugs/feedback natively within the app, and allowing users to discover manifestations they do not currently own within a filtered set.

## What Changes

- Add a feedback and bugs gathering mechanism natively in the UI, including a management screen for users and admins.
- Introduce a new "Ownership" facet category in faceted navigation with options like "Owned" and "Not Owned".

## Capabilities

### New Capabilities

- `feedback-mechanism`: A native UI flow and backend endpoint to gather user feedback and bug reports.

### Modified Capabilities

- `faceted-navigation`: Extending existing faceted search logic to include an inverse ownership filter ("show me manifestations I don't have").

## Impact

- **Frontend**: Feedback UI components, Faceted navigation search UI updates.
- **Backend**: Faceted search queries and filter resolution logic. New endpoint for feedback ingestion.

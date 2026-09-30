---
type: Concept
title: proposal
timestamp: 2026-07-22T10:18:50Z
---

## Why

The current faceted navigation and metadata display logic has several inconsistencies related to the FRBR ontology and user authentication status. Filters and counts frequently refer only to "My items" even when browsing broader entities (Works, Expressions, Global Library). Furthermore, certain user-specific facets like "Collection status", "Tags", "Storage location", and "Progress" incorrectly appear in (or fail to properly filter) higher FRBR views such as Global Library, Works, and Expressions. Additionally, Manifestation-level facets (Media category, Physical Kind) and Item-level facets (Tags, Storage Location, Named Collections) fail to filter or return the correct associated broader entities (Expressions/Works). Finally, unauthorized users see 0 counts and broken views. This change addresses these inconsistencies to ensure accurate, context-aware filtering and counting across all FRBR layers.

## What Changes

- **Fix FRBR-Specific Counts in Filters**: Update filter counts to reflect the numbers associated with the currently viewed FRBR type (Work, Expression, Manifestation, Item) rather than defaulting to "My items" (Item-level counts).
- **Contextualize All Item-Level Facets Across FRBR Views**:
  - Ensure that Collection Status, Progress, Tags, Storage Location, and Named Collections — when shown in Works, Expressions, or Global Library — filter those views by returning entities associated with matching child Items (e.g., Works whose Items have a given tag or status).
  - Hide user-specific facets (Collection Status, Progress, Tags, Storage Location, Named Collections) for unauthorized users, as they require user context.
- **Fix Manifestation-Level Facet Filtering for Works/Expressions**: Ensure that filtering by Media Category or Physical Kind correctly returns related broader entities (Expressions, Works) in the Global Library.
- **Fix Unauthorized User Experience**: Ensure that unauthenticated users do not see 0 counts where they shouldn't, hide all user-specific facets, and fix the display of Expressions/Works that are currently hidden.

## Capabilities

### New Capabilities

- `cross-frbr-filtering`: Standardizes how lower-level entity attributes (like Item status or Manifestation media categories) bubble up to filter higher-level entities (Expressions, Works).

### Modified Capabilities

- `faceted-navigation`: Modifying requirements for count aggregation (must respect FRBR level) and facet visibility (must respect auth state and FRBR context).

## Impact

- **Backend API (`app/api/`)**: Modifications to the metadata and facet aggregation logic to ensure accurate counts and filtering across FRBR hierarchy.
- **Frontend Components (`components/`)**: Updates to faceted navigation UI to conditionally render facets based on authentication status and current FRBR view.
- **Database Queries (`app/services/` or `app/repositories/`)**: Complex JOINs or aggregation queries to support filtering Works/Expressions by their child Items' statuses.

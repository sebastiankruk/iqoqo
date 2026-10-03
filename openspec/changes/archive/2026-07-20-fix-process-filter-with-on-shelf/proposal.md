---
type: Concept
title: proposal
timestamp: 2026-07-22T10:18:50Z
---

## Why

There is a bug in the filtering logic for Work and Expression views: filtering by Process (e.g., Unread, Read, Want to Read) fails to apply when the "On Shelf" filter is also selected. When "On Shelf" is active, all elements are returned regardless of the Process filter. However, when "On Shelf" is not selected, the Process filter works correctly. This breaks the ability to find specific items in one's collection (e.g., unread items on the shelf).

## What Changes

- Update the backend filtering logic to properly combine "Process" and "On Shelf" filters with a logical AND instead of an OR or ignoring one.
- Ensure that cross-FRBR filters (like "On Shelf" and "Process") are correctly composed when querying Works and Expressions.

## Capabilities

### New Capabilities

### Modified Capabilities

- `cross-frbr-filtering`: Fix combination logic when applying multiple cross-tier filters simultaneously.

## Impact

- Backend: Query building logic for Work and Expression list views.
- Frontend: Ensure filter parameters are sent correctly when both are selected.

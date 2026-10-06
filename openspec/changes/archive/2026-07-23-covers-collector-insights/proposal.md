---
type: Concept
title: proposal
timestamp: 2026-07-22T10:18:49Z
---

## Why

The current cover pipeline has two UX gaps. First, when all external API and LLM tiers fail, the Tier 5 PIL fallback (`generate_fallback_cover`) produces a bare gradient image with no visual indication of its origin or instructions for improvement — users see a generic cover and have no idea whether it came from OpenLibrary, an AI model, or was locally generated. The `cover_source` metadata is stored in the DB but never surfaced in the UI. Second, the dashboard (`StatsCards`) shows only basic status counts (items, reading, wishlist, lent, borrowed) with no deeper analytics — collectors have no visibility into their cataloging velocity over time, how their collection distributes across media types/formats, or any temporal acquisition trends.

This change replaces the stub fallback covers with visually polished, provenance-aware alternatives and adds a read-only Collector Insights analytics surface to the dashboard.

## What Changes

- **Cover fallback redesign**: Replace the current `generate_fallback_cover()` in `app/utils/covers.py` with an enhanced version that renders a "powered-by" provenance badge and a clearer visual treatment. The badge communicates what tier generated the cover (fallback, AI, API download, user upload).
- **Cover provenance UI**: Surface the `cover_source` metadata on item and manifestation detail pages as a small, readable provenance indicator (e.g., "Source: OpenLibrary", "Source: AI-generated", "Source: Fallback").
- **Collector insights API**: Add new endpoints in `app/api/profile.py` to return aggregate analytics for the authenticated user: item acquisition velocity (items added per month over time), media type/format distribution breakdown, and optional per-format sub-grouping.
- **Collector insights UI**: Expand the dashboard beyond `StatsCards` with new analytics components in `frontend/components/dashboard/` that render read-only charts/summaries for item velocity (bar/line chart), type distributions (donut/bar chart), and format breakdowns.

## Capabilities

### New Capabilities

- `cover-provenance`: Covers the enhanced fallback cover generation with "powered-by" provenance badges and the frontend display of cover source metadata on item/manifestation views.
- `collector-insights`: Covers the backend analytics API endpoints (item velocity, type distributions) and the frontend dashboard analytics components.

### Modified Capabilities

None — existing specs are not affected at the requirement level.

## Impact

- **Backend**: `app/utils/covers.py` (redesigned fallback generator + provenance badge rendering), `app/api/profile.py` (new analytics endpoints), `app/core/data_manager.py` (new aggregate query methods).
- **Frontend**: `frontend/components/dashboard/stats-cards.tsx` (extended or accompanied by new analytics cards), new `frontend/components/dashboard/collection-insights.tsx` and/or `frontend/components/dashboard/velocity-chart.tsx`, item/manifestation detail views (provenance indicator).
- **Database**: No schema changes — analytics are computed from existing `Item.created_at`, `Manifestation.meta.format`, `Expression.content_type` columns. Cover provenance already stored in `Manifestation.meta.cover_source`.
- **Dependencies**: Potentially a lightweight charting library for frontend (e.g., Recharts, already common in Next.js ecosystems) if not already present.

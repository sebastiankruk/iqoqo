## Context

The dashboard currently lacks layout responsiveness for metric tiles on mobile viewports, causing them to stack vertically and consume too much vertical space. Additionally, users need a way to distinguish between global repository metrics (everything in the system) and metrics specific to their personal collection.

## Goals / Non-Goals

**Goals:**

- Implement a horizontal scrolling flex-wrap layout for metric tiles and the wish list section on mobile devices.
- Provide a UI toggle to switch between "Stats" and "Insights" (time charts).
- Provide a global vs personal scope toggle for statistics, with dynamic labels for each scope.
- Hide FRBR stats entirely from the dashboard.

**Non-Goals:**

- Designing completely new dashboard metrics outside of the agreed set.
- Refactoring the entire dashboard layout beyond the top tiles and wish list.

## Decisions

- **Layout**: Use Tailwind CSS classes `overflow-x-auto flex-nowrap` on mobile viewports for metric tiles, Insight charts (full-width single items), and the wish list container to enforce single-line horizontal scrolling.
- **Scoping**: Add a `scope` query parameter (`?scope=global|personal`) to the profile/stats API, as well as to the profile/insights API. The backend dynamically alters queries based on this parameter. The frontend passes this `scope` state down into both the numeric Stats tiles and the Insights charts (`CollectionInsights`, `VelocityChart`, `TypeDistributionChart`).
- **Labels**: Frontend dynamically changes stat labels based on scope (e.g., Personal "My items" -> Global "All items", "Reading" -> "Being read", "On wish list" -> "On wish lists").

## Risks / Trade-offs

- [Risk] Horizontal scrolling might be unintuitive on some devices if scrollbars are hidden. → Mitigation: Ensure a slight peek of the next tile is visible on standard mobile viewports to hint at scrollability.

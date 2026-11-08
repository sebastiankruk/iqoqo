## Context

Standard cover thumbnails are too small to read cartographic maps or game boards. Collectors cataloging fantasy novels, RPGs, board games, or folding maps need a smooth pan/zoom/rotate viewer and a fast way to filter items that contain maps.

## Goals / Non-Goals

**Goals:**
- Deliver `<MapViewerModal />` with smooth CSS transform pan/zoom/rotate (`1x`–`5x`) and touch gesture support on mobile.
- Keep button density within `iqoqo-ux-auditor` limits ($\le 4$ visible buttons per container).
- Enable filtering `/collection` by `has_map=true` across Items, Manifestations, and Works.

**Non-Goals:**
- External tile-server GIS hosting (GeoServer / Mapbox tiles); uses high-res image assets stored via our cover/gallery pipeline.

## Decisions

### Zero-Dependency CSS Transform Pan/Zoom Viewer
* **Decision:** Implement `<MapViewerModal />` using React pointer/wheel/pinch handlers and hardware-accelerated CSS `transform: translate3d(...) scale(...) rotate(...)` inside a Shadcn `Dialog`.
* **Rationale:** Avoids heavy external canvas/GIS bundle bloat in both web and Capacitor static builds while delivering 60fps pan/zoom inspection.
